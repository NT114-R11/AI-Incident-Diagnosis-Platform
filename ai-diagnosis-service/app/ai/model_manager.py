from asyncio import TimeoutError as AsyncTimeoutError
from google.genai import errors
from pydantic import BaseModel

from app.ai.providers.gemini_provider import GeminiProvider
from app.config import settings


class ModelManager:
    RETRYABLE_API_CODES = {408, 429}

    def __init__(
        self,
        primary_provider=None,
        fallback_provider=None,
        fallback_enabled: bool | None = None,
    ):
        self.primary_provider = primary_provider or GeminiProvider(
            model=settings.gemini_primary_model
        )

        self.fallback_provider = fallback_provider

        if self.fallback_provider is None and settings.gemini_fallback_enabled:
            self.fallback_provider = GeminiProvider(
                model=settings.gemini_fallback_model
            )

        self.fallback_enabled = (
            settings.gemini_fallback_enabled
            if fallback_enabled is None
            else fallback_enabled
        )

    @classmethod
    def _is_retryable_error(cls, error: Exception) -> bool:
        if isinstance(error, errors.APIError):
            status_code = error.code

            return (
                status_code in cls.RETRYABLE_API_CODES
                or status_code >= 500
            )

        return isinstance(
            error,
            (TimeoutError, AsyncTimeoutError, ConnectionError, OSError),
        )

    async def generate(self,prompt: str,response_schema: type[BaseModel] | None = None) -> str | BaseModel:
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        try:
            if response_schema is None:
                return await self.primary_provider.generate(prompt)

            return await self.primary_provider.generate(
                prompt,
                response_schema=response_schema,
            )

        except Exception as primary_error:
            if not self._is_retryable_error(primary_error):
                raise

            if not self.fallback_enabled or self.fallback_provider is None:
                raise

            try:
                if response_schema is None:
                    return await self.fallback_provider.generate(prompt)

                return await self.fallback_provider.generate(
                    prompt,
                    response_schema=response_schema,
                )

            except Exception as fallback_error:
                raise RuntimeError(
                    "All configured Gemini models failed"
                ) from fallback_error


    async def close(self) -> None:
        providers = [self.primary_provider, self.fallback_provider]
        closed = set()

        for provider in providers:
            if provider is None or id(provider) in closed:
                continue

            closed.add(id(provider))
            await provider.close()
