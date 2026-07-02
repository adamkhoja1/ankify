# ankify

Generate high-quality spaced-repetition (Anki) flashcards from a source, with a
rubric-driven review loop and an eval harness. Also packages the `ankify` Claude Code skill
(`skills/ankify/`), linked into the cais marketplace.

The pipeline is markdown-first: convert a source to clean markdown, generate candidate
cards, self-review them against a card-quality rubric, review them in a small web app
(accept / edit / discard / give feedback → regenerate), and import the approved cards into
Anki. The same rubric powers an eval harness that scores generation against a validation set
and calibrates the LLM judge against human labels.

## Setup

```bash
uv sync
```

Set an LLM key in the environment (`OPENAI_API_KEY` for GPT-5.5, the current default, or
`ANTHROPIC_API_KEY`); the provider, model, and key can also be set in the review app's
settings panel. Anki import needs Anki open with the AnkiConnect add-on (code 2055492159).

## Usage

```bash
# Generate + self-review cards from a markdown source into a review session
uv run ankify generate --source-path paper.md --notes "focus on the method"

# Or seed the review app with cards you generated yourself (JSON array of card objects)
uv run ankify seed cards.json --source-path paper.md

# Review in the browser: flip, accept/edit/discard, leave feedback, regenerate a round
uv run ankify serve

# Import the approved cards into Anki and sync
uv run ankify push --deck "My Deck"

# Run the verification loop on the validation set (needs `uv sync --extra eval` once)
uv run ankify eval --limit 10
```

See `docs/ARCHITECTURE.md` for the design and `docs/RUBRIC.md` for the card-quality rubric.
