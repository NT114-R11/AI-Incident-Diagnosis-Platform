
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.ai.diagnosis_service import AIDiagnosisService
from app.schemas.ai_diagnosis import AIDiagnosis


@pytest.fixture
def analysis():
    incident_id = uuid4()

    return SimpleNamespace(
        diagnosis=SimpleNamespace(
            model_dump=lambda **kwargs: {
                "incident_id": str(incident_id),
                "status": "diagnosed",
                "probable_cause": "Container repeatedly crashes",
                "confidence": 0.95,
                "findings": [],
            }
        ),
        context=SimpleNamespace(
            incident=SimpleNamespace(
                id=incident_id,
                model_dump=lambda **kwargs: {
                    "id": str(incident_id),
                    "alert_name": "PodCrashLoopBackOff",
                    "namespace": "ecommerce",
                    "pod": "order-service-123",
                },
            ),
            evidence={
                "kubernetes": {
                    "container_reason": "CrashLoopBackOff",
                }
            },
            collection_status=SimpleNamespace(
                model_dump=lambda: {
                    "prometheus": "success",
                    "loki": "success",
                    "kubernetes": "success",
                }
            ),
            collected_at=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture
def model_manager():
    manager = SimpleNamespace()
    manager.generate = AsyncMock()
    return manager


@pytest.mark.asyncio
async def test_diagnose_returns_ai_result(analysis, model_manager):
    expected = AIDiagnosis(
        status="success",
        probable_cause="Database connection failure",
        explanation="The container logs indicate database connection errors.",
        confidence=0.9,
        supporting_evidence=["loki.errors"],
        investigation_steps=["Inspect database connectivity"],
    )

    model_manager.generate.return_value = expected

    service = AIDiagnosisService(model_manager=model_manager)

    result = await service.diagnose(analysis)

    assert result == expected
    assert result.status == "success"

    model_manager.generate.assert_awaited_once()

    kwargs = model_manager.generate.await_args.kwargs
    assert kwargs["response_schema"] is AIDiagnosis


@pytest.mark.asyncio
async def test_diagnose_returns_unavailable_when_ai_fails(
    analysis,
    model_manager,
):
    model_manager.generate.side_effect = RuntimeError(
        "All configured Gemini models failed"
    )

    service = AIDiagnosisService(model_manager=model_manager)

    result = await service.diagnose(analysis)

    assert result.status == "unavailable"
    assert result.probable_cause is None
    assert result.explanation is None
    assert result.confidence is None
    assert result.supporting_evidence == []
    assert result.investigation_steps == []


@pytest.mark.asyncio
async def test_diagnose_uses_existing_analysis_without_collecting_again(
    analysis,
    model_manager,
):
    model_manager.generate.return_value = AIDiagnosis(
        status="success",
        explanation="Analysis completed",
    )

    service = AIDiagnosisService(model_manager=model_manager)

    await service.diagnose(analysis)

    prompt = model_manager.generate.await_args.args[0]

    assert "PodCrashLoopBackOff" in prompt
    assert "CrashLoopBackOff" in prompt
