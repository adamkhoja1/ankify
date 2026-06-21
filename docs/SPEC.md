# ankification — design spec

Status: **draft, pending sign-off.** See `docs/RESEARCH.md` for the evidence base and
`docs/RUBRIC.md` (to be written) for the implementable rubric.

## Goal

Turn a source (paper, chapter, web page, transcript) plus the user's own notes into a set
of high-quality spaced-repetition cards, through a loop of LLM generation, rubric-driven
self-review, and human approval — then import into Anki. The same rubric powers an **eval
harness** we actually run to iterate the generator against a validation set.

The skill lives here (in `~/Projects/ankification`) and is linked into the
`cais_informal_marketplace` marketplace by git URL, mirroring `to_md`.

## Principles (from research)

- **Markdown first.** Always convert the source to clean markdown before generating
  (via the `to_md` skill; or pandoc on LaTeX source — e.g. arXiv `e-print` tarballs —
  when that yields cleaner output than PDF).
- **Stringency on the question, latitude on the answer.** The question must be atomic,
  unambiguous, self-contained, and effortful; the answer may elaborate.
- **The hard failure is T1** (plausible-but-broken). Self-review targets it explicitly via
  the five probes (lacks-context, multiple-responses, shallow, wordy, narrow).
- **Grounded evaluation.** Judge generated cards against expert reference cards for the
  same source, not in a vacuum.
- **Cloze is allowed** where a fill-in-the-blank/atomic-fact pattern is genuinely better;
  Basic Q&A is the default. Reversible pairs for true bidirectional associations.

## Repo layout (flat, per code-preferences)

```
ankification/
  .claude-plugin/plugin.json        # marketplace plugin manifest (mirrors to_md)
  skills/ankify/SKILL.md            # the skill, moved out of cais_informal_marketplace
  skills/ankify/principles.md       # condensed card-writing guidance (kept in sync w/ rubric)
  src/ankification/
    models.py            # pydantic: Card, CardType, CardSet, Source, RubricScore, Verdict...
    ingest.py            # source -> clean markdown (to_md / pandoc-arxiv); chunking
    generate.py          # markdown + notes -> candidate cards (Anthropic)
    selfreview.py        # multi-round rubric critique; refine or drop before surfacing
    rubric.py            # rubric as data + LLM judge (grounded + ungrounded)
    anki.py              # AnkiConnect client: decks, addNotes (Basic+Cloze), dedupe, sync
    llm.py               # thin Anthropic/OpenAI client wrapper, model config, .env keys
    eval/
      datasets.py        # val-set loaders: Memory Machines (HF), Quantum Country, Ultimate Geo
      harness.py         # generate -> grounded-judge -> metrics; iteration reports
      report.py          # tier distribution, usable%, probe-failure rates vs reference
    server/app.py        # FastAPI: serve a card set, accept/edit/discard/feedback, regen, import
    cli.py               # fire CLI: generate | review | eval | import | serve
  frontend/              # React + Vite + TS card-review app (built assets served by FastAPI)
  docs/                  # SPEC, RESEARCH, RUBRIC, ARCHITECTURE
  tests/                 # pytest; integration tests hit real AnkiConnect + real LLM (no mocks)
```

## Data model (pydantic)

- `CardType = basic | cloze | reversible`
- `Card{ type, front, back, cloze_text?, tags[], source_ref, rationale? }`
- `CardSet{ source: Source, cards: [Card], round: int }`
- `Source{ title, kind, markdown, uri? }`
- `RubricScore{ criterion, score, reason }`; `Verdict{ tier: T0..T3, scores[], usable: bool }`
- `ReviewDecision{ card_id, action: accept|edit|discard, edited_card?, feedback? }`

## Pipeline

1. **Clarify** (skill-driven) — ask only value-adding questions (scope, depth, which deck,
   cloze appetite, must-cover/skip). Generic answers are baked into the skill.
