
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.schemas.ai_diagnosis import AIDiagnosis
from app.schemas.diagnosis_analysis import DiagnosisAnalysis
from app.schemas.incident_context import (
    IncidentContext,
    IncidentContextIncident,
    EvidenceCollectionStatus,
)
from app.services.diagnosis_service import DiagnosisService


class FakeContextService:
    def __init__(self, context):
        self.context = context
        self.call_count = 0

    async def collect(self, incident):
        self.call_count += 1
        return self.context


class FakeEvidenceValidator:
    def validate(self, context):
        return SimpleNamespace(
            is_sufficient=False,
            warnings=["Insufficient test evidence"],
            matched_sources=[],
        )


def create_context(incident_id):
    now = datetime.now(timezone.utc)

    return IncidentContext(
        incident=IncidentContextIncident(
            id=incident_id,
            fingerprint="test-fingerprint",
            alert_name="TestAlert",
            namespace="voting-app",
            pod="test-pod",
            severity="high",
            status="open",
            summary="Test incident",
            first_seen_at=now,
            last_seen_at=now,
        ),
        evidence={},
        collection_status=EvidenceCollectionStatus(
            prometheus="success",
            loki="failed",
            kubernetes="failed",
        ),
        collected_at=now,
    )


@pytest.mark.asyncio
async def test_diagnosis_service_passes_same_analysis_to_ai():
    incident_id = uuid4()
    incident = SimpleNamespace(id=incident_id)

    context = create_context(incident_id)
    context_service = FakeContextService(context)

    ai_result = AIDiagnosis(
        status="success",
        probable_cause="Test probable cause",
        explanation="Test explanation",
        confidence=0.9,
        supporting_evidence=["test-evidence"],
        investigation_steps=["Inspect pod status"],
    )

    ai_service = SimpleNamespace(
        diagnose=AsyncMock(return_value=ai_result)
    )

    service = DiagnosisService(
        context_service=context_service,
        evidence_validator=FakeEvidenceValidator(),
        ai_diagnosis_service=ai_service,
    )

    result = await service.diagnose_with_context(incident)

    assert isinstance(result, DiagnosisAnalysis)
    assert result.ai_diagnosis == ai_result

    ai_service.diagnose.assert_awaited_once()

    passed_analysis = ai_service.diagnose.await_args.args[0]

    assert passed_analysis is result

    assert passed_analysis.context is context
    assert passed_analysis.diagnosis == result.diagnosis
    assert passed_analysis.ai_diagnosis == ai_result

    assert context_service.call_count == 1


@pytest.mark.asyncio
async def test_diagnosis_service_skips_ai_when_not_configured():
    incident_id = uuid4()
    incident = SimpleNamespace(id=incident_id)

    context = create_context(incident_id)
    context_service = FakeContextService(context)

    service = DiagnosisService(
        context_service=context_service,
        evidence_validator=FakeEvidenceValidator(),
    )

    result = await service.diagnose_with_context(incident)

    assert result.ai_diagnosis is None
    assert result.context is context
    assert context_service.call_count == 1
