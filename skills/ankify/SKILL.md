---
name: ankify
description: Generate high-quality Anki flashcards from sources via a markdown-first, rubric-driven pipeline with a human review loop. Use when creating flashcards, study cards, Anki decks, or converting notes, papers, or documents into reviewable material.
allowed-tools: Read, Write, Edit, Glob, Bash, AskUserQuestion
---

# Ankify

Turn a source (paper, chapter, web page, transcript) plus the user's own notes into
high-quality spaced-repetition cards, through generation, rubric-driven self-review, and a
human review loop, then import into Anki.

This skill is backed by the `ankify` library (this repo). Run commands with
`uv run ankify <command>` from the repo root, or `ankify <command>` if installed.

## Principles

Read `principles.md` for the card-writing rubric (and `docs/RUBRIC.md` / `card_writing_advice/`
for depth). The essentials: cards must be **meaningful** (worth remembering long-term) and
**stable** (reliably recallable months later, in isolation). Apply stringency to the
**question**; the answer may add brief context. Atomic, single unambiguous answer,
self-contained, not yes/no, faithful to the source, concise. Prefer fewer excellent cards.

Cloze is allowed where a fill-in-the-blank on a specific term is the cleaner test; Basic Q&A
is the default. Reversible pairs only for true bidirectional associations.

## Where cards live

Cards persist in a **project-local store** under `.ankify/` in the working directory (not
synced anywhere by default), so each folder/project keeps its own decks:

```
.ankify/
  sessions/<name>.json    review state: cards + accept/edit/discard decisions (resumable)
  sources/<name>.json     content-addressed Source registry — the source TEXT, stored once
  media/                  images referenced by cards
  exports/<name>.apkg     accepted cards, rewritten continuously as the user reviews
```

Source text lives only in `sources/` (referenced from rounds by id), so it is never duplicated
across rounds and is **not** embedded in the session file — the session holds just the user's
own cards and decisions. This separation is what makes the git policy below clean.

Address a session by `--name <name>` (default `default`) — pick a short name per deck/topic
(e.g. `--name varian`). All commands below are per-`name`.

### Git policy for `.ankify/` (when source may be copyrighted)

The session (`sessions/`) is the user's own work and is usually safe and useful to version.
The `sources/` text, `media/` figures, and binary `exports/` are the parts that may be
copyrighted or heavy. **By default, write a `.ankify/.gitignore`** so those stay local while
the session can be committed:

```gitignore
# .ankify/.gitignore
sources/
media/
exports/
```

This is a judgment call you make in context — you should almost never need to ask:
- **Default to writing it** when the source could be copyrighted (textbooks, papers, articles).
- **Skip it** when the material clearly isn't copyrighted, or the store is clearly for private
  use where publishing source is fine.
- **Remove it (or narrow it)** when the user asks to commit the session/source/figures through
  the `.ankify/` folder — then track what they want and only ignore the rest (e.g. keep just
  `exports/` ignored, since the `.apkg` is binary and regenerable via `ankify export`).
- When genuinely unsure, lean toward including it; ask the user only in rare ambiguous cases.

