"""Rubric scoring: LLM-judge probes and tiering (see docs/RUBRIC.md).

`Judge` runs the five binary failure-mode probes and the holistic T0-T3 tier on a card.
Tiering is *grounded* against reference-deck cards for the same source when available
(the Memory Machines finding: grounded judging is far more reliable), else ungrounded.

The instruction prompts are adapted from Memory Machines (Apache-2.0; see NOTICE). Their
output-format sections are stripped at load time; structured outputs enforce the shape.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import cache
from importlib import resources

from pydantic import BaseModel

from .llm import LLM
from .models import Card, ProbeName, ProbeResult, Tier, Verdict

_PROBE_FILES: dict[ProbeName, str] = {
    ProbeName.LACKS_CONTEXT: "probe_lacks_context.txt",
    ProbeName.MULTIPLE_RESPONSES: "probe_multiple_responses.txt",
    ProbeName.SHALLOW: "probe_shallow.txt",
    ProbeName.WORDY: "probe_wordy.txt",
    ProbeName.NARROW: "probe_narrow.txt",
}


@cache
def _load_prompt(filename: str) -> str:
    """Read a vendored prompt, dropping its output-format section."""
    text = resources.files("ankification.prompts").joinpath(filename).read_text()
    for marker in ("## Output Format", "## Output format", "You must respond with a JSON"):
        idx = text.find(marker)
        if idx != -1:
            text = text[:idx]
    return text.strip()


class _ProbeOut(BaseModel):
    reason: str
    failed: bool


class _TierOut(BaseModel):
    reasoning: str
    tier: Tier


def _render_cards(cards: Sequence[Card]) -> str:
    return "\n\n".join(c.as_qa() for c in cards)


class Judge:
    """Scores a card against the rubric using an `LLM`."""

    def __init__(
        self, llm: LLM, probe_effort: str | None = None, tier_effort: str | None = None
    ) -> None:
        self.llm = llm
        self.probe_effort = probe_effort  # None -> the LLM's configured reasoning effort
        self.tier_effort = tier_effort

    def run_probe(self, card: Card, probe: ProbeName) -> ProbeResult:
        system = _load_prompt(_PROBE_FILES[probe])
        user = f"Evaluate this memory prompt:\n\n{card.as_qa()}"
        out = self.llm.parse(user=user, schema=_ProbeOut, system=system, effort=self.probe_effort)
        return ProbeResult(probe=probe, failed=out.failed, reason=out.reason)

    def run_probes(self, card: Card) -> list[ProbeResult]:
        return [self.run_probe(card, probe) for probe in ProbeName]

    def tier(
        self,
        card: Card,
        source_description: str = "",
        reference_cards: Sequence[Card] | None = None,
    ) -> _TierOut:
        if reference_cards:
            prompt = (
                _load_prompt("tier_grounded.txt")
                .replace("{RATED_MEMORY_PROMPTS}", _render_cards(reference_cards))
                .replace("{SOURCE_DESCRIPTION}", source_description or "(not provided)")
                .replace("{GENERATED_PROMPT}", card.as_qa())
            )
        else:
            prompt = (
                _load_prompt("tier_ungrounded.txt")
                .replace("{SOURCE_DESCRIPTION}", source_description or "(not provided)")
                .replace("{GENERATED_PROMPT}", card.as_qa())
            )
        prompt += "\n\nReturn your reasoning and the final tier as structured output."
        return self.llm.parse(user=prompt, schema=_TierOut, effort=self.tier_effort)

    def judge(
        self,
        card: Card,
        source_description: str = "",
        reference_cards: Sequence[Card] | None = None,
        run_probes: bool = True,
    ) -> Verdict:
        tier_out = self.tier(card, source_description, reference_cards)
        probes = self.run_probes(card) if run_probes else []
        return Verdict(tier=tier_out.tier, probes=probes, reason=tier_out.reasoning)
