"""LLM client: structured, cost-tracked completions across providers.

Generation, self-review, and the eval judge all go through `LLM.parse`, which returns a
Pydantic-typed result. The provider/model/effort/key come from `ModelConfig` (config.py),
configurable from the settings panel. Both providers use their native structured-output
`.parse()` helper — OpenAI `chat.completions.parse(response_format=...)` and Anthropic
`messages.parse(output_format=...)` — so the only per-provider difference is where the
`effort` knob goes (OpenAI `reasoning_effort`, Anthropic `output_config.effort` + adaptive
thinking). A shared `CostTracker` accumulates spend and raises `BudgetExceededError` at the cap.
"""

from __future__ import annotations

import logging
import threading
import warnings
from dataclasses import dataclass, field
from typing import Any, cast

from anthropic import Anthropic, BadRequestError
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel

from .config import ModelConfig, load_config

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-5.5"

# (input, output) USD per token; token counts are the source of truth, prices are estimates.
_PRICING: dict[str, tuple[float, float]] = {
    "gpt-5.5": (1.25e-6, 10.0e-6),
    "claude-opus-4-8": (5.0e-6, 25.0e-6),
    "claude-opus-4-7": (5.0e-6, 25.0e-6),
    "claude-sonnet-4-6": (3.0e-6, 15.0e-6),
    "claude-haiku-4-5": (1.0e-6, 5.0e-6),
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
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def record(self, model: str, in_tokens: int, out_tokens: int, effort: str = "") -> float:
        # Locked: probes are judged concurrently, and lost updates would undercount spend.
        with self._lock:
            in_price, out_price = _PRICING.get(model, _DEFAULT_PRICE)
            cost = in_tokens * in_price + out_tokens * out_price
            self.spent_usd += cost
            self.input_tokens += in_tokens
            self.output_tokens += out_tokens
            self.n_calls += 1
            if effort:
                self.by_effort[effort] = self.by_effort.get(effort, 0) + 1
            if self.budget_usd is not None and self.spent_usd > self.budget_usd:
                raise BudgetExceededError(
                    f"spent ~${self.spent_usd:.2f} > budget ${self.budget_usd:.2f} "
                    f"after {self.n_calls} calls ({self.input_tokens}+{self.output_tokens} tok)"
                )
            return cost

    @property
    def exhausted(self) -> bool:
        return self.budget_usd is not None and self.spent_usd > self.budget_usd

    def summary(self) -> str:
        return (
            f"~${self.spent_usd:.3f} | {self.n_calls} calls | "
            f"{self.input_tokens} in + {self.output_tokens} out tok | effort {self.by_effort}"
        )


class LLM:
    """Provider-aware client for structured, cost-tracked completions (config-driven)."""

    def __init__(
        self,
        config: ModelConfig | None = None,
        tracker: CostTracker | None = None,
    ) -> None:
        self.config = config if config is not None else load_config()
        self.model = self.config.model
        self.default_effort = self.config.reasoning_effort
        self.tracker = tracker if tracker is not None else CostTracker()
        key = self.config.resolved_key() or None
        if self.config.provider == "anthropic":
            self._anthropic: Anthropic | None = Anthropic(api_key=key)
            self._openai: OpenAI | None = None
        else:
            self._openai = OpenAI(api_key=key)
            self._anthropic = None

    def parse[T: BaseModel](
        self,
        *,
        user: str,
        schema: type[T],
        system: str | None = None,
        effort: str | None = None,
    ) -> T:
        """Return a validated instance of `schema` from the configured model."""
        eff = effort if effort is not None else self.default_effort
        if self.config.provider == "anthropic":
            return self._parse_anthropic(user=user, schema=schema, system=system, effort=eff)
        return self._parse_openai(user=user, schema=schema, system=system, effort=eff)

    def _parse_openai[T: BaseModel](
        self, *, user: str, schema: type[T], system: str | None, effort: str
    ) -> T:
        assert self._openai is not None
        messages: list[ChatCompletionMessageParam] = []
        if system is not None:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        completion = self._openai.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=schema,
            reasoning_effort=effort,  # type: ignore[arg-type]
        )
        if completion.usage is not None:
            self.tracker.record(
                self.model,
                completion.usage.prompt_tokens,
                completion.usage.completion_tokens,
                effort,
            )
        message = completion.choices[0].message
        if message.refusal:
            raise RuntimeError(f"model refused: {message.refusal}")
        if message.parsed is None:
            raise RuntimeError(f"structured parse returned no output: {message.content!r}")
        return message.parsed

    def _parse_anthropic[T: BaseModel](
        self, *, user: str, schema: type[T], system: str | None, effort: str
    ) -> T:
        # Native structured output: messages.parse(output_format=schema) -> parsed_output.
        # Reasoning depth is `output_config.effort` paired with adaptive thinking (current Claude
        # models); older models reject those, so we retry without them on a 400.
        assert self._anthropic is not None
        call: dict[str, object] = {
            "model": self.model,
            "max_tokens": 16000,
            "messages": [{"role": "user", "content": user}],
            "output_format": schema,
        }
        if system is not None:
            call["system"] = system
        reasoning: dict[str, object] = {"thinking": {"type": "adaptive"}}
        if effort:
            reasoning["output_config"] = {"effort": effort}

        with warnings.catch_warnings():  # output_format is "deprecated" but is the parse path
            warnings.simplefilter("ignore", DeprecationWarning)
            try:
                response: Any = self._anthropic.messages.parse(**call, **reasoning)  # type: ignore[arg-type]
            except BadRequestError as exc:
                # Older Claude models reject adaptive thinking / effort — retry plain.
                logger.warning(
                    "retrying %s without adaptive thinking / effort=%r after 400: %s",
                    self.model,
                    effort,
                    exc,
                )
                response = self._anthropic.messages.parse(**call)  # type: ignore[arg-type]

        usage = response.usage
        self.tracker.record(self.model, usage.input_tokens, usage.output_tokens, effort)
        parsed = response.parsed_output
        if parsed is None:
            raise RuntimeError(f"structured parse returned no output (stop={response.stop_reason})")
        return cast(T, parsed)