The judge/generator **model** (OpenAI or Anthropic, model name, reasoning effort, API key) is
set once via the **gear icon** in the review app (top-right), stored at
`~/.config/ankify/config.json`; env vars (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`) are the
fallback.

## Process

### 1. Get the source into markdown first

Always convert to clean markdown before generating — extraction quality dominates card
quality.

- PDF / DOCX / EPUB / URL → use the **`to-md`** skill.
- A paper on arXiv → prefer LaTeX source over PDF: `uv run ankify` exposes
  `ankify.ingest.arxiv_to_markdown(arxiv_id)` (pandoc on the e-print), or use `to-md`.
- Already markdown/text → use as-is.

### 2. Clarify scope — only where it adds concrete value

The defaults below answer the generic questions, so ask the user only when a genuine choice
would change the cards. Good reasons to ask (use AskUserQuestion):

- The source is large or mixed — which sections/topics to cover or skip, and how deep.
- The user has existing cards to avoid duplicating, or a house style.
- Ambiguity about audience/level (intro vs. expert framing changes what's worth a card).
- Whether they want minimal input (just generate and import) or to review every card.

Do **not** ask generic questions the skill already answers (card format, what makes a good
card, whether to use cloze). If the user said "just make cards," generate and surface them
without interrogation.

### 3. Generate, then self-review (several rounds)

Generate candidate cards applying the principles, then **critique and rewrite the set
against the rubric before showing the user** — drop off-target/duplicate/low-value cards,
refactor vague or non-atomic ones, tighten wording. Do at least two review passes.

- **Interactive (recommended):** you (Claude) generate and self-review in-context, then write
  the approved-for-review cards as a JSON array of card objects and seed the review app:
  `uv run ankify seed cards.json --source-path source.md --name <name> --notes "<scope>"`.
  Seeding into an existing session *extends* it (carries prior cards + decisions forward, appends
  the new ones) — see "Resuming a review". **Pass `--source-path` for the cards you're seeding:**
  each seeded card is tagged with that source (stored once in `sources/`, referenced by id) so its
  origin stays recoverable. When a deck spans multiple sources/chapters, **seed (or generate) once
  per source** — a single seed can only tag its cards with one source, so batching several
  chapters into one seed leaves them unattributed. (`--source-path` is otherwise optional when
  extending an existing session.)
  Card JSON fields: `type` (`basic`|`cloze`|`reversible`), `front`, `back`, `cloze_text`
  (with `{{c1::...}}`), `extra`, `subdeck`, `tags`, `source_ref`, `rationale`. Leave unused
  fields `""`. For images, put files in `.ankify/media/` and reference them with a bare
  `<img src="figure.png">` (any format: png/jpg/svg).
  **Subdecks:** for larger / multi-section texts, set each card's `subdeck` **by default** to a
  clean chapter/section label (e.g. `Ch01 - The Market`) so cards land in Anki subdecks
  `<deck>::<subdeck>`; leave it empty for a single-topic source. Follow the user's grouping if
  they give one; ask only if genuinely ambiguous. Users can edit a card's subdeck in the review
  app.
- **Programmatic:** `uv run ankify generate --source-path source.md --name <name>
  --notes "<scope>"` generates and self-reviews via the API into the session.

### 4. Human review loop

Launch the review web app and let the user flip through cards:

```
uv run ankify serve --name <name>
```

They accept / edit / discard each card and can leave feedback. **Regenerate round** carries
forward pending and accepted cards, drops what they discarded, and adds cards from their
requests + revisions of cards discarded with feedback. Repeat until they approve the set
(unless they asked for minimal input). Accepted cards stream into
`.ankify/exports/<name>.apkg` as they go.

Be liberal about asking open-ended questions between rounds where it helps ("These came out
shallow — want more 'why/how' cards, or broader coverage?"), but only when it adds value.

### 5. Get the cards into Anki

Accepted cards are written **continuously** to `.ankify/exports/<name>.apkg` — **no AnkiConnect
needed**. The user imports by clicking **"Download accepted .apkg"** in the review app (or
grabbing `.ankify/exports/<name>.apkg` directly) and double-clicking it / File → Import in Anki.
The package carries Basic + Cloze + images and is GUID-stable, so re-importing an updated
package **updates** notes instead of duplicating.

Optional live one-click sync (needs Anki open with the AnkiConnect add-on, code 2055492159):
the app's "Import approved → Anki" button, or `uv run ankify push --name <name> --deck
"<Deck>"`.

## Resuming a review

Card sets persist, so the user can stop and return any time. To pick up where they left off:

```
uv run ankify sessions            # list sessions: name, accepted, pending
uv run ankify serve --name <name>   # reopen the review app in the browser
```

When the user says "let's keep working on my <topic> cards," run `ankify sessions` to
find the set, then `serve --name <name>` to reopen the frontend for them.

**Extending is non-destructive.** Re-running `seed` (or `generate`) against an existing session
*adds* a round: the current cards and their accept/edit/discard decisions are carried forward
and the new cards appended, so previously accepted cards and the accepted `.apkg` are preserved.
Use this to grow a deck (e.g. add chapter 4 to a session that already covers 1–3) without
re-reviewing earlier cards. A source (`--source-path`/`--text`) is only required when *creating*
a new session — when extending, `seed` reuses the session's recorded source. Pass `--replace`
only when you deliberately want to discard the carried-forward set and start the working round
from just the new cards.

## Quality checklist (before surfacing cards)

- [ ] Tests one thing, one unambiguous answer
- [ ] Self-contained; question is source-anchored, not generic
- [ ] Not yes/no; demands recall, tests understanding where the source explains "why/how"
- [ ] Faithful to the source; concise; worth memorizing
- [ ] Cloze only where it's genuinely the cleaner test

## Iterating on this skill

The verification loop lives in `src/ankify/eval/`. Run
`uv run ankify eval --limit 10` (or `scripts/run_eval.py`) to score generation against
the validation set and calibrate the judge; see `docs/EVAL.md`.
