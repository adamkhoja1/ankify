"""Run the verification loop on the validation set and write a report.

Usage: uv run scripts/run_eval.py --limit 10 --budget 15
Real API spend (GPT-5.5, high reasoning). Writes eval_runs/<timestamp>.md.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import fire

from ankify.eval.datasets import load_memory_machines
from ankify.eval.harness import (
    calibrate_judge,
    evaluate_generation,
    reference_ceiling,
    render_report,
)
from ankify.generate import Generator
from ankify.llm import LLM, BudgetExceededError, CostTracker
from ankify.rubric import Judge


def main(
    limit: int = 10,
    budget: float = 15.0,
    split: str = "test",
    calib_candidates: int = 15,
    ceiling_cards: int = 10,
    review_rounds: int = 1,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    tracker = CostTracker(budget_usd=budget)
    llm = LLM(tracker=tracker)
    generator = Generator(llm)
    judge = Judge(llm)

    items = load_memory_machines(split=split, limit=limit)
    print(f"loaded {len(items)} val items")

    calib = ceiling = None
    try:
        _, gen_metrics = evaluate_generation(items, generator, judge, review_rounds=review_rounds)
        calib = calibrate_judge(items, judge, max_candidates=calib_candidates)
        ceiling = reference_ceiling(items, judge, max_cards=ceiling_cards)
    except BudgetExceededError as exc:
        print(f"\n!! stopped early: {exc}")
        gen_metrics = getattr(main, "_partial", None) or _empty_metrics()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    report = render_report(
        dataset="Memory Machines (srs-prompts)",
        gen=gen_metrics,
        calib=calib,
        ceiling=ceiling,
        tracker=tracker,
        timestamp=timestamp,
    )
    out_dir = Path("eval_runs")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    out_path.write_text(report)
    print("\n" + report)
    print(f"written: {out_path}")


def _empty_metrics():
    from ankify.eval.harness import GenMetrics

    return GenMetrics()


if __name__ == "__main__":
    fire.Fire(main)
