"""Offline unit tests (no API): cost tracking, prompt loading, parsing, session logic."""

from pathlib import Path

import pytest

from ankify.eval.datasets import parse_qa
from ankify.ingest import from_file
from ankify.llm import BudgetExceededError, CostTracker
from ankify.models import Card, CardSet, CardType, ReviewAction, ReviewDecision
from ankify.rubric import _load_prompt
from ankify.server.session import ReviewSession


def test_cost_tracker_accumulates_and_caps() -> None:
    t = CostTracker(budget_usd=1.0)
    t.record("gpt-5.5", 1000, 1000)
    assert t.n_calls == 1 and t.spent_usd > 0
    with pytest.raises(BudgetExceededError):
        t.record("gpt-5.5", 10_000_000, 10_000_000)


def test_cost_tracker_no_budget_never_raises() -> None:
    t = CostTracker()
    for _ in range(5):
        t.record("gpt-5.5", 10_000_000, 10_000_000)
    assert t.n_calls == 5


@pytest.mark.parametrize("filename", ["probe_shallow.txt", "tier_grounded.txt"])
def test_load_prompt_strips_output_format(filename: str) -> None:
    text = _load_prompt(filename)
    assert "## Output Format" not in text
    assert "You must respond with a JSON" not in text
    assert len(text) > 100  # non-trivial content remains


def test_parse_qa_basic_cloze_and_invalid() -> None:
    basic = parse_qa("Q. What is X?\nA. The answer.")
    assert basic is not None and basic.type is CardType.BASIC and basic.front == "What is X?"
    cloze = parse_qa("Cloze: The capital is {{c1::Paris}}.")
    assert cloze is not None and cloze.type is CardType.CLOZE
    assert parse_qa("just a sentence with no Q or A marker structure") is None
    assert parse_qa("Cloze: no deletion here") is None


def test_session_approved_cards_respects_decisions() -> None:
    a = Card(front="qa", back="1")
    b = Card(front="qb", back="2")
    c = Card(front="qc", back="3")
    session = ReviewSession(
        rounds=[CardSet(cards=[a, b, c])],
    )
    session.decisions[a.id] = ReviewDecision(card_id=a.id, action=ReviewAction.ACCEPT)
    edited = Card(front="qb-edited", back="2!")
    session.decisions[b.id] = ReviewDecision(
        card_id=b.id, action=ReviewAction.EDIT, edited_card=edited
    )
    session.decisions[c.id] = ReviewDecision(card_id=c.id, action=ReviewAction.DISCARD)

    approved = session.approved_cards()
    fronts = [card.front for card in approved]
    assert fronts == ["qa", "qb-edited"]
    assert session.pending_count() == 0
    assert [card.front for card in session.discarded_cards()] == ["qc"]


def test_carried_cards_keeps_pending_and_accepted_drops_discarded() -> None:
    pending = Card(front="p", back="1")
    accepted = Card(front="a", back="2")
    edited = Card(front="e", back="3")
    discarded = Card(front="d", back="4")
    session = ReviewSession(
        rounds=[CardSet(cards=[pending, accepted, edited, discarded])],
    )
    session.decisions[accepted.id] = ReviewDecision(card_id=accepted.id, action=ReviewAction.ACCEPT)
    new_edit = Card(front="e-edited", back="3!")
    session.decisions[edited.id] = ReviewDecision(
        card_id=edited.id, action=ReviewAction.EDIT, edited_card=new_edit
    )
    session.decisions[discarded.id] = ReviewDecision(
        card_id=discarded.id, action=ReviewAction.DISCARD
    )
    carried = [c.front for c in session.carried_cards()]
    # pending + accepted + (edited as its edited text), in order; discarded dropped
    assert carried == ["p", "a", "e-edited"]


def test_ingest_rejects_binary(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    with pytest.raises(ValueError, match="to_md"):
        from_file(pdf)


def test_ingest_reads_markdown(tmp_path: Path) -> None:
    md = tmp_path / "note.md"
    md.write_text("# Title\n\nbody")
    src = from_file(md)
    assert src.markdown.startswith("# Title") and src.kind == "markdown"
