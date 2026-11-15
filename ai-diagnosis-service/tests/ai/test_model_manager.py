from unittest.mock import AsyncMock
import pytest
from app.ai.model_manager import ModelManager
from google.genai import errors
from pydantic import BaseModel


class MockAIResponse(BaseModel):
    status: str
    confidence: float



@pytest.mark.asyncio
async def test_primary_receives_response_schema(
    primary_provider,
    fallback_provider,
):
    expected = MockAIResponse(
        status="diagnosed",
        confidence=0.9,
    )
    primary_provider.generate.return_value = expected

    manager = ModelManager(
        primary_provider=primary_provider,
        fallback_provider=fallback_provider,
    )

    result = await manager.generate(
        "Analyze incident",
        response_schema=MockAIResponse,
    )

    assert result == expected

    primary_provider.generate.assert_awaited_once_with(
        "Analyze incident",
        response_schema=MockAIResponse,
    )
    fallback_provider.generate.assert_not_awaited()

@pytest.mark.asyncio
async def test_fallback_receives_same_response_schema(
    primary_provider,
    fallback_provider,
):
    primary_provider.generate.side_effect = errors.APIError(
        code=503,
        response_json={"error": {"message": "Service unavailable"}},
        response=None,
    )

    expected = MockAIResponse(
        status="diagnosed",
        confidence=0.85,
    )
    fallback_provider.generate.return_value = expected

    manager = ModelManager(
        primary_provider=primary_provider,
        fallback_provider=fallback_provider,
    )

    result = await manager.generate(
        "Analyze incident",
        response_schema=MockAIResponse,
    )

    assert result == expected

    fallback_provider.generate.assert_awaited_once_with(
        "Analyze incident",
        response_schema=MockAIResponse,
    )

@pytest.fixture
def primary_provider():
    provider = AsyncMock()
    return provider


@pytest.fixture
def fallback_provider():
    provider = AsyncMock()
    return provider


@pytest.mark.asyncio
async def test_primary_success_does_not_call_fallback(
    primary_provider,
    fallback_provider,
):
    primary_provider.generate.return_value = "Primary result"

    manager = ModelManager(
        primary_provider=primary_provider,
        fallback_provider=fallback_provider,
    )

    result = await manager.generate("Analyze incident")

    assert result == "Primary result"
    primary_provider.generate.assert_awaited_once_with("Analyze incident")
    fallback_provider.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_primary_failure_uses_fallback(
    primary_provider,
    fallback_provider,
):
    primary_provider.generate.side_effect = errors.APIError(
        code=503,
        response_json={"error": {"message": "Service unavailable"}},
        response=None,
    )
    fallback_provider.generate.return_value = "Fallback result"

    manager = ModelManager(
        primary_provider=primary_provider,
        fallback_provider=fallback_provider,
    )

    result = await manager.generate("Analyze incident")

    assert result == "Fallback result"
    primary_provider.generate.assert_awaited_once()
    fallback_provider.generate.assert_awaited_once()

@pytest.mark.asyncio
async def test_all_models_failure_raises_error(
    primary_provider,
    fallback_provider,
):
    primary_provider.generate.side_effect = errors.APIError(
        code=503,
        response_json={"error": {"message": "Primary unavailable"}},
        response=None,
    )

    fallback_provider.generate.side_effect = RuntimeError(
        "Fallback unavailable"
    )

    manager = ModelManager(
        primary_provider=primary_provider,
        fallback_provider=fallback_provider,
    )

    with pytest.raises(
        RuntimeError,
        match="All configured Gemini models failed",
    ):
        await manager.generate("Analyze incident")

    primary_provider.generate.assert_awaited_once()
    fallback_provider.generate.assert_awaited_once()

    
@pytest.mark.asyncio
async def test_fallback_disabled_does_not_call_fallback(
    primary_provider,
    fallback_provider,
):
    primary_provider.generate.side_effect = RuntimeError("Primary unavailable")

    manager = ModelManager(
        primary_provider=primary_provider,
        fallback_provider=fallback_provider,
        fallback_enabled=False,
    )

    with pytest.raises(RuntimeError, match="Primary unavailable"):
        await manager.generate("Analyze incident")

    fallback_provider.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_empty_prompt_is_rejected(
    primary_provider,
    fallback_provider,
):
    manager = ModelManager(
        primary_provider=primary_provider,
        fallback_provider=fallback_provider,
    )

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        await manager.generate("   ")

    primary_provider.generate.assert_not_awaited()
    fallback_provider.generate.assert_not_awaited()
@pytest.mark.asyncio
async def test_non_retryable_error_does_not_use_fallback(
    primary_provider,
    fallback_provider,
):
    primary_provider.generate.side_effect = ValueError("Invalid request")

    manager = ModelManager(
        primary_provider=primary_provider,
        fallback_provider=fallback_provider,
    )

    with pytest.raises(ValueError, match="Invalid request"):
        await manager.generate("Analyze incident")

    fallback_provider.generate.assert_not_awaited()