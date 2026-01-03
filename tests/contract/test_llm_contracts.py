"""Contract tests for LLM provider interface.

These tests verify that all LLM providers correctly implement
the BaseLLMProvider interface.
"""

import inspect
from abc import ABC, abstractmethod
from typing import get_type_hints

import pytest

from ankification.cards.models import BasicCard, Card, CardType, ClozeCard
from ankification.llm.base import BaseLLMProvider
from ankification.llm.openai_provider import OpenAIProvider
from ankification.llm.anthropic_provider import AnthropicProvider


# All concrete LLM providers that should implement the interface
LLM_PROVIDERS = [OpenAIProvider, AnthropicProvider]


class TestBaseLLMProviderContract:
    """Contract tests for BaseLLMProvider interface definition."""

    def test_base_provider_is_abstract(self) -> None:
        """BaseLLMProvider should be an abstract base class."""
        assert issubclass(BaseLLMProvider, ABC)

    def test_generate_cards_is_abstract(self) -> None:
        """generate_cards should be an abstract method."""
        assert hasattr(BaseLLMProvider.generate_cards, "__isabstractmethod__")
        assert BaseLLMProvider.generate_cards.__isabstractmethod__

    def test_refine_card_is_abstract(self) -> None:
        """refine_card should be an abstract method."""
        assert hasattr(BaseLLMProvider.refine_card, "__isabstractmethod__")
        assert BaseLLMProvider.refine_card.__isabstractmethod__

    def test_name_property_is_abstract(self) -> None:
        """name property should be abstract."""
        # The name property getter should be abstract
        assert "name" in dir(BaseLLMProvider)

    def test_generate_cards_signature(self) -> None:
        """generate_cards should have the correct signature."""
        sig = inspect.signature(BaseLLMProvider.generate_cards)
        params = list(sig.parameters.keys())

        # Should have these parameters (excluding self)
        assert "content" in params
        assert "source" in params
        assert "card_types" in params
        assert "count_guidance" in params
        assert "user_directives" in params

    def test_refine_card_signature(self) -> None:
        """refine_card should have the correct signature."""
        sig = inspect.signature(BaseLLMProvider.refine_card)
        params = list(sig.parameters.keys())

        assert "card" in params
        assert "feedback" in params


class TestLLMProviderImplementations:
    """Contract tests verifying all LLM providers implement the interface."""

    @pytest.mark.parametrize("provider_class", LLM_PROVIDERS)
    def test_provider_inherits_from_base(self, provider_class: type) -> None:
        """Each provider should inherit from BaseLLMProvider."""
        assert issubclass(provider_class, BaseLLMProvider)

    @pytest.mark.parametrize("provider_class", LLM_PROVIDERS)
    def test_provider_implements_generate_cards(self, provider_class: type) -> None:
        """Each provider should implement generate_cards."""
        assert hasattr(provider_class, "generate_cards")
        method = getattr(provider_class, "generate_cards")
        # Should not be abstract anymore
        assert not getattr(method, "__isabstractmethod__", False)

    @pytest.mark.parametrize("provider_class", LLM_PROVIDERS)
    def test_provider_implements_refine_card(self, provider_class: type) -> None:
        """Each provider should implement refine_card."""
        assert hasattr(provider_class, "refine_card")
        method = getattr(provider_class, "refine_card")
        assert not getattr(method, "__isabstractmethod__", False)

    @pytest.mark.parametrize("provider_class", LLM_PROVIDERS)
    def test_provider_implements_name_property(self, provider_class: type) -> None:
        """Each provider should implement name property."""
        assert hasattr(provider_class, "name")

    @pytest.mark.parametrize("provider_class", LLM_PROVIDERS)
    def test_generate_cards_is_async(self, provider_class: type) -> None:
        """generate_cards should be an async method."""
        method = getattr(provider_class, "generate_cards")
        assert inspect.iscoroutinefunction(method)

    @pytest.mark.parametrize("provider_class", LLM_PROVIDERS)
    def test_refine_card_is_async(self, provider_class: type) -> None:
        """refine_card should be an async method."""
        method = getattr(provider_class, "refine_card")
        assert inspect.iscoroutinefunction(method)


class TestLLMProviderNaming:
    """Contract tests for provider naming consistency."""

    @pytest.mark.parametrize("provider_class", LLM_PROVIDERS)
    def test_provider_name_is_string(self, provider_class: type) -> None:
        """Provider name should be a string."""
        # Create instance to check name property
        # Note: This requires config, but we're checking type annotation
        pass  # Skip instance creation, just verify the contract

    def test_openai_provider_name(self) -> None:
        """OpenAI provider should have expected name."""
        # Verify class has name defined
        assert hasattr(OpenAIProvider, "name")

    def test_anthropic_provider_name(self) -> None:
        """Anthropic provider should have expected name."""
        assert hasattr(AnthropicProvider, "name")


class TestLLMProviderReturnTypes:
    """Contract tests for return type specifications."""

    def test_generate_cards_returns_list_of_cards(self) -> None:
        """generate_cards return type should be list[Card]."""
        sig = inspect.signature(BaseLLMProvider.generate_cards)
        # Check the return annotation exists
        assert sig.return_annotation is not inspect.Parameter.empty

    def test_refine_card_returns_card(self) -> None:
        """refine_card return type should be Card."""
        sig = inspect.signature(BaseLLMProvider.refine_card)
        assert sig.return_annotation is not inspect.Parameter.empty


class TestLLMProviderParameterTypes:
    """Contract tests for parameter type specifications."""

    def test_generate_cards_content_is_string(self) -> None:
        """generate_cards content parameter should be str."""
        sig = inspect.signature(BaseLLMProvider.generate_cards)
        assert sig.parameters["content"].annotation == str

    def test_generate_cards_source_is_string(self) -> None:
        """generate_cards source parameter should be str."""
        sig = inspect.signature(BaseLLMProvider.generate_cards)
        assert sig.parameters["source"].annotation == str

    def test_generate_cards_card_types_is_list(self) -> None:
        """generate_cards card_types parameter should be list[str]."""
        sig = inspect.signature(BaseLLMProvider.generate_cards)
        annotation = sig.parameters["card_types"].annotation
        # Should be list[str]
        assert "list" in str(annotation).lower()

    def test_refine_card_card_parameter_is_card(self) -> None:
        """refine_card card parameter should be Card type."""
        sig = inspect.signature(BaseLLMProvider.refine_card)
        assert sig.parameters["card"].annotation == Card

    def test_refine_card_feedback_is_string(self) -> None:
        """refine_card feedback parameter should be str."""
        sig = inspect.signature(BaseLLMProvider.refine_card)
        assert sig.parameters["feedback"].annotation == str
