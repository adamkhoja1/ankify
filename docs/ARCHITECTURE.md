# Architecture

For models working on this repo. See `SPEC.md` for the design rationale, `RESEARCH.md` for
the evidence base, `RUBRIC.md` for the card-quality rubric, `EVAL.md` for eval findings.

## Layout

```
src/ankify/
  models.py        pydantic: Card, CardType, CardSet, Source, Tier, ProbeName, Verdict, ReviewDecision
  llm.py           LLM (OpenAI/GPT-5.5 structured outputs via chat.completions.parse) + CostTracker
  rubric.py        Judge: five binary probes + holistic T0-T3 tier (grounded/ungrounded)
  generate.py      Generator: generate() and self_review(); shared _PRINCIPLES
  ingest.py        markdown-first: from_file/from_text, url_to_markdown, arxiv_to_markdown (pandoc)
  anki.py          AnkiConnect client: decks, import_cards (Basic+Cloze, reversible->2 notes), sync
  cli.py           fire CLI: seed | generate | serve | push | eval
  prompts/         vendored Memory Machines judge prompts (Apache-2.0; see NOTICE)
  eval/
    datasets.py    val-set loaders (Memory Machines live; QC + Ultimate Geography are stubs)
    harness.py     evaluate_generation, calibrate_judge, reference_ceiling, render_report
  server/
    session.py     ReviewSession (rounds + decisions) + SessionStore (JSON persistence)
    app.py         FastAPI: /api/session|decision|regenerate|decks|import + serves frontend/dist
frontend/          React + Vite review app (App.tsx); built to frontend/dist, served by FastAPI
skills/ankify/     the Claude Code skill (SKILL.md, principles.md, card_writing_advice/)
.claude-plugin/    plugin.json (marketplace manifest)
scripts/           smoke_judge.py, smoke_generate.py, run_eval.py
```

## Data flow

1. **Ingest** (`ingest`) → `Source` (markdown).
2. **Generate** (`generate.Generator.generate`) → `CardSet` of candidate `Card`s. Highlight
   sources are targeted precisely; full sources get broad coverage.
3. **Self-review** (`generate.Generator.self_review`) → N holistic critique-and-rewrite rounds.
4. **Human review** — cards land in a `ReviewSession` (`server/session`); the React app over
   `server/app` records accept/edit/discard/feedback; `_regenerate` produces a new round that
   keeps approved cards, drops discards, and addresses feedback.
5. **Import** (`anki.AnkiConnect.import_cards`) → Basic/Cloze notes, dedup, sync.

## Eval (the verification loop)

`eval/harness` generates cards for val sources, **grounded-judges** them against reference
decks (`rubric.Judge`), and **calibrates** the judge against human tier labels. Metrics:
% usable (T2+T3), tier distribution, per-probe failure rates, exact/usable agreement vs human.
Reports → `eval_runs/` (gitignored). To iterate: edit `generate._PRINCIPLES` or the prompts,
re-run `ankify eval`, diff reports.

## LLM layer

`LLM.parse(user, schema, system, effort)` returns a pydantic instance via OpenAI structured
outputs. Default model `gpt-5.5`; generation and judging use `effort="high"`. `CostTracker`
accumulates tokens/spend and raises `BudgetExceededError` at the cap. The interface is
provider-agnostic — an Anthropic/Opus backend can be swapped in `llm.py` without touching
callers (an Anthropic key was not available this session; see SPEC decision 1).

## Conventions

Python 3.13 + uv; pydantic; fire CLI; pytest. Run `uv run ruff check --fix .` and
`uv run mypy .` before committing. Real-API runs live in `scripts/` and `ankify eval`,
not in the pytest suite (which stays offline and green).
