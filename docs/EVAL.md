# Eval findings

The verification loop (`scripts/run_eval.py`, `src/ankification/eval/`) generates cards for
val sources, grounded-judges them against reference decks, and calibrates the judge against
human tier labels. Reports are written to `eval_runs/` (gitignored).

## Run 1 — Memory Machines, N=3 (2026-06-21)

- **Generation:** 50% usable; tiers `{T0:3, T2:1, T3:2}`. The T0 (off-target) cards revealed
  a targeting mismatch: MM val items are single *highlights*, but the generator targeted the
  broader topic. **Fix applied:** `Generator.generate` now targets the excerpt precisely when
  `source.kind == "highlight"`. (For real full-source ankification, broad coverage is correct.)
- **Reference ceiling:** 100% usable — expert cards are on-target by construction.
- **Judge calibration:** exact tier agreement 50%, but **usable-vs-unusable accuracy 100%**.
  Confusion was only T0->T1 (both unusable). The judge reliably makes the usable/not decision;
  like Matuschak found, the hard call is T1-vs-polish, not the usable boundary.
- Cost: ~$0.74 / 96 calls (GPT-5.5, high effort).

## How to iterate

Change `generate._PRINCIPLES` or the prompts, then `uv run scripts/run_eval.py --limit N`
and diff the new report against the prior one. Watch `usable_frac`, the T0 rate (targeting),
and per-probe failure rates (construction). Calibration guards against the judge drifting.
