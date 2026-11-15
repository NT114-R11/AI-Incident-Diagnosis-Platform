
from pydantic import BaseModel
from google import genai
from google.genai import errors, types

from app.config import settings


class GeminiProvider:
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.model = model
        self.api_key = api_key or settings.gemini_api_key
        self.timeout_seconds = (
            timeout_seconds or settings.gemini_timeout_seconds
        )

        if not self.api_key:
            raise ValueError("Gemini API key is not configured")

        self.client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(
                timeout=int(self.timeout_seconds * 1000),
            ),
        )

    async def generate(self, prompt: str, response_schema: type[BaseModel] | None = None) -> str | BaseModel:
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        config = None

        if response_schema is not None:
            schema = response_schema.model_json_schema()
            schema.pop("additionalProperties", None)
            
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema
            )

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config
            )

            if response_schema is None:
                if not response.text:
                    raise RuntimeError("Gemini returned an empty response")

                return response.text

            if response.parsed is not None:
                return response_schema.model_validate(response.parsed)

            if response.text:
                return response_schema.model_validate_json(response.text)

            raise RuntimeError("Gemini returned an empty structured response")

        except errors.APIError:
            raise

    async def close(self) -> None:
        await self.client.aio.aclose()
