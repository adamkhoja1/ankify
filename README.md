# Ankification

Library and CLI tool for creating spaced repetition flashcards from content using LLMs.

## Features

- 📚 **Multiple Content Sources**: URLs, PDFs, EPUBs, text files, or direct text input
- 🤖 **LLM-Powered**: Generate high-quality cards using OpenAI (GPT-4) or Anthropic (Claude)
- 🎴 **Multiple Card Types**: Both basic (front/back) and cloze deletion cards
- ✏️ **AI-Assisted Editing**: Refine cards with natural language feedback
- 💾 **Persistent Storage**: SQLite database with full edit history
- 📤 **Flexible Export**: CSV files or direct sync to Anki via AnkiConnect
- 🏷️ **Tagging System**: Organize cards with configurable tag pools
- ⚙️ **Fully Configurable**: YAML configuration with environment variable support

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ankification.git
cd ankification

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Add uv to your PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Complete User Guide

### Step-by-Step Setup (For Non-Technical Users)

#### Step 1: Install Prerequisites

Before you begin, you need:
1. A computer with macOS, Linux, or Windows
2. An OpenAI account OR Anthropic account (for the AI that generates cards)
3. About 10-15 minutes

**Getting an API Key:**

**Option A - OpenAI (GPT-4):**
1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Click on your profile → "View API Keys"
4. Click "Create new secret key"
5. Copy the key (starts with `sk-...`) - you'll need this later!
6. You'll need to add billing info (typically ~$0.01-0.10 per article)

**Option B - Anthropic (Claude):**
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Go to "API Keys" in settings
4. Create a new key
5. Copy the key - you'll need this later!

#### Step 2: Install Ankification

Open Terminal (Mac/Linux) or Command Prompt (Windows) and run these commands one at a time:

```bash
# 1. Install uv (a fast Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone (download) the ankification code
git clone https://github.com/yourusername/ankification.git
cd ankification

# 3. Install all required components
uv sync

# 4. Make the 'ankification' command available everywhere
# For Mac/Linux with zsh:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# For Mac/Linux with bash:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

After running these commands, restart your terminal.

#### Step 3: Configure Your API Key

```bash
# Create the configuration file
ankification config init
```

This creates a file at `~/.config/ankification/config.yaml`. Now you need to edit it:

**Mac/Linux:**
```bash
# Open in default text editor
open ~/.config/ankification/config.yaml
```

**Or manually navigate to:**
- Mac: Go to Finder → Go menu (hold Option key) → Library → .config → ankification → config.yaml
- Linux: `~/.config/ankification/config.yaml`

**Edit the file** to add your API key. Find these lines and update them:

```yaml
llm:
  default_provider: openai  # Change to "anthropic" if using Claude
  openai:
    api_key: sk-your-actual-key-here  # Paste your OpenAI key here
  anthropic:
    api_key: sk-ant-your-key-here     # OR paste your Anthropic key here
```

**Tip:** You can also use environment variables (more secure):
```bash
# Add to your ~/.zshrc or ~/.bashrc
export OPENAI_API_KEY="sk-your-actual-key-here"
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
```

Then in the config file, keep:
```yaml
openai:
  api_key: ${OPENAI_API_KEY}
```

#### Step 4: Generate Your First Flashcards!

Let's start with a simple example - a Wikipedia article:

```bash
ankification generate https://en.wikipedia.org/wiki/Photosynthesis
```

This will:
1. Download the article
2. Send it to the AI (OpenAI or Anthropic)
3. Generate flashcards automatically
4. Show you how many cards were created
5. Save them to a CSV file in `~/Documents/Anki/`

**You'll see output like:**
```
Generating cards from 1 source(s)...

✓ Generated 12 cards
  - 8 basic card(s)
  - 4 cloze card(s)

Interactive review is not yet implemented. All cards marked as accepted.

Exporting 12 accepted card(s)...
✓ Exported to: /Users/yourname/Documents/Anki/anki_cards_20240115_143022.csv

✓ Done!
```

#### Step 5: Import into Anki

**Option A - CSV Import (Easiest):**

1. Open Anki
2. Click "File" → "Import"
3. Navigate to `~/Documents/Anki/` and select the CSV file
4. Anki will ask you to map the fields:
   - Field 1 → Front
   - Field 2 → Back
   - Field 3 → Tags
5. Click "Import"
6. Done! Your flashcards are now in Anki

**Option B - AnkiConnect (Direct sync):**

1. In Anki, install the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) addon:
   - Tools → Add-ons → Get Add-ons
   - Code: `2055492159`
   - Restart Anki

2. Keep Anki running, then generate cards with:
   ```bash
   ankification generate https://example.com --export-format ankiconnect
   ```

3. Cards appear directly in your deck - no manual import needed!

### Common Use Cases

#### Use Case 1: Study from PDF Textbooks

```bash
# Generate flashcards from a PDF chapter
ankification generate ~/Documents/biology_chapter3.pdf \
  --count-guidance "around 25 cards" \
  --card-types basic
