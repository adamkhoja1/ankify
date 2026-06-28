import pytest
from pydantic import ValidationError

from ankify.models import (
    Card,
    CardSet,
    CardType,
    ProbeName,
    ProbeResult,
    Source,
    Tier,
    Verdict,
)


def test_basic_card_roundtrips():
    c = Card(type=CardType.BASIC, front="What is X?", back="Y")
    assert c.prompt_text() == "What is X?"
    assert c.answer_text() == "Y"
    assert c.as_qa() == "Q. What is X?\nA. Y"
    assert c.id  # auto-assigned


def test_cloze_card_requires_marker():
    ok = Card(type=CardType.CLOZE, cloze_text="The capital is {{c1::Paris}}.")
    assert ok.prompt_text().startswith("The capital")
    with pytest.raises(ValidationError):
        Card(type=CardType.CLOZE, cloze_text="The capital is Paris.")  # no deletion
    with pytest.raises(ValidationError):
        Card(type=CardType.CLOZE, cloze_text="   ")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"type": CardType.BASIC, "front": "Q", "back": ""},
        {"type": CardType.BASIC, "front": "", "back": "A"},
        {"type": CardType.REVERSIBLE, "front": "term", "back": ""},
    ],
)
def test_front_back_required(kwargs):
    with pytest.raises(ValidationError):
        Card(**kwargs)


def test_card_ids_unique():
    a, b = Card(front="a", back="1"), Card(front="b", back="2")
    assert a.id != b.id


def test_cardset_lookup_by_id():
    c = Card(front="q", back="a")
    cs = CardSet(source=Source(title="S"), cards=[c])
    assert cs.by_id(c.id) is c
    assert cs.by_id("missing") is None


@pytest.mark.parametrize(
    ("tier", "usable"),
    [(Tier.T0, False), (Tier.T1, False), (Tier.T2, True), (Tier.T3, True)],
)
def test_tier_usable(tier, usable):
    assert tier.usable is usable
    assert Verdict(tier=tier).usable is usable


def test_verdict_clean_requires_usable_and_no_probe_failures():
    clean = Verdict(
        tier=Tier.T3,
        probes=[ProbeResult(probe=ProbeName.WORDY, failed=False)],
    )
    assert clean.clean and clean.failed_probes == []

    dirty = Verdict(
        tier=Tier.T3,
        probes=[ProbeResult(probe=ProbeName.SHALLOW, failed=True, reason="surface")],
    )
    assert not dirty.clean
    assert dirty.failed_probes == [ProbeName.SHALLOW]

    weak = Verdict(tier=Tier.T1)
    assert not weak.clean
