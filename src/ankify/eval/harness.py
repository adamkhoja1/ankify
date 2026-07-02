"""The verification loop: generate cards for val sources, grounded-judge them, and
calibrate the judge against human tier labels. Produces metrics used to iterate the
generator/principles. See docs/SPEC.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ..generate import Generator
from ..llm import BudgetExceededError, CostTracker
from ..models import Card, Verdict
from ..rubric import Judge
from .datasets import ValItem

logger = logging.getLogger(__name__)


@dataclass
class GenResult:
    item_id: str
    judged: list[tuple[Card, Verdict]] = field(default_factory=list)


@dataclass
class GenMetrics:
    n_items: int = 0
    n_cards: int = 0
    usable: int = 0
    clean: int = 0
    tier_counts: dict[str, int] = field(default_factory=dict)
    probe_fail: dict[str, int] = field(default_factory=dict)

    @property
    def usable_frac(self) -> float:
        return self.usable / self.n_cards if self.n_cards else 0.0

    @property
    def clean_frac(self) -> float:
        return self.clean / self.n_cards if self.n_cards else 0.0


@dataclass
class CalibResult:
    n: int = 0
    exact: int = 0  # our tier == human tier
    usable_correct: int = 0  # our usable == human usable
    confusion: dict[str, int] = field(default_factory=dict)  # "human->ours"

    @property
    def exact_agreement(self) -> float:
        return self.exact / self.n if self.n else 0.0

    @property
    def usable_accuracy(self) -> float:
        return self.usable_correct / self.n if self.n else 0.0


def evaluate_generation(
    items: list[ValItem],
    generator: Generator,
    judge: Judge,
    count_hint: int = 2,
    review_rounds: int = 1,
) -> tuple[list[GenResult], GenMetrics]:
    """Generate + judge cards for each item. On budget exhaustion, returns the partial
    results accumulated so far instead of discarding the run."""
    results: list[GenResult] = []
    metrics = GenMetrics()
    for item in items:
        result = GenResult(item_id=item.id)
        try:
            draft = generator.generate(item.source, count_hint=count_hint)
            reviewed = generator.self_review(draft, item.source, rounds=review_rounds)
            for card in reviewed.cards:
                verdict = judge.judge(
                    card,
                    source_description=item.source.markdown,
                    reference_cards=item.reference_cards or None,
                )
                result.judged.append((card, verdict))
                metrics.n_cards += 1
                metrics.tier_counts[verdict.tier.value] = (
                    metrics.tier_counts.get(verdict.tier.value, 0) + 1
                )
                if verdict.usable:
                    metrics.usable += 1
                if verdict.clean:
                    metrics.clean += 1
                for probe in verdict.failed_probes:
                    metrics.probe_fail[probe.value] = metrics.probe_fail.get(probe.value, 0) + 1
        except BudgetExceededError as exc:
            logger.warning("stopping generation eval at %s (budget exhausted): %s", item.id, exc)
            if result.judged:
                results.append(result)
            break
        results.append(result)
        metrics.n_items += 1
        logger.info("generation eval %s: %d cards", item.id, len(result.judged))
    return results, metrics


def calibrate_judge(items: list[ValItem], judge: Judge, max_candidates: int = 20) -> CalibResult:
    """Judge human-labeled candidates (grounded against same-highlight references) and
    compare our tier to the human label."""
    calib = CalibResult()
    for item in items:
        for cand in item.candidates:
            if cand.human_tier is None:
                continue
            if calib.n >= max_candidates:
                return calib
            refs = [c for c in item.reference_cards if c is not cand.card] or None
            try:
                verdict = judge.judge(cand.card, source_description=item.source.markdown,
                                      reference_cards=refs)
            except BudgetExceededError as exc:
                logger.warning("stopping judge calibration early (budget exhausted): %s", exc)
                return calib
            calib.n += 1
            if verdict.tier == cand.human_tier:
                calib.exact += 1
            if verdict.usable == cand.human_tier.usable:
                calib.usable_correct += 1
            key = f"{cand.human_tier.value}->{verdict.tier.value}"
            calib.confusion[key] = calib.confusion.get(key, 0) + 1
    return calib


def reference_ceiling(items: list[ValItem], judge: Judge, max_cards: int = 12) -> GenMetrics:
    """Judge expert reference cards the same way, as a quality ceiling."""
    metrics = GenMetrics()
    for item in items:
        for card in item.reference_cards:
            if metrics.n_cards >= max_cards:
                return metrics
            others = [c for c in item.reference_cards if c is not card] or None
            try:
                verdict = judge.judge(card, source_description=item.source.markdown,
                                      reference_cards=others)
            except BudgetExceededError as exc:
                logger.warning("stopping reference ceiling early (budget exhausted): %s", exc)
                return metrics
            metrics.n_cards += 1
            metrics.tier_counts[verdict.tier.value] = (
                metrics.tier_counts.get(verdict.tier.value, 0) + 1
            )
            if verdict.usable:
                metrics.usable += 1
            if verdict.clean:
                metrics.clean += 1
    return metrics


def render_report(
    *,
    dataset: str,
    gen: GenMetrics,
    calib: CalibResult | None,
    ceiling: GenMetrics | None,
    tracker: CostTracker,
    timestamp: str,
    note: str = "",
) -> str:
    lines = [
        f"# Eval report — {dataset}",
        f"_{timestamp}_",
    ]
    if note:
        lines.append(f"\n**{note}**")
    lines += [
        "",
        "## Generation quality (our cards, grounded-judged vs references)",
        f"- items: {gen.n_items}, cards: {gen.n_cards}",
        f"- **usable (T2+T3): {gen.usable_frac:.0%}**, clean (usable + no probe fails): "
        f"{gen.clean_frac:.0%}",
        f"- tier distribution: {dict(sorted(gen.tier_counts.items()))}",
        f"- probe failures: {dict(sorted(gen.probe_fail.items()))}",
    ]
    if ceiling and ceiling.n_cards:
        lines += [
            "",
            "## Reference-deck ceiling (expert cards, judged identically)",
            f"- cards: {ceiling.n_cards}, usable: {ceiling.usable_frac:.0%}, "
            f"tiers: {dict(sorted(ceiling.tier_counts.items()))}",
        ]
    if calib and calib.n:
        lines += [
            "",
            "## Judge calibration vs human labels",
            f"- candidates: {calib.n}",
            f"- exact tier agreement: {calib.exact_agreement:.0%}",
            f"- usable-vs-unusable accuracy: {calib.usable_accuracy:.0%}",
            f"- confusion (human->ours): {dict(sorted(calib.confusion.items()))}",
        ]
    lines += ["", "## Cost", f"- {tracker.summary()}"]
    return "\n".join(lines) + "\n"
