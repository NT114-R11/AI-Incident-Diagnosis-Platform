
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from pydantic import BaseModel
from google.genai import types
import pytest
from google.genai import errors

from app.ai.providers.gemini_provider import GeminiProvider
class MockAIResponse(BaseModel):
    status: str
    confidence: float



@pytest.mark.asyncio
async def test_generate_returns_structured_response(provider):
    expected = MockAIResponse(
        status="diagnosed",
        confidence=0.95,
    )

    provider.client.aio.models.generate_content.return_value = (
        SimpleNamespace(
            parsed=expected,
            text=expected.model_dump_json(),
        )
    )

    result = await provider.generate(
        "Analyze incident",
        response_schema=MockAIResponse,
    )

    assert isinstance(result, MockAIResponse)
    assert result.status == "diagnosed"
    assert result.confidence == 0.95

    call_kwargs = (
        provider.client.aio.models.generate_content.await_args.kwargs
    )

    assert call_kwargs["model"] == "gemini-test"
    assert call_kwargs["contents"] == "Analyze incident"
    assert isinstance(
        call_kwargs["config"],
        types.GenerateContentConfig,
    )
    assert call_kwargs["config"].response_mime_type == "application/json"


@pytest.mark.asyncio
async def test_generate_validates_structured_json(provider):
    provider.client.aio.models.generate_content.return_value = (
        SimpleNamespace(
            parsed=None,
            text='{"status": "diagnosed", "confidence": 0.85}',
        )
    )

    result = await provider.generate(
        "Analyze incident",
        response_schema=MockAIResponse,
    )

    assert isinstance(result, MockAIResponse)
    assert result.status == "diagnosed"
    assert result.confidence == 0.85


@pytest.fixture
def provider():
    instance = GeminiProvider.__new__(GeminiProvider)
    instance.model = "gemini-test"

    instance.client = MagicMock()
    instance.client.aio.models.generate_content = AsyncMock()

    return instance


@pytest.mark.asyncio
async def test_generate_returns_response_text(provider):
    provider.client.aio.models.generate_content.return_value = (
        SimpleNamespace(text="Incident analysis result")
    )

    result = await provider.generate("Analyze this incident")

    assert result == "Incident analysis result"

    provider.client.aio.models.generate_content.assert_awaited_once_with(
        model="gemini-test",
        contents="Analyze this incident",
        config=None
    )


@pytest.mark.asyncio
async def test_generate_rejects_empty_prompt(provider):
    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        await provider.generate("   ")

    provider.client.aio.models.generate_content.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_rejects_empty_response(provider):
    provider.client.aio.models.generate_content.return_value = (
        SimpleNamespace(text=None)
    )

    with pytest.raises(RuntimeError, match="empty response"):
        await provider.generate("Analyze this incident")


@pytest.mark.asyncio
async def test_generate_propagates_api_error(provider):
    api_error = errors.APIError(
        code=503,
        response_json={"error": {"message": "Service unavailable"}},
        response=None,
    )

    provider.client.aio.models.generate_content.side_effect = api_error

    with pytest.raises(errors.APIError):
        await provider.generate("Analyze this incident")
