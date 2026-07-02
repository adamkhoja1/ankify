"""Offline tests for Judge fan-out (stub LLM, no API)."""

from typing import cast

from pydantic import BaseModel

from ankify.llm import LLM
from ankify.models import Card, ProbeName, Tier
from ankify.rubric import Judge, _ProbeOut, _TierOut


class _StubLLM(LLM):
    """Answers tier and probe prompts with canned results; records what was asked."""

    def __init__(self) -> None:  # no client/config
        self.schemas: list[str] = []

    def parse[T: BaseModel](
        self,
        *,
        user: str,
        schema: type[T],
        system: str | None = None,
        effort: str | None = None,
    ) -> T:
        self.schemas.append(schema.__name__)
        if schema is _TierOut:
            return cast(T, _TierOut(reasoning="solid", tier=Tier.T3))
        return cast(T, _ProbeOut(reason="", failed=False))


def test_judge_runs_tier_and_all_probes() -> None:
    llm = _StubLLM()
    verdict = Judge(llm).judge(Card(front="q", back="a"))
    assert verdict.tier is Tier.T3 and verdict.reason == "solid"
    assert [p.probe for p in verdict.probes] == list(ProbeName)  # all five, in order
    assert llm.schemas.count("_TierOut") == 1 and llm.schemas.count("_ProbeOut") == 5


def test_judge_without_probes_is_single_call() -> None:
    llm = _StubLLM()
    verdict = Judge(llm).judge(Card(front="q", back="a"), run_probes=False)
    assert verdict.probes == [] and llm.schemas == ["_TierOut"]
