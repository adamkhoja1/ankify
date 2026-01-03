"""Command-line interface for ankification."""

import asyncio
import sys

import click

from .cards import Card, CardGenerator, CardStatus
from .config import Config, ConfigManager
from .export import AnkiConnectExporter, CSVExporter
from .storage.database import Database
from .tui import run_tui


@click.group()
@click.pass_context
def main(ctx: click.Context) -> None:
    """Ankification - Generate Anki flashcards from content using LLMs."""
    ctx.ensure_object(dict)

    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.load()
    ctx.obj["config"] = config
    ctx.obj["config_manager"] = config_manager


@main.command()
@click.argument("sources", nargs=-1, required=True)
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["openai", "anthropic"]),
    help="LLM provider to use",
)
@click.option(
    "--count-guidance",
    "-c",
    help='Guidance for number of cards (e.g., "around 20", "comprehensive")',
)
@click.option(
    "--card-types",
    "-t",
    multiple=True,
    type=click.Choice(["basic", "cloze"]),
    help="Types of cards to generate",
)
@click.option(
    "--export-format", "-e", type=click.Choice(["csv", "ankiconnect"]),
    help="Export format",
)
@click.option("--no-review", is_flag=True, help="Skip interactive review")
@click.pass_context
def generate(
    ctx: click.Context,
    sources: tuple[str, ...],
    provider: str | None,
    count_guidance: str | None,
    card_types: tuple[str, ...],
    export_format: str | None,
    no_review: bool,
) -> None:
    """Generate flashcards from one or more sources.

    SOURCES can be URLs, file paths, or use - for stdin.
    """
    config: Config = ctx.obj["config"]

    # Convert card_types tuple to list or use config default
    card_types_list = list(card_types) if card_types else None

    # Use config default for export format if not specified
    if export_format is None:
        export_format = config.export.default_format

    asyncio.run(
        _generate_async(
            list(sources),
            config,
            provider,
            count_guidance,
            card_types_list,
            export_format,
            no_review,
        )
    )


async def _generate_async(
    sources: list[str],
    config: Config,
    provider: str | None,
    count_guidance: str | None,
    card_types: list[str] | None,
    export_format: str,
    no_review: bool,
) -> None:
    """Async implementation of generate command."""
    click.echo(f"Generating cards from {len(sources)} source(s)...")

    # Initialize database
    async with Database(config.storage.database_path) as db:
        # Initialize generator
        generator = CardGenerator(config, db)

        try:
            # Generate cards and create session
            session_id = await generator.create_session(
                sources, provider, card_types, count_guidance
            )

            # Get generated cards
            cards = await db.get_cards_by_session(session_id)

            click.echo(f"\n✓ Generated {len(cards)} cards")

            # Show card types breakdown
            basic_count = sum(1 for c in cards if c.type.value == "basic")
            cloze_count = sum(1 for c in cards if c.type.value == "cloze")
            if basic_count:
                click.echo(f"  - {basic_count} basic card(s)")
            if cloze_count:
                click.echo(f"  - {cloze_count} cloze card(s)")

            # Review flow
            if not no_review:
                click.echo("\nLaunching interactive review...")

                # Launch TUI for review
                reviewed_cards, tui_export_choice = run_tui(cards, config)

                # Save reviewed cards
                for card in reviewed_cards:
                    await db.save_card(card)

                # Override export format if user chose in TUI
                if tui_export_choice:
                    export_format = tui_export_choice

            # Export
            await _export_cards(cards, export_format, config)

            # Complete session
            await db.complete_session(session_id)

            click.echo("\n✓ Done!")

        except Exception as e:
            click.echo(f"\n✗ Error: {e}", err=True)
            sys.exit(1)


async def _export_cards(cards: list[Card], export_format: str, config: Config) -> None:
    """Export cards to specified format."""
    # Filter accepted cards
    accepted_cards = [c for c in cards if c.status == CardStatus.ACCEPTED]

    if not accepted_cards:
        click.echo("\nNo accepted cards to export.")
        return

    click.echo(f"\nExporting {len(accepted_cards)} accepted card(s)...")

    if export_format == "csv":
        csv_exporter = CSVExporter(config.export.csv.output_dir)
        output_path = csv_exporter.export(accepted_cards)
        click.echo(f"✓ Exported to: {output_path}")

    elif export_format == "ankiconnect":
        anki_exporter = AnkiConnectExporter(
            url=config.export.ankiconnect.url, deck=config.export.ankiconnect.deck
        )

        try:
            # Test connection
            await anki_exporter.test_connection()

            # Export
            results = await anki_exporter.export(accepted_cards)

            click.echo(f"✓ Exported {results['success']} card(s) to Anki")
            if results["failed"]:
                click.echo(f"✗ Failed to export {results['failed']} card(s)", err=True)
                for error in results.get("errors", []):
                    click.echo(f"  {error}", err=True)

        except Exception as e:
            click.echo(f"✗ AnkiConnect error: {e}", err=True)
            click.echo(
                "Make sure Anki is running and AnkiConnect addon is installed.",
                err=True,
            )


@main.group()
def config() -> None:
    """Manage configuration."""
    pass


@config.command("init")
@click.pass_context
def config_init(ctx: click.Context) -> None:
    """Initialize configuration file."""
    config_manager: ConfigManager = ctx.obj["config_manager"]

    try:
        config_manager.init_config()
        click.echo(f"✓ Configuration initialized at {config_manager.config_path}")
        click.echo("\nEdit the file to set your API keys and preferences.")
    except FileExistsError:
        click.echo(f"Configuration already exists at {config_manager.config_path}")
        click.echo("Use 'ankification config show' to view current configuration.")


