"""Card fixtures for testing."""

from datetime import datetime, timedelta

import pytest

from ankification.cards.models import BasicCard, CardStatus, CardType, ClozeCard


# === Individual Card Fixtures ===


@pytest.fixture
def draft_basic_card() -> BasicCard:
    """Basic card in draft status."""
    return BasicCard(
        front="What is the capital of France?",
        back="Paris",
        source="geography.txt",
        tags=["geography", "europe"],
        status=CardStatus.DRAFT,
    )


@pytest.fixture
def accepted_basic_card() -> BasicCard:
    """Basic card in accepted status."""
    return BasicCard(
        front="What is 2 + 2?",
        back="4",
        source="math.txt",
        tags=["math", "arithmetic"],
        status=CardStatus.ACCEPTED,
    )


@pytest.fixture
def rejected_basic_card() -> BasicCard:
    """Basic card in rejected status."""
    return BasicCard(
        front="Bad question",
        back="Bad answer",
        source="rejected.txt",
        tags=["rejected"],
        status=CardStatus.REJECTED,
    )


@pytest.fixture
def draft_cloze_card() -> ClozeCard:
    """Cloze card in draft status."""
    return ClozeCard(
        text="The {{c1::mitochondria}} is the powerhouse of the cell.",
        source="biology.txt",
        tags=["biology", "cells"],
        status=CardStatus.DRAFT,
    )


@pytest.fixture
def accepted_cloze_card() -> ClozeCard:
    """Cloze card in accepted status."""
    return ClozeCard(
        text="Python was created by {{c1::Guido van Rossum}} in {{c2::1991}}.",
        source="programming.txt",
        tags=["programming", "python"],
        status=CardStatus.ACCEPTED,
    )


@pytest.fixture
def multi_cloze_card() -> ClozeCard:
    """Cloze card with multiple deletions."""
    return ClozeCard(
        text="{{c1::HTTP}} stands for {{c2::Hypertext Transfer Protocol}} and uses port {{c3::80}}.",
        source="networking.txt",
        tags=["networking", "protocols"],
        status=CardStatus.DRAFT,
    )


# === Card with Specific Attributes ===


@pytest.fixture
def card_with_long_content() -> BasicCard:
    """Card with long front and back content."""
    return BasicCard(
        front="Explain the entire history of computer science from its origins to the present day, including all major developments, key figures, and technological breakthroughs that have shaped the field.",
        back="Computer science traces its roots back to the work of Charles Babbage and Ada Lovelace in the 19th century. " * 20,
        source="history.txt",
        tags=["history", "computer-science"],
    )


@pytest.fixture
def card_with_special_characters() -> BasicCard:
    """Card with special characters in content."""
    return BasicCard(
        front="What is the formula for: E = mc²?",
        back="Energy equals mass times the speed of light squared (E = mc²). Special chars: <>&\"'",
        source="physics.txt",
        tags=["physics", "formulas"],
    )


@pytest.fixture
def card_with_unicode() -> BasicCard:
    """Card with unicode characters."""
    return BasicCard(
        front="How do you say 'hello' in Japanese?",
        back="こんにちは (Konnichiwa) - Hello in Japanese 🇯🇵",
        source="languages.txt",
        tags=["languages", "japanese"],
    )


@pytest.fixture
def card_with_code() -> BasicCard:
    """Card containing code snippets."""
    return BasicCard(
        front="How do you define a function in Python?",
        back="""```python
def my_function(arg1, arg2):
    return arg1 + arg2
```""",
        source="python.txt",
        tags=["programming", "python", "functions"],
    )


@pytest.fixture
def card_with_many_tags() -> BasicCard:
    """Card with many tags."""
    return BasicCard(
        front="What is machine learning?",
        back="A subset of AI that enables systems to learn from data.",
        source="ml.txt",
        tags=["ai", "machine-learning", "deep-learning", "neural-networks", "data-science", "python", "tensorflow", "pytorch"],
    )


@pytest.fixture
def card_with_empty_tags() -> BasicCard:
    """Card with no tags."""
    return BasicCard(
        front="No tags question",
        back="No tags answer",
        source="empty.txt",
        tags=[],
    )


# === Card Collections ===


@pytest.fixture
def basic_card_collection() -> list[BasicCard]:
    """Collection of basic cards with various statuses."""
    return [
        BasicCard(front=f"Q{i}", back=f"A{i}", source="test.txt", status=status)
        for i, status in enumerate([
            CardStatus.DRAFT,
            CardStatus.DRAFT,
            CardStatus.ACCEPTED,
            CardStatus.ACCEPTED,
            CardStatus.REJECTED,
        ])
    ]


@pytest.fixture
def cloze_card_collection() -> list[ClozeCard]:
    """Collection of cloze cards with various statuses."""
    return [
        ClozeCard(text=f"{{{{c1::Answer{i}}}}} is correct.", source="test.txt", status=status)
        for i, status in enumerate([
            CardStatus.DRAFT,
            CardStatus.DRAFT,
            CardStatus.ACCEPTED,
            CardStatus.REJECTED,
        ])
    ]


@pytest.fixture
def mixed_card_collection() -> list[BasicCard | ClozeCard]:
    """Mixed collection of basic and cloze cards."""
    cards: list[BasicCard | ClozeCard] = [
        BasicCard(front="Basic Q1", back="Basic A1", source="test.txt", status=CardStatus.DRAFT),
        BasicCard(front="Basic Q2", back="Basic A2", source="test.txt", status=CardStatus.ACCEPTED),
        ClozeCard(text="{{c1::Cloze1}} answer", source="test.txt", status=CardStatus.DRAFT),
        ClozeCard(text="{{c1::Cloze2}} answer", source="test.txt", status=CardStatus.ACCEPTED),
        BasicCard(front="Basic Q3", back="Basic A3", source="test.txt", status=CardStatus.REJECTED),
    ]
    return cards


@pytest.fixture
def cards_from_multiple_sources() -> list[BasicCard]:
    """Cards from different sources."""
    sources = ["file1.txt", "file2.txt", "file3.md", "https://example.com"]
    return [
        BasicCard(
            front=f"Question from {src}",
            back=f"Answer from {src}",
            source=src,
            tags=[f"source-{i}"],
        )
        for i, src in enumerate(sources)
    ]


@pytest.fixture
def timestamped_cards() -> list[BasicCard]:
    """Cards with specific timestamps for ordering tests."""
    base_time = datetime(2024, 1, 1, 12, 0, 0)
    cards = []
    for i in range(5):
        card = BasicCard(
            front=f"Timestamped Q{i}",
            back=f"Timestamped A{i}",
            source="time.txt",
        )
        card.created_at = base_time + timedelta(hours=i)
        card.modified_at = base_time + timedelta(hours=i, minutes=30)
        cards.append(card)
    return cards
