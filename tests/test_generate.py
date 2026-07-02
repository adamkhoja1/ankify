"""Offline tests for Generator prompt assembly (capture LLM, no API)."""

from typing import cast

from pydantic import BaseModel

from ankify.generate import Generator, _RawCardSet
from ankify.llm import LLM
from ankify.models import Card, CardSet, Source


class _CaptureLLM(LLM):
    """Records the prompts it is asked to parse; returns an empty card set."""

    def __init__(self) -> None:  # no client/config
        self.prompts: list[str] = []

    def parse[T: BaseModel](
        self,
        *,
        user: str,
        schema: type[T],
        system: str | None = None,
        effort: str | None = None,
    ) -> T:
        self.prompts.append(user)
        return cast(T, _RawCardSet(cards=[]))


def test_generate_and_self_review_include_notes() -> None:
    llm = _CaptureLLM()
    gen = Generator(llm)
    source = Source(title="t", markdown="body text")
    gen.generate(source, notes="ONLY chapter 2")
    assert "ONLY chapter 2" in llm.prompts[0]

    draft = CardSet(cards=[Card(front="q", back="a")])
    gen.self_review(draft, source, notes="ONLY chapter 2", rounds=1)
    assert "ONLY chapter 2" in llm.prompts[1]  # scope survives the review round


def test_self_review_without_notes_omits_scope_header() -> None:
    llm = _CaptureLLM()
    Generator(llm).self_review(
        CardSet(cards=[Card(front="q", back="a")]), Source(title="t", markdown="m"), rounds=1
    )
    assert "User notes / scope" not in llm.prompts[0]