```

#### Use Case 2: Learn from Online Articles

```bash
# Multiple articles on the same topic
ankification generate \
  https://example.com/intro-to-ml \
  https://example.com/neural-networks \
  https://example.com/deep-learning \
  --provider anthropic
```

#### Use Case 3: Create Cards from Your Notes

```bash
# From your markdown notes
ankification generate ~/Notes/lecture_notes.md
```

#### Use Case 4: EPUB Books

```bash
# From an ebook
ankification generate ~/Books/learning_python.epub \
  --count-guidance "comprehensive - cover all key concepts"
```

### Managing Your Cards

#### Add Tags for Organization

Before generating, set up your tag categories:

```bash
# Add tags you'll use often
ankification tags add biology chemistry physics math programming

# See your tags
ankification tags list
```

#### View Past Sessions

```bash
# See what you've generated before
ankification list-sessions

# This shows:
# - Session ID (for exporting later)
# - When it was created
# - What sources were used
```

#### Re-export Old Sessions

```bash
# Export a specific session again
ankification list-sessions  # Get the session ID
ankification export --session abc-123-def-456

# Or export everything marked as accepted
ankification export
```

### Customizing Your Experience

#### Change the Number of Cards Generated

```bash
# Generate fewer cards (key concepts only)
ankification generate article.pdf --count-guidance "around 10 cards, only the most important"

# Generate more comprehensive coverage
ankification generate article.pdf --count-guidance "comprehensive - cover all details"

# Or be specific
ankification generate article.pdf --count-guidance "exactly 15 cards"
```

#### Choose Card Types

```bash
# Only basic (front/back) cards
ankification generate article.pdf --card-types basic

# Only cloze deletion cards
ankification generate article.pdf --card-types cloze

# Mix of both (default)
ankification generate article.pdf --card-types basic --card-types cloze
```

#### Switch Between OpenAI and Claude

```bash
# Use Claude (Anthropic)
ankification generate article.pdf --provider anthropic

# Use GPT-4 (OpenAI)
ankification generate article.pdf --provider openai
```

#### Add Persistent Preferences

Edit `~/.config/ankification/config.yaml`:

```yaml
generation:
  user_directives:
    - Keep cards concise and clear
    - Focus on practical applications
    - Include examples when relevant
    - Avoid overly technical jargon
```

These instructions will be included with every card generation request!

### Troubleshooting

#### "Command not found: ankification"

**Solution:** Add uv to your PATH:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

#### "OpenAI API key not configured"

**Solution:** Either:
1. Edit `~/.config/ankification/config.yaml` and add your key directly
2. Set environment variable: `export OPENAI_API_KEY="your-key"`

#### "Failed to connect to AnkiConnect"

**Solution:**
1. Make sure Anki is running
2. Install AnkiConnect addon (code: 2055492159)
3. Restart Anki

#### Generated cards are too technical/simple

**Solution:** Add user directives in config:
```yaml
generation:
  user_directives:
    - Use simple, beginner-friendly language
    - Explain technical terms
```

Or use count guidance:
```bash
ankification generate article.pdf --count-guidance "15 cards for a beginner"
```

#### Cards don't import correctly to Anki

**Solution for CSV import:**
1. In Anki import dialog, make sure:
   - "Fields separated by: Semicolon"
   - "Allow HTML in fields" is checked
   - Field mapping: 1→Front, 2→Back, 3→Tags

### Tips for Best Results

1. **Start with shorter content** - Try a single article before a whole book
2. **Review the config file** - The generated `config.yaml` has helpful comments
3. **Use specific guidance** - Instead of "some cards", say "around 15 cards focusing on key concepts"
4. **Experiment with providers** - Try both OpenAI and Claude to see which you prefer
5. **Organize with tags** - Set up your tag system before generating lots of cards
6. **Check export location** - Cards are saved to `~/Documents/Anki/` by default (configurable)

## CLI Commands

### `generate`

Generate flashcards from one or more sources.

```bash
ankification generate [OPTIONS] SOURCES...

Options:
  -p, --provider [openai|anthropic]  LLM provider to use
  -c, --count-guidance TEXT          Guidance for number of cards
  -t, --card-types [basic|cloze]     Types of cards to generate (can specify multiple)
  -e, --export-format [csv|ankiconnect]  Export format
  --no-review                        Skip interactive review (auto-accept all)
