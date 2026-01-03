"""Configuration schema and validation."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class OpenAIConfig(BaseModel):
    """OpenAI provider configuration."""

    api_key: str = Field(default="", description="OpenAI API key")
    model: str = Field(default="gpt-4-turbo-preview", description="Model to use")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature")


class AnthropicConfig(BaseModel):
    """Anthropic provider configuration."""

    api_key: str = Field(default="", description="Anthropic API key")
    model: str = Field(
        default="claude-3-5-sonnet-20241022", description="Model to use"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Temperature")


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    default_provider: str = Field(
        default="openai", description="Default LLM provider (openai or anthropic)"
    )
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    anthropic: AnthropicConfig = Field(default_factory=AnthropicConfig)

    @field_validator("default_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider name."""
        if v not in {"openai", "anthropic"}:
            raise ValueError("default_provider must be 'openai' or 'anthropic'")
        return v


class GenerationConfig(BaseModel):
    """Card generation configuration."""

    card_types: list[str] = Field(
        default=["basic", "cloze"], description="Card types to generate"
    )
    auto_determine_count: bool = Field(
        default=True, description="Auto-determine number of cards"
    )
    count_guidance: str | None = Field(
        default=None, description="Optional guidance for card count"
    )
    user_directives: list[str] = Field(
        default_factory=list, description="Persistent user instructions"
    )

    @field_validator("card_types")
    @classmethod
    def validate_card_types(cls, v: list[str]) -> list[str]:
        """Validate card types."""
        valid_types = {"basic", "cloze"}
        for card_type in v:
            if card_type not in valid_types:
                raise ValueError(f"Invalid card type: {card_type}")
        return v


class TagsConfig(BaseModel):
    """Tags configuration."""

    pools: list[str] = Field(
        default_factory=list, description="Available tag pools"
    )
    auto_tag: bool = Field(default=True, description="Enable auto-tagging")
    prompt_for_tags: bool = Field(
        default=True, description="Prompt user for tag selection"
    )


class KeybindingsConfig(BaseModel):
    """TUI keybindings configuration."""

    next: str = Field(default="j", description="Next card")
    prev: str = Field(default="k", description="Previous card")
    accept: str = Field(default="a", description="Accept card")
    reject: str = Field(default="d", description="Reject card")
    edit: str = Field(default="e", description="Edit card")
    refine: str = Field(default="r", description="Refine card with LLM")
    quit: str = Field(default="q", description="Quit and export")
    help: str = Field(default="?", description="Show help")


class TUIConfig(BaseModel):
    """TUI configuration."""

    keybindings: KeybindingsConfig = Field(default_factory=KeybindingsConfig)
    show_shortcuts: bool = Field(
        default=True, description="Show shortcuts in interface"
    )


class AnkiConnectConfig(BaseModel):
    """AnkiConnect configuration."""

    url: str = Field(default="http://localhost:8765", description="AnkiConnect URL")
    deck: str = Field(default="Default", description="Target deck name")


class CSVExportConfig(BaseModel):
    """CSV export configuration."""

    output_dir: str = Field(
        default="~/Documents/Anki", description="Output directory for CSV files"
    )

    @field_validator("output_dir")
    @classmethod
    def expand_path(cls, v: str) -> str:
        """Expand user path."""
        return str(Path(v).expanduser())


class ExportConfig(BaseModel):
    """Export configuration."""

    default_format: str = Field(
        default="csv", description="Default export format (csv or ankiconnect)"
    )
    ankiconnect: AnkiConnectConfig = Field(default_factory=AnkiConnectConfig)
    csv: CSVExportConfig = Field(default_factory=CSVExportConfig)

    @field_validator("default_format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate export format."""
        if v not in {"csv", "ankiconnect"}:
            raise ValueError("default_format must be 'csv' or 'ankiconnect'")
        return v


class StorageConfig(BaseModel):
    """Storage configuration."""

    database_path: str = Field(
        default="~/.local/share/ankification/cards.db",
        description="SQLite database path",
    )
    keep_history: bool = Field(default=True, description="Keep edit history")

    @field_validator("database_path")
    @classmethod
    def expand_path(cls, v: str) -> str:
        """Expand user path."""
        return str(Path(v).expanduser())


class Config(BaseModel):
    """Main configuration."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    tags: TagsConfig = Field(default_factory=TagsConfig)
    tui: TUIConfig = Field(default_factory=TUIConfig)
    export: ExportConfig = Field(default_factory=ExportConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    @classmethod
    def default(cls) -> "Config":
        """Create default configuration."""
        return cls()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump()
