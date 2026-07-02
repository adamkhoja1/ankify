"""Offline tests for the eval harness: metric bookkeeping and budget-exhaustion behavior.

Uses stub Generator/Judge subclasses (no LLM); the real-API path lives in `ankify eval`.
"""

from ankify.eval.datasets import ValItem
from ankify.eval.harness import evaluate_generation, render_report
from ankify.generate import Generator
from ankify.llm import BudgetExceededError, CostTracker
from ankify.models import Card, CardSet, Source, Tier, Verdict
from ankify.rubric import Judge


class _StubGenerator(Generator):
    def __init__(self) -> None:  # no LLM
        pass

    def generate(
        self,
        source: Source,
        notes: str = "",
        count_hint: int | None = None,
        allow_cloze: bool = True,
    ) -> CardSet:
        return CardSet(cards=[Card(front=f"q about {source.title}", back="a")])

    def self_review(
        self, cardset: CardSet, source: Source, notes: str = "", rounds: int = 2
    ) -> CardSet:
        return cardset


class _StubJudge(Judge):
    """Returns T3 verdicts; raises BudgetExceededError from call `fail_at` onward."""

    def __init__(self, fail_at: int | None = None) -> None:  # no LLM
        self.fail_at = fail_at
        self.calls = 0

    def judge(
        self,
        card: Card,
        source_description: str = "",
        reference_cards: list[Card] | None = None,
        run_probes: bool = True,
    ) -> Verdict:
        self.calls += 1
        if self.fail_at is not None and self.calls >= self.fail_at:
            raise BudgetExceededError("cap")
        return Verdict(tier=Tier.T3)


def _items(n: int) -> list[ValItem]:
    return [
        ValItem(id=f"i{k}", source=Source(title=f"s{k}", markdown="body")) for k in range(n)
    ]


def test_evaluate_generation_counts_metrics() -> None:
    results, metrics = evaluate_generation(_items(3), _StubGenerator(), _StubJudge())
    assert metrics.n_items == 3 and metrics.n_cards == 3
    assert metrics.usable == 3 and metrics.usable_frac == 1.0
    assert [r.item_id for r in results] == ["i0", "i1", "i2"]


def test_evaluate_generation_returns_partials_on_budget_exhaustion() -> None:
    # judge dies on the 3rd card: items 0-1 complete, item 2 aborts, item 3 never runs
    results, metrics = evaluate_generation(_items(4), _StubGenerator(), _StubJudge(fail_at=3))
    assert metrics.n_items == 2 and metrics.n_cards == 2
    assert [r.item_id for r in results] == ["i0", "i1"]


def test_render_report_includes_early_stop_note() -> None:
    _, metrics = evaluate_generation(_items(1), _StubGenerator(), _StubJudge())
    report = render_report(
        dataset="d",
        gen=metrics,
        calib=None,
        ceiling=None,
        tracker=CostTracker(),
        timestamp="now",
        note="Stopped early: budget exhausted; metrics are partial.",
    )
    assert "Stopped early" in report