```

**Examples:**

```bash
# Generate from URL with Claude
ankification generate https://example.com -p anthropic

# Generate around 20 basic cards
ankification generate article.txt -c "around 20" -t basic

# Generate mixed cards and export to Anki
ankification generate paper.pdf -t basic -t cloze -e ankiconnect
```

### `config`

Manage configuration.

```bash
# Initialize config file
ankification config init

# Show current configuration
ankification config show

# Set a config value
ankification config set llm.default_provider anthropic
ankification config set generation.count_guidance "around 15"
```

### `tags`

Manage tag pools.

```bash
# Add tags
ankification tags add machine-learning AI neural-networks

# List tags
ankification tags list

# Remove tag
ankification tags remove outdated-tag
```

### `list-sessions`

List recent generation sessions.

```bash
# List last 10 sessions
ankification list-sessions

# List last 20 sessions
ankification list-sessions -n 20
```

### `export`

Export cards from previous sessions.

```bash
# Export all accepted cards
ankification export

# Export specific session
ankification export -s <session-id>

# Export to AnkiConnect
ankification export -f ankiconnect

# Export only draft cards
ankification export --status draft
```

## Configuration

The configuration file is located at `~/.config/ankification/config.yaml`.

### Full Configuration Example

```yaml
llm:
  default_provider: openai
  openai:
    api_key: ${OPENAI_API_KEY}
    model: gpt-4-turbo-preview
    temperature: 0.7
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    model: claude-3-5-sonnet-20241022
    temperature: 0.7

generation:
  card_types:
    - basic
    - cloze
  auto_determine_count: true
  count_guidance: null  # or "around 20", "comprehensive", etc.
  user_directives:
    - Keep cards concise
    - Focus on key concepts

tags:
  pools:
    - programming
    - python
    - biology
  auto_tag: true
  prompt_for_tags: true

tui:
  keybindings:
    next: j
    prev: k
    accept: a
    reject: d
    edit: e
    refine: r
    quit: q
    help: "?"
  show_shortcuts: true

export:
  default_format: csv
  ankiconnect:
    url: http://localhost:8765
    deck: Default
  csv:
    output_dir: ~/Documents/Anki

storage:
  database_path: ~/.local/share/ankification/cards.db
  keep_history: true
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=ankification --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_fetchers.py

# Run with verbose output
uv run pytest -v
```

### Project Structure

```
ankification/
├── src/ankification/
│   ├── cards/           # Card models and generation
│   ├── config/          # Configuration management
│   ├── export/          # Export to CSV and AnkiConnect
│   ├── fetchers/        # Content fetching from various sources
│   ├── llm/             # LLM provider integrations
│   ├── storage/         # SQLite database operations
│   ├── tui/             # Terminal UI (in progress)
│   └── cli.py           # CLI interface
├── tests/
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── ARCHITECTURE.md      # Detailed architecture documentation
└── README.md            # This file
```

### Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed information about:
- Module structure and responsibilities
- Data flow
- Design decisions
- Database schema
- Implementation phases

## Supported Input Formats

- **URLs**: Web articles and documentation
- **PDF**: Portable Document Format files
- **EPUB**: Electronic publications and ebooks
- **Text files**: `.txt`, `.md`, `.markdown`, `.rst`
- **Direct text**: Pipe or paste content directly

## Export Formats

### CSV

Creates semicolon-delimited CSV files compatible with Anki's import feature.

**Basic cards format:**
```
Front;Back;Tags
```

**Cloze cards format:**
```
Text with {{c1::cloze}} deletions;Tags
```

### AnkiConnect

Directly syncs cards to a running Anki instance using the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) addon.

**Requirements:**
1. Anki must be running
2. AnkiConnect addon must be installed
3. Default configuration works for most setups

## Roadmap

### Completed ✅
- Core architecture and module structure
- Configuration system with YAML support
- Content fetchers for URL, PDF, EPUB, text
- LLM providers (OpenAI and Anthropic)
- Card generation and editing
- SQLite storage with edit history
- CSV and AnkiConnect export
- CLI interface with all basic commands
- Comprehensive unit tests (95 passing)

### In Progress 🚧
- Interactive TUI for card review and editing
- Additional tests for LLM and export components

### Planned 🔮
- Integration tests
- Adaptive prompting (learn from user feedback)
- Batch processing improvements
- Additional export formats
- Web UI option
- Plugin system for custom fetchers and exporters

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Built with [Click](https://click.palletsprojects.com/) for CLI
- [Textual](https://textual.textualize.io/) for TUI
- [Pydantic](https://docs.pydantic.dev/) for configuration validation
- [uv](https://github.com/astral-sh/uv) for fast package management
