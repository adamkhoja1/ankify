# Eval findings

The verification loop (`scripts/run_eval.py`, `src/ankify/eval/`) generates cards for
val sources, grounded-judges them against reference decks, and calibrates the judge against
human tier labels. Reports are written to `eval_runs/` (gitignored).

## Run 1 — Memory Machines, N=3 (2026-06-21)

- **Generation:** 50% usable; tiers `{T0:3, T2:1, T3:2}`. The T0 (off-target) cards revealed
  a targeting mismatch: MM val items are single *highlights*, but the generator targeted the
  broader topic. **Fix applied:** `Generator.generate` now targets the excerpt precisely when
  `source.kind == "highlight"`. (For real full-source ankify, broad coverage is correct.)
- **Reference ceiling:** 100% usable — expert cards are on-target by construction.
- **Judge calibration:** exact tier agreement 50%, but **usable-vs-unusable accuracy 100%**.
  Confusion was only T0->T1 (both unusable). The judge reliably makes the usable/not decision;
  like Matuschak found, the hard call is T1-vs-polish, not the usable boundary.
- Cost: ~$0.74 / 96 calls (GPT-5.5, high effort).

## Run 2 — Memory Machines, N=8 (2026-06-21, post targeting-fix)

Re-ran after the highlight-targeting fix from run 1:

- **Generation:** usable jumped **50% → 95%**; off-target (T0) rate fell **50% → 5%** (1/19).
  Tiers `{T0:1, T2:7, T3:11}`. Now on par with the expert reference ceiling (90% usable).
- **Open lever:** "clean" is only 26% — the `shallow` probe fires on 10/19. Cards are usable
  but could go deeper; tuning `_PRINCIPLES` toward explanatory depth is the next iteration.
- **Judge calibration (N=16):** usable-vs-unusable accuracy 88%, exact-tier agreement 25%.
  The judge compresses toward the middle vs human extremes — fine for relative iteration,
  worth tuning for absolute calibration.
- Cost: ~$2.46 / 286 calls.

The loop caught a real defect, the fix was verified by re-running — that is the workflow.

## How to iterate

Change `generate._PRINCIPLES` or the prompts, then `uv run scripts/run_eval.py --limit N`
and diff the new report against the prior one. Watch `usable_frac`, the T0 rate (targeting),
and per-probe failure rates (construction). Calibration guards against the judge drifting.
