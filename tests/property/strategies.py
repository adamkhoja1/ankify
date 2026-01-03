"""Custom Hypothesis strategies for generating test data."""

from datetime import datetime, timedelta
from typing import Any

from hypothesis import strategies as st

from ankification.cards.models import BasicCard, CardStatus, CardType, ClozeCard


# === Primitive Strategies ===

# Text that's valid for card content (no null bytes, reasonable length)
card_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    min_size=1,
    max_size=1000,
)

# Short text for tags and identifiers
short_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N"),
        whitelist_characters="-_",
    ),
    min_size=1,
    max_size=50,
)

# Tag names (alphanumeric with hyphens)
tag_name = st.from_regex(r"[a-z][a-z0-9-]{0,29}", fullmatch=True)

# Tag lists
tag_list = st.lists(tag_name, min_size=0, max_size=10, unique=True)

# Source identifiers (file paths or URLs)
file_source = st.from_regex(r"[a-z][a-z0-9_-]{0,19}\.(txt|md|pdf|html)", fullmatch=True)
url_source = st.from_regex(r"https?://[a-z][a-z0-9-]{0,19}\.[a-z]{2,4}/[a-z0-9/-]*", fullmatch=True)
source = st.one_of(file_source, url_source)

# Card status
card_status = st.sampled_from([CardStatus.DRAFT, CardStatus.ACCEPTED, CardStatus.REJECTED])

# Timestamps
past_datetime = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
)


# === Card Strategies ===


@st.composite
def basic_card_strategy(draw: st.DrawFn) -> BasicCard:
    """Generate a random BasicCard."""
    front = draw(card_text)
    back = draw(card_text)
    src = draw(source)
    tags = draw(tag_list)
    status = draw(card_status)
    created = draw(past_datetime)
    modified = draw(st.datetimes(min_value=created, max_value=datetime(2030, 12, 31)))

    card = BasicCard(
        front=front,
        back=back,
        source=src,
        tags=tags,
        status=status,
    )
    card.created_at = created
    card.modified_at = modified
    return card


@st.composite
def cloze_deletion(draw: st.DrawFn, index: int = 1) -> str:
    """Generate a single cloze deletion."""
    answer = draw(st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
        min_size=1,
        max_size=50,
    ))
    # Escape any braces in the answer
    answer = answer.replace("{", "").replace("}", "")
    return f"{{{{c{index}::{answer}}}}}"


@st.composite
def cloze_text_strategy(draw: st.DrawFn) -> str:
    """Generate valid cloze deletion text."""
    num_deletions = draw(st.integers(min_value=1, max_value=3))
    parts = []

    for i in range(num_deletions):
        # Add some context text
        prefix = draw(st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
            min_size=1,
            max_size=30,
        ))
        prefix = prefix.replace("{", "").replace("}", "")
        parts.append(prefix)

        # Add cloze deletion
        cloze = draw(cloze_deletion(index=i + 1))
        parts.append(cloze)

    # Add final suffix
    suffix = draw(st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
        min_size=0,
        max_size=20,
    ))
    suffix = suffix.replace("{", "").replace("}", "")
    parts.append(suffix)

    return " ".join(parts)


@st.composite
def cloze_card_strategy(draw: st.DrawFn) -> ClozeCard:
    """Generate a random ClozeCard."""
    text = draw(cloze_text_strategy())
    src = draw(source)
    tags = draw(tag_list)
    status = draw(card_status)
    created = draw(past_datetime)
    modified = draw(st.datetimes(min_value=created, max_value=datetime(2030, 12, 31)))

    card = ClozeCard(
        text=text,
        source=src,
        tags=tags,
        status=status,
    )
    card.created_at = created
    card.modified_at = modified
    return card


@st.composite
def any_card_strategy(draw: st.DrawFn) -> BasicCard | ClozeCard:
    """Generate either a BasicCard or ClozeCard."""
    if draw(st.booleans()):
        return draw(basic_card_strategy())
    else:
        return draw(cloze_card_strategy())


# === Collection Strategies ===

basic_card_list = st.lists(basic_card_strategy(), min_size=0, max_size=20)
cloze_card_list = st.lists(cloze_card_strategy(), min_size=0, max_size=20)
mixed_card_list = st.lists(any_card_strategy(), min_size=0, max_size=20)


# === Session Strategies ===


@st.composite
def session_params_strategy(draw: st.DrawFn) -> dict[str, Any]:
    """Generate session creation parameters."""
    sources = draw(st.lists(source, min_size=1, max_size=5))
    provider = draw(st.sampled_from(["openai", "anthropic"]))
    card_types = draw(st.lists(
        st.sampled_from(["basic", "cloze"]),
        min_size=1,
        max_size=2,
        unique=True,
    ))
    count_guidance = draw(st.from_regex(r"[1-9][0-9]?-[1-9][0-9]?", fullmatch=True))

    return {
        "sources": sources,
        "provider": provider,
        "card_types": card_types,
        "count_guidance": count_guidance,
    }


# === Config Strategies ===


@st.composite
def config_provider_strategy(draw: st.DrawFn) -> str:
    """Generate valid LLM provider name."""
    return draw(st.sampled_from(["openai", "anthropic"]))


@st.composite
def config_model_strategy(draw: st.DrawFn, provider: str) -> str:
    """Generate valid model name for a provider."""
    if provider == "openai":
        return draw(st.sampled_from(["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]))
    else:
        return draw(st.sampled_from([
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]))


@st.composite
def count_guidance_strategy(draw: st.DrawFn) -> str:
    """Generate valid count guidance strings."""
    min_count = draw(st.integers(min_value=1, max_value=20))
    max_count = draw(st.integers(min_value=min_count, max_value=50))
    return f"{min_count}-{max_count}"
