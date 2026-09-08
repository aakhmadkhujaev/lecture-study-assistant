"""Provider abstraction for structured language-model generation."""

from typing import Protocol


class AIProviderError(Exception):
    """Base class for expected provider failures."""


class AIConfigurationError(AIProviderError):
    """Raised when the provider is not configured."""


class AIRequestError(AIProviderError):
    """Raised when the provider request fails."""


class LLMProvider(Protocol):
    """Interface used by the study-guide generator."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return the provider's structured JSON response."""
