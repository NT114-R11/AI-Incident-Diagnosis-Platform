from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.diagnosis import DiagnosisResult
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


@pytest.mark.asyncio
async def test_diagnose_with_context_returns_both_results():
    incident_id = uuid4()
    now = datetime.now(timezone.utc)

    incident = SimpleNamespace(id=incident_id)

    context = IncidentContext(
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

    context_service = FakeContextService(context)

    service = DiagnosisService(
        context_service=context_service,
        evidence_validator=FakeEvidenceValidator(),
    )

    result = await service.diagnose_with_context(incident)

    assert isinstance(result, DiagnosisAnalysis)
    assert isinstance(result.diagnosis, DiagnosisResult)
    assert isinstance(result.context, IncidentContext)

    assert result.diagnosis.incident_id == incident_id
    assert result.diagnosis.status == "insufficient_evidence"

    assert result.context is context

    # Evidence must only be collected once per analysis.
    assert context_service.call_count == 1