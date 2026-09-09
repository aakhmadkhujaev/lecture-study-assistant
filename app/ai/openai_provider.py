"""OpenAI provider implementation."""

from openai import OpenAI

from config.settings import Settings

from app.ai.provider import AIConfigurationError, AIRequestError


class OpenAIProvider:
    """Generate JSON responses with the configured OpenAI model."""

    def __init__(self, settings: Settings) -> None:
        api_key = settings.openai_api_key
        if not api_key:
            raise AIConfigurationError(
                "OPENAI_API_KEY is not configured. Add it to .env before using the optional OpenAI provider."
            )
        if not settings.ai_model:
            raise AIConfigurationError(
                "AI_MODEL is not configured. Add the model name to .env before using the optional OpenAI provider."
            )
        self._client = OpenAI(api_key=api_key)
        self._model = settings.ai_model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Request JSON-only structured output from OpenAI."""
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content
        except Exception as error:
            raise AIRequestError(f"The AI request failed: {error}") from error
        if not content:
            raise AIRequestError("The AI returned an empty response.")
        return content
