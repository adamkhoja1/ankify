"""Validation-set loaders. Each loader yields `ValItem`s: a source to generate from plus
expert/human reference cards for grounded judging.

Primary set: Memory Machines (`laddermedia/srs-prompts`), which also carries human tier
labels (`task_type`) for judge calibration. Quantum Country and Ultimate Geography loaders
are stubs pending their scrape/parse (see docs/RESEARCH.md §3).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..models import Card, CardType, Source, Tier

logger = logging.getLogger(__name__)

# Memory Machines task_type -> our tier scale.
_TASK_TIER: dict[str, Tier] = {
    "off-target": Tier.T0,
    "needs-refactor": Tier.T1,
    "needs-polish": Tier.T2,
    "ready-to-review": Tier.T3,
}


@dataclass
class Candidate:
    card: Card
    human_tier: Tier | None = None
    pluckable: bool | None = None


@dataclass
class ValItem:
    id: str
    source: Source
    reference_cards: list[Card] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)


def parse_qa(text: str) -> Card | None:
    """Parse a Memory Machines `content` string into a Card."""
    text = text.strip()
    if text.lower().startswith("cloze:"):
        body = text.split(":", 1)[1].strip()
        if "{{c" not in body:
            return None
        return Card(type=CardType.CLOZE, cloze_text=body)
    if "A." in text and text.lstrip().startswith("Q."):
        q, a = text.split("A.", 1)
        front = q.strip().removeprefix("Q.").strip()
        back = a.strip()
        if front and back:
            return Card(type=CardType.BASIC, front=front, back=back)
    return None


def load_memory_machines(split: str = "test", limit: int | None = None) -> list[ValItem]:
    """Load Memory Machines highlights as ValItems, grouped by highlight_id."""
    from datasets import load_dataset  # type: ignore[import-untyped]

    rows = load_dataset("laddermedia/srs-prompts")[split]
    by_highlight: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_highlight[row["highlight_id"]].append(row)

    items: list[ValItem] = []
    for highlight_id, group in by_highlight.items():
        first = group[0]
        meta = first.get("source_meta") or {}
        summary = meta.get("summary", "") if isinstance(meta, dict) else ""
        markdown = first["highlight"]
        if first.get("highlight_interpretation"):
            markdown += f"\n\nWhy it matters: {first['highlight_interpretation']}"
        if summary:
            markdown += f"\n\nSource summary: {summary}"

        candidates: list[Candidate] = []
        references: list[Card] = []
        for row in group:
            card = parse_qa(row["content"])
            if card is None:
                continue
            tier = _TASK_TIER.get(row["task_type"])
            candidates.append(Candidate(card=card, human_tier=tier, pluckable=row["pluckable"]))
            if row["pluckable"]:
                references.append(card)

        items.append(
            ValItem(
                id=f"mm-{highlight_id}",
                source=Source(
                    title=first.get("source_url") or f"highlight-{highlight_id}",
                    kind="highlight",
                    markdown=markdown,
                    uri=first.get("source_url", ""),
                ),
                reference_cards=references,
                candidates=candidates,
            )
        )
        if limit and len(items) >= limit:
            break
    logger.info("loaded %d Memory Machines val items (split=%s)", len(items), split)
    return items


def load_quantum_country(limit: int | None = None) -> list[ValItem]:
    raise NotImplementedError(
        "Quantum Country loader pending: scrape the 112 embedded prompts from "
        "quantum.country/qcvc (see docs/RESEARCH.md §3)."
    )


def load_ultimate_geography(limit: int | None = None) -> list[ValItem]:
    raise NotImplementedError(
        "Ultimate Geography loader pending: parse country/capital facts from the "
        "anki-geo/ultimate-geography MIT repo (see docs/RESEARCH.md §3)."
    )
