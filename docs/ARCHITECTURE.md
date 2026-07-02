# Architecture

For models working on this repo. See `SPEC.md` for the design rationale, `RESEARCH.md` for
the evidence base, `RUBRIC.md` for the card-quality rubric, `EVAL.md` for eval findings.

## Layout

```
src/ankify/
  models.py        pydantic: Card, CardType, CardSet, Source, Tier, ProbeName, Verdict, ReviewDecision
  config.py        global ModelConfig at ~/.config/ankify/config.json (chmod 600): provider/model/effort/key
  llm.py           LLM: provider-aware structured outputs (OpenAI + Anthropic) + thread-safe CostTracker
  rubric.py        Judge: five binary probes + holistic T0-T3 tier (grounded/ungrounded), run concurrently
  generate.py      Generator: generate(), augment(), self_review(); shared _PRINCIPLES
  ingest.py        markdown-first: from_file/from_text, url_to_markdown, arxiv_to_markdown (pandoc)
  anki.py          AnkiConnect client: decks, import_cards (Basic+Cloze, reversible->2 notes), sync
  export.py        genanki .apkg export: stable per-card GUIDs, deck::subdeck grouping, media bundling
  store.py         project-local .ankify/ store: sessions/sources/media/exports path resolution
  cli.py           fire CLI: seed | generate | serve | sessions | export | push | eval
  prompts/         vendored Memory Machines judge prompts (Apache-2.0; see NOTICE)
  eval/
    datasets.py    val-set loaders (Memory Machines live, needs the [eval] extra; QC + UG are stubs)
    harness.py     evaluate_generation, calibrate_judge, reference_ceiling, render_report
  server/
    session.py     ReviewSession (rounds + decisions) + SessionStore (atomic JSON) + SourceStore
    app.py         FastAPI: /api/session|decision|regenerate|decks|import|config|subdeck; serves the UI
frontend/          React + Vite review app (App.tsx); built to frontend/dist (committed), served by
                   FastAPI from the repo or from ankify/_frontend in a wheel install
skills/ankify/     the Claude Code skill (SKILL.md, principles.md, card_writing_advice/)
.claude-plugin/    plugin.json (marketplace manifest)
scripts/           smoke_judge.py, smoke_generate.py, run_eval.py, one-off migrations
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
Reports → `eval_runs/` (gitignored); if the budget runs out mid-run, a partial report is
still written (and says so). Needs `uv sync --extra eval` (the `datasets` dependency is
heavy and optional). To iterate: edit `generate._PRINCIPLES` or the prompts, re-run
`ankify eval`, diff reports.

## LLM layer

`LLM.parse(user, schema, system, effort)` returns a pydantic instance via the provider's
native structured outputs (OpenAI `chat.completions.parse`, Anthropic `messages.parse`).
Provider/model/effort/key come from `ModelConfig` (`config.py`), settable in the app's
settings panel; default is OpenAI `gpt-5.5` with `effort="high"`. `CostTracker` (thread-safe;
probes run concurrently) accumulates tokens/spend and raises `BudgetExceededError` at the
cap — the harness catches it and reports partial results.

## Conventions

Python 3.13 + uv; pydantic; fire CLI; pytest. Run `uv run ruff check --fix .` and
`uv run mypy .` before committing (strict, covers `src`/`tests`/`scripts`; `vendor/` and
`frontend/` are excluded). `uv run pytest` collects `tests/` only. Real-API runs live in
`scripts/` and `ankify eval`, not in the pytest suite (which stays offline and green).
After changing `frontend/src`, run `npm run build` in `frontend/` and commit the updated
`frontend/dist` (it is force-included in the wheel as `ankify/_frontend`).
