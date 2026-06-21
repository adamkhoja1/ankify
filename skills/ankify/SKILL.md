---
name: ankify
description: Generate high-quality Anki flashcards from sources via a markdown-first, rubric-driven pipeline with a human review loop. Use when creating flashcards, study cards, Anki decks, or converting notes, papers, or documents into reviewable material.
allowed-tools: Read, Write, Edit, Glob, Bash, AskUserQuestion
---

# Ankify

Turn a source (paper, chapter, web page, transcript) plus the user's own notes into
high-quality spaced-repetition cards, through generation, rubric-driven self-review, and a
human review loop, then import into Anki.

This skill is backed by the `ankification` library (this repo). Run commands with
`uv run ankification <command>` from the repo root, or `ankification <command>` if installed.

## Principles

Read `principles.md` for the card-writing rubric (and `docs/RUBRIC.md` / `card_writing_advice/`
for depth). The essentials: cards must be **meaningful** (worth remembering long-term) and
**stable** (reliably recallable months later, in isolation). Apply stringency to the
**question**; the answer may add brief context. Atomic, single unambiguous answer,
self-contained, not yes/no, faithful to the source, concise. Prefer fewer excellent cards.

Cloze is allowed where a fill-in-the-blank on a specific term is the cleaner test; Basic Q&A
is the default. Reversible pairs only for true bidirectional associations.

## Process

### 1. Get the source into markdown first

Always convert to clean markdown before generating — extraction quality dominates card
quality.

- PDF / DOCX / EPUB / URL → use the **`to_md`** skill.
- A paper on arXiv → prefer LaTeX source over PDF: `uv run ankification` exposes
  `ankification.ingest.arxiv_to_markdown(arxiv_id)` (pandoc on the e-print), or use `to_md`.
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
  `uv run ankification seed cards.json --source-path source.md --notes "<scope>"`.
  Card JSON fields: `type` (`basic`|`cloze`|`reversible`), `front`, `back`, `cloze_text`
  (with `{{c1::...}}`), `extra`, `tags`, `source_ref`, `rationale`. Leave unused fields `""`.
- **Programmatic:** `uv run ankification generate --source-path source.md --notes "<scope>"`
  generates and self-reviews via the API into the session.

### 4. Human review loop

Launch the review web app and let the user flip through cards:

```
uv run ankification serve
```

They accept / edit / discard each card and can leave feedback. **Regenerate round** produces
a new round that keeps approved cards, drops what they discarded, and addresses their
feedback. Repeat until they approve the set (unless they asked for minimal input).

Be liberal about asking open-ended questions between rounds where it helps ("These came out
shallow — want more 'why/how' cards, or broader coverage?"), but only when it adds value.

### 5. Import into Anki

When the user approves, import the approved cards (Basic + Cloze) and sync:

```
uv run ankification push --deck "<Deck Name>"
```

Requires Anki open with the AnkiConnect add-on (code 2055492159). If Anki isn't running, the
session is saved — tell the user they can re-run `push` once Anki is open.

## Quality checklist (before surfacing cards)

- [ ] Tests one thing, one unambiguous answer
- [ ] Self-contained; question is source-anchored, not generic
- [ ] Not yes/no; demands recall, tests understanding where the source explains "why/how"
- [ ] Faithful to the source; concise; worth memorizing
- [ ] Cloze only where it's genuinely the cleaner test

## Iterating on this skill

The verification loop lives in `src/ankification/eval/`. Run
`uv run ankification eval --limit 10` (or `scripts/run_eval.py`) to score generation against
the validation set and calibrate the judge; see `docs/EVAL.md`.
