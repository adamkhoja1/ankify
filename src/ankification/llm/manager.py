"""LLM provider manager."""

from ..config import Config
from .anthropic_provider import AnthropicProvider
from .base import BaseLLMProvider
from .openai_provider import OpenAIProvider


class LLMManager:
    """Manages LLM providers."""

    def __init__(self, config: Config) -> None:
        """Initialize LLM manager with configuration.

        Args:
            config: Application configuration
        """
        self.config = config
        self._providers: dict[str, BaseLLMProvider] = {}

    def get_provider(self, provider_name: str | None = None) -> BaseLLMProvider:
        """Get an LLM provider by name.

        Args:
            provider_name: Provider name ('openai' or 'anthropic').
                          If None, uses default from config.

        Returns:
            LLM provider instance

        Raises:
            ValueError: If provider is unknown or API key is missing
        """
        if provider_name is None:
            provider_name = self.config.llm.default_provider

        provider_name = provider_name.lower()

        # Return cached provider if available
        if provider_name in self._providers:
            return self._providers[provider_name]

        # Create new provider
        provider: BaseLLMProvider

        if provider_name == "openai":
            api_key = self.config.llm.openai.api_key
            if not api_key:
                raise ValueError(
                    "OpenAI API key not configured. Set it in config or OPENAI_API_KEY env var."
                )

            provider = OpenAIProvider(
                api_key=api_key,
                model=self.config.llm.openai.model,
                temperature=self.config.llm.openai.temperature,
            )

        elif provider_name == "anthropic":
            api_key = self.config.llm.anthropic.api_key
            if not api_key:
                raise ValueError(
                    "Anthropic API key not configured. "
                    "Set it in config or ANTHROPIC_API_KEY env var."
                )

            provider = AnthropicProvider(
                api_key=api_key,
                model=self.config.llm.anthropic.model,
                temperature=self.config.llm.anthropic.temperature,
            )

        else:
            raise ValueError(
                f"Unknown provider: {provider_name}. Must be 'openai' or 'anthropic'."
            )

        # Cache provider
        self._providers[provider_name] = provider
        return provider