2. **Ingest** — `ingest.py` → clean markdown. Prefer arXiv LaTeX→pandoc when available.
3. **Generate** — `generate.py` produces candidate cards with rationales.
4. **Self-review** — `selfreview.py` runs N rounds: score each card on the rubric/probes,
   refine T1/T2 cards, drop T0 and unfixable ones. Only survivors surface.
5. **Human review** — `cli serve` launches FastAPI+React; user flips cards and
   accepts/edits/discards/leaves feedback. Feedback + discards spawn a new generation round
   scoped to the gaps. Repeat until the user approves the set (or asks to stop).
6. **Import** — `anki.py` writes approved cards (Basic+Cloze) via AnkiConnect, dedupes, syncs.

## Eval harness (the verification loop)

- `cli eval` runs: for each val source → ingest → generate → self-review → **grounded judge**
  each card (tier T0–T3 + probe scores) against the reference deck → metrics.
- Metrics: % usable (T2+T3), tier distribution, per-probe failure rates, mean rubric score;
  reference deck judged the same way as the ceiling. Memory Machines datasets give human
  labels to calibrate our judge against (κ vs human tiers).
- Output: a markdown report per run under `eval_runs/` (gitignored), diffed across iterations
  so we can see whether prompt/principle changes move usable% up.
- **Run for real, bounded.** A run is capped (configurable N sources × M cards); spend is
  estimated up front and reported.

## Backend + frontend

- FastAPI serves the built React app and a small JSON API (get set, post decisions, post
  feedback→regen, post import). State is a working card set on disk (a run dir), so a review
  session is resumable and the CLI/skill and UI share it.
- React: one card centered, click/space to flip, keys for accept/edit/discard, a feedback box,
  a "regenerate round" button, and progress. Plain, fast, no heavy UI deps.

## Skill (SKILL.md) posture

- Markdown-first instruction with `to_md`/pandoc guidance.
- A clarifying-questions section: ask open-ended scope/quality questions liberally **only
  where they add concrete value**; the default flow needs no questions.
- Orchestrates the library CLI; explains the human-in-the-loop review app.
- Cloze permitted; Basic default. Quality checklist replaced by the rubric.

## Model & cost defaults (for sign-off)

- Generation + self-review + judge default to **Claude** (Anthropic), per code-preferences.
  Proposed: generation/self-review on a strong mid-tier (cost-aware) model, judging on the
  same or one tier up. Exact model + the eval-run spend ceiling are sign-off questions.
- OpenAI key is also present; used only if we want a second judge for agreement checks.

## Testing

- pytest, TDD. Unit tests for rubric scoring shape, cloze parsing, card models, ingest
  chunking. Integration tests (no mocks) for: AnkiConnect import round-trip (Basic+Cloze),
  a real generate→self-review pass on a tiny fixture, and a real grounded-judge call.
  Structural coverage (boundary/equivalence) for parsing and rubric aggregation.

## Marketplace linking

- Add `.claude-plugin/plugin.json` (name `ankify`) + move `skills/ankify/`.
- Push `ankification` to GitHub; change the `ankify` entry in
  `cais_informal_marketplace/.claude-plugin/marketplace.json` from `./plugins/ankify` to the
  `git@github.com:...` URL, matching `to_md`. Remove the old in-repo `plugins/ankify/`.

## Decisions (signed off)

1. **Model + eval spend ceiling** — **GPT-5.5** (`gpt-5.5`, via the available
   `OPENAI_API_KEY`; no Anthropic key was present) for generation and judging, both at
   **high** reasoning effort; lower effort for incidental calls. First real eval run
   bounded by a CostTracker (token-based; ~$15 ceiling). The `LLM` interface is
   provider-agnostic so an Anthropic/Opus backend can be swapped in later.
2. **Val-set scope** — **core 3**: Memory Machines datasets + Quantum Country + Ultimate
   Geography. AnKing/Japanese excluded for now (gated/copyrighted).
3. **Rubric prompts** — **adapt the Apache-2.0 Memory Machines judge prompts** (T0–T3 tiering
   + 5 probes) with NOTICE/attribution, aligned to `docs/RUBRIC.md`.