@config.command("show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """Show current configuration."""
    config_manager: ConfigManager = ctx.obj["config_manager"]
    yaml_str = config_manager.show_config()
    click.echo(yaml_str)


@config.command("set")
@click.argument("key")
@click.argument("value")
@click.pass_context
def config_set(ctx: click.Context, key: str, value: str) -> None:
    """Set a configuration value.

    Example: ankification config set llm.default_provider anthropic
    """
    config_manager: ConfigManager = ctx.obj["config_manager"]

    try:
        config_manager.set_value(key, value)
        click.echo(f"✓ Set {key} = {value}")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        sys.exit(1)


@main.group()
def tags() -> None:
    """Manage tag pools."""
    pass


@tags.command("add")
@click.argument("tag_names", nargs=-1, required=True)
@click.pass_context
def tags_add(ctx: click.Context, tag_names: tuple[str, ...]) -> None:
    """Add tags to the pool."""
    config_manager: ConfigManager = ctx.obj["config_manager"]
    config = config_manager.get()

    for tag in tag_names:
        if tag not in config.tags.pools:
            config.tags.pools.append(tag)

    config_manager.save(config)
    click.echo(f"✓ Added {len(tag_names)} tag(s) to pool")


@tags.command("list")
@click.pass_context
def tags_list(ctx: click.Context) -> None:
    """List all tags in the pool."""
    config: Config = ctx.obj["config"]

    if not config.tags.pools:
        click.echo("No tags in pool.")
        return

    click.echo("Available tags:")
    for tag in sorted(config.tags.pools):
        click.echo(f"  - {tag}")


@tags.command("remove")
@click.argument("tag_name")
@click.pass_context
def tags_remove(ctx: click.Context, tag_name: str) -> None:
    """Remove a tag from the pool."""
    config_manager: ConfigManager = ctx.obj["config_manager"]
    config = config_manager.get()

    if tag_name in config.tags.pools:
        config.tags.pools.remove(tag_name)
        config_manager.save(config)
        click.echo(f"✓ Removed '{tag_name}' from pool")
    else:
        click.echo(f"Tag '{tag_name}' not in pool")


@main.command("list-sessions")
@click.option("--limit", "-n", default=10, help="Number of sessions to show")
@click.pass_context
def list_sessions(ctx: click.Context, limit: int) -> None:
    """List recent generation sessions."""
    config: Config = ctx.obj["config"]
    asyncio.run(_list_sessions_async(config, limit))


async def _list_sessions_async(config: Config, limit: int) -> None:
    """Async implementation of list-sessions."""
    async with Database(config.storage.database_path) as db:
        sessions = await db.get_sessions(limit)

        if not sessions:
            click.echo("No sessions found.")
            return

        click.echo(f"Recent sessions (showing {len(sessions)}):\n")

        for session in sessions:
            click.echo(f"ID: {session['id']}")
            click.echo(f"Created: {session['created_at']}")
            click.echo(f"Sources: {', '.join(session['sources'])}")
            if session["completed_at"]:
                click.echo(f"Completed: {session['completed_at']}")
            click.echo()


@main.command("export")
@click.option("--session", "-s", help="Session ID to export")
@click.option(
    "--format", "-f", "export_format",
    type=click.Choice(["csv", "ankiconnect"]),
    help="Export format",
)
@click.option(
    "--status",
    type=click.Choice(["accepted", "draft", "rejected"]),
    help="Filter by status",
)
@click.pass_context
def export_command(
    ctx: click.Context,
    session: str | None,
    export_format: str | None,
    status: str | None,
) -> None:
    """Export cards from a previous session."""
    config: Config = ctx.obj["config"]

    if export_format is None:
        export_format = config.export.default_format

    asyncio.run(_export_session_async(config, session, export_format, status))


async def _export_session_async(
    config: Config, session_id: str | None, export_format: str, status_filter: str | None
) -> None:
    """Async implementation of export command."""
    from .cards.models import CardStatus

    async with Database(config.storage.database_path) as db:
        # Get cards
        if session_id:
            cards = await db.get_cards_by_session(session_id)
            if not cards:
                click.echo(f"No cards found for session {session_id}")
                return
        else:
            # Export all accepted cards if no session specified
            cards = await db.get_cards_by_status(CardStatus.ACCEPTED)
            if not cards:
                click.echo("No accepted cards found")
                return

        # Filter by status if specified
        if status_filter:
            status_enum = CardStatus(status_filter)
            cards = [c for c in cards if c.status == status_enum]

        await _export_cards(cards, export_format, config)


@main.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int, reload: bool) -> None:
    """Start the web interface server.

    This starts a FastAPI server with the web interface. The server will be
    accessible at http://{host}:{port}

    By default, the server runs on http://127.0.0.1:8000
    """
    import uvicorn


    click.echo(f"Starting Ankification web server at http://{host}:{port}")
    click.echo("Press Ctrl+C to stop the server")
    click.echo("")

    if reload:
        click.echo("Running in development mode with auto-reload enabled")
        click.echo("")

    try:
        uvicorn.run(
            "ankification.web.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        click.echo("\nServer stopped")


if __name__ == "__main__":
    main()
