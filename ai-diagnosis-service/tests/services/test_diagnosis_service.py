
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.schemas.evidence_validation import EvidenceValidationResult
from app.services.diagnosis_service import DiagnosisService

from app.schemas.incident_context import (
    IncidentContext,
    IncidentContextIncident,
    EvidenceCollectionStatus,
)
INCIDENT_ID = UUID("00baaf85-5351-4806-88f9-62913bdef9da")


class FakeIncidentContextService:
    def __init__(self, context):
        self.context = context
        self.called = False

    async def collect(self, incident):
        self.called = True
        return self.context


class FakeEvidenceValidator:
    def __init__(self, result):
        self.result = result
        self.called = False

    def validate(self, context):
        self.called = True
        return self.result


@pytest.mark.asyncio
async def test_insufficient_evidence_returns_without_diagnosis():
    now = datetime.now(timezone.utc)

    context = IncidentContext(
        incident=IncidentContextIncident(
            id=INCIDENT_ID,
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
            loki="success",
            kubernetes="failed",
        ),
        collected_at=now,
    )
    context_service = FakeIncidentContextService(context)

    validation_result = EvidenceValidationResult(
        is_sufficient=False,
        available_sources=["prometheus"],
        unavailable_sources=["loki", "kubernetes"],
        warnings=["No relevant Prometheus evidence found."],
        validated_at=datetime.now(timezone.utc),
    )

    validator = FakeEvidenceValidator(validation_result)

    service = DiagnosisService(
        context_service=context_service,
        evidence_validator=validator,
    )
    incident = SimpleNamespace(id=INCIDENT_ID)
    result = await service.diagnose(incident)

    assert context_service.called is True
    assert validator.called is True

    assert result.incident_id == INCIDENT_ID
    assert result.status == "insufficient_evidence"
    assert result.confidence == 0.0
    assert result.probable_cause is None
    assert result.severity is None
    assert result.findings == []


@pytest.mark.asyncio
async def test_sufficient_evidence_reaches_diagnosis_stage():
    incident = SimpleNamespace(id=INCIDENT_ID)

    now = datetime.now(timezone.utc)

    context = IncidentContext(
        incident=IncidentContextIncident(
            id=INCIDENT_ID,
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
            loki="success",
            kubernetes="failed",
        ),
        collected_at=now,
    )

    context_service = FakeIncidentContextService(context)

    validation_result = EvidenceValidationResult(
        is_sufficient=True,
        available_sources=["prometheus", "loki"],
        unavailable_sources=["kubernetes"],
        warnings=[],
        validated_at=datetime.now(timezone.utc),
    )

    validator = FakeEvidenceValidator(validation_result)

    service = DiagnosisService(
        context_service=context_service,
        evidence_validator=validator,
    )

    result = await service.diagnose(incident)

    assert result.incident_id == INCIDENT_ID
    assert result.status == "no_issue_detected"
    assert result.findings == []
    assert result.confidence == 0.0
