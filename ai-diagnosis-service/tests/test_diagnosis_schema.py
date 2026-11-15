
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.diagnosis import (
    DiagnosisFinding,
    DiagnosisResult,
)


@pytest.fixture
def valid_finding_data():
    return {
        "rule_id": "POD_CRASH_LOOP",
        "category": "pod_crash_loop",
        "title": "Pod is in CrashLoopBackOff",
        "description": "Container repeatedly fails to start.",
        "severity": "critical",
        "confidence": 0.95,
        "evidence_refs": [
            "kubernetes.pods[0].containers[0].state",
        ],
    }


@pytest.fixture
def valid_diagnosis_data(valid_finding_data):
    return {
        "incident_id": uuid4(),
        "status": "diagnosed",
        "analyzed_at": datetime.now(timezone.utc),
        "probable_cause": "Container repeatedly crashes.",
        "confidence": 0.95,
        "severity": "critical",
        "summary": "A pod is experiencing CrashLoopBackOff.",
        "findings": [valid_finding_data],
        "evidence_refs": [
            "kubernetes.pods[0].containers[0].state",
        ],
    }


class TestDiagnosisFinding:

    def test_create_valid_finding(self, valid_finding_data):
        finding = DiagnosisFinding(**valid_finding_data)

        assert finding.rule_id == "POD_CRASH_LOOP"
        assert finding.category == "pod_crash_loop"
        assert finding.severity == "critical"
        assert finding.confidence == 0.95

    def test_reject_invalid_category(self, valid_finding_data):
        valid_finding_data["category"] = "unknown_category"

        with pytest.raises(ValidationError):
            DiagnosisFinding(**valid_finding_data)

    def test_reject_invalid_severity(self, valid_finding_data):
        valid_finding_data["severity"] = "warning"

        with pytest.raises(ValidationError):
            DiagnosisFinding(**valid_finding_data)

    @pytest.mark.parametrize("confidence", [-0.1, 1.1])
    def test_reject_confidence_out_of_range(
        self,
        valid_finding_data,
        confidence,
    ):
        valid_finding_data["confidence"] = confidence

        with pytest.raises(ValidationError):
            DiagnosisFinding(**valid_finding_data)

    def test_reject_too_many_evidence_refs(self, valid_finding_data):
        valid_finding_data["evidence_refs"] = [
            f"evidence.ref.{index}" for index in range(51)
        ]

        with pytest.raises(ValidationError):
            DiagnosisFinding(**valid_finding_data)


class TestDiagnosisResult:

    def test_create_valid_diagnosis(self, valid_diagnosis_data):
        diagnosis = DiagnosisResult(**valid_diagnosis_data)

        assert diagnosis.status == "diagnosed"
        assert diagnosis.severity == "critical"
        assert len(diagnosis.findings) == 1
        assert diagnosis.findings[0].rule_id == "POD_CRASH_LOOP"

    @pytest.mark.parametrize(
        "status",
        [
            "diagnosed",
            "no_issue_detected",
            "insufficient_evidence",
        ],
    )
    def test_accept_valid_status(self, valid_diagnosis_data, status):
        valid_diagnosis_data["status"] = status

        diagnosis = DiagnosisResult(**valid_diagnosis_data)

        assert diagnosis.status == status

    def test_reject_invalid_status(self, valid_diagnosis_data):
        valid_diagnosis_data["status"] = "unknown"

        with pytest.raises(ValidationError):
            DiagnosisResult(**valid_diagnosis_data)

    def test_reject_confidence_out_of_range(self, valid_diagnosis_data):
        valid_diagnosis_data["confidence"] = 1.5

        with pytest.raises(ValidationError):
            DiagnosisResult(**valid_diagnosis_data)

    def test_reject_invalid_incident_id(self, valid_diagnosis_data):
        valid_diagnosis_data["incident_id"] = "not-a-uuid"

        with pytest.raises(ValidationError):
            DiagnosisResult(**valid_diagnosis_data)

    def test_reject_unexpected_field(self, valid_diagnosis_data):
        valid_diagnosis_data["unexpected"] = "not allowed"

        with pytest.raises(ValidationError):
            DiagnosisResult(**valid_diagnosis_data)

    def test_allow_empty_findings(self, valid_diagnosis_data):
        valid_diagnosis_data["status"] = "no_issue_detected"
        valid_diagnosis_data["findings"] = []
        valid_diagnosis_data["probable_cause"] = None
        valid_diagnosis_data["severity"] = None

        diagnosis = DiagnosisResult(**valid_diagnosis_data)

        assert diagnosis.findings == []
        assert diagnosis.probable_cause is None
        assert diagnosis.severity is None
