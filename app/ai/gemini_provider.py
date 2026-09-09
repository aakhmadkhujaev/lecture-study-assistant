"""Google Gemini provider implementation."""

from typing import Any

from google import genai
from google.genai import types

from config.settings import Settings

from app.ai.provider import AIConfigurationError, AIRequestError
from app.ai.schemas import StudyGuide


def _gemini_response_schema() -> dict[str, Any]:
    """Return the Pydantic schema with unsupported Gemini fields removed."""
    schema = StudyGuide.model_json_schema()
    return _remove_unsupported_schema_fields(schema)


def _remove_unsupported_schema_fields(value: Any) -> Any:
    """Remove unsupported additional-properties keywords recursively."""
    if isinstance(value, dict):
        return {
            key: _remove_unsupported_schema_fields(item)
            for key, item in value.items()
            if key not in {"additionalProperties", "additional_properties"}
        }
    if isinstance(value, list):
        return [_remove_unsupported_schema_fields(item) for item in value]
    return value


class GeminiProvider:
    """Generate validated JSON responses with the configured Gemini model."""

    def __init__(self, settings: Settings) -> None:
        api_key = settings.gemini_api_key
        if not api_key:
            raise AIConfigurationError(
                "GEMINI_API_KEY is not configured. Add it to .env before generating a study guide."
            )
        if not settings.ai_model:
            raise AIConfigurationError(
                "GEMINI_MODEL is not configured. Add the model name to .env before generating a study guide."
            )
        try:
            self._client = genai.Client(api_key=api_key)
        except Exception as error:
            raise AIRequestError(f"The AI client could not be initialized: {error}") from error
        self._model = settings.ai_model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Request a JSON-only structured response from Gemini."""
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0,
                    response_mime_type="application/json",
                    response_json_schema=_gemini_response_schema(),
                ),
            )
            content = response.text
        except Exception as error:
            raise AIRequestError(f"The AI request failed: {error}") from error
        if not content:
            raise AIRequestError("The AI returned an empty response.")
        return content