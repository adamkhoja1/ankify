"""LLM client: structured completions on GPT-5.5 with cost tracking.

Generation, self-review, and the eval judge all go through `LLM.parse`, which returns a
Pydantic-typed response via OpenAI structured outputs. Reasoning effort is per-call
(default `high` for generation and judging; cheaper tiers for incidental calls). A shared
`CostTracker` accumulates spend and raises `BudgetExceededError` at the cap so the eval
stays bounded. Reads `OPENAI_API_KEY` from the environment (`.env` loaded on import).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-5.5"
Effort = Literal["minimal", "low", "medium", "high"]

# (input, output) USD per token. gpt-5.5 figures are an ESTIMATE pending confirmation;
# token counts in CostTracker are the source of truth. Override per model as needed.
_PRICING: dict[str, tuple[float, float]] = {
    "gpt-5.5": (1.25e-6, 10.0e-6),
}
_DEFAULT_PRICE = (1.25e-6, 10.0e-6)


class BudgetExceededError(RuntimeError):
    """Raised when a cost-capped tracker exceeds its budget."""


@dataclass
class CostTracker:
    """Accumulates API spend and token counts; enforces an optional ceiling."""

    budget_usd: float | None = None
    spent_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    n_calls: int = 0
    by_effort: dict[str, int] = field(default_factory=dict)

    def record(self, model: str, usage: CompletionUsage, effort: str = "") -> float:
        in_price, out_price = _PRICING.get(model, _DEFAULT_PRICE)
        in_tok = usage.prompt_tokens
        out_tok = usage.completion_tokens
        cost = in_tok * in_price + out_tok * out_price
        self.spent_usd += cost
        self.input_tokens += in_tok
        self.output_tokens += out_tok
        self.n_calls += 1
        if effort:
            self.by_effort[effort] = self.by_effort.get(effort, 0) + 1
        if self.budget_usd is not None and self.spent_usd > self.budget_usd:
            raise BudgetExceededError(
                f"spent ~${self.spent_usd:.2f} > budget ${self.budget_usd:.2f} "
                f"after {self.n_calls} calls ({self.input_tokens}+{self.output_tokens} tok)"
            )
        return cost

    def summary(self) -> str:
        return (
            f"~${self.spent_usd:.3f} | {self.n_calls} calls | "
            f"{self.input_tokens} in + {self.output_tokens} out tok | effort {self.by_effort}"
        )


class LLM:
    """OpenAI client configured for structured, cost-tracked completions."""

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        tracker: CostTracker | None = None,
    ) -> None:
        self.client = OpenAI()
        self.model = model
        self.tracker = tracker if tracker is not None else CostTracker()

    def parse[T: BaseModel](
        self,
        *,
        user: str,
        schema: type[T],
        system: str | None = None,
        effort: Effort = "high",
    ) -> T:
        """Return a validated instance of `schema` from the model.

        Generation and judging pass `effort="high"`; use lower tiers for cheap incidental
        calls. OpenAI caches repeated prefixes automatically, so put stable context (the
        source) first in `system` to get cache discounts across many calls.
        """
        messages: list[ChatCompletionMessageParam] = []
        if system is not None:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        completion = self.client.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=schema,
            reasoning_effort=effort,
        )
        if completion.usage is not None:
            self.tracker.record(self.model, completion.usage, effort)
        message = completion.choices[0].message
        if message.refusal:
            raise RuntimeError(f"model refused: {message.refusal}")
        if message.parsed is None:
            raise RuntimeError(f"structured parse returned no output: {message.content!r}")
        return message.parsed
