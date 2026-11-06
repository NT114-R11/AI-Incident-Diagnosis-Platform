import pytest
from pydantic import ValidationError

from models import RemediationRequest


@pytest.fixture
def valid_request():
    return {
        "schema_version": "1.0",
        "request_id": "req-001",
        "incident_id": "inc-001",
        "created_at": "2026-11-06T13:00:00Z",
        "expires_at": "2026-11-06T13:10:00Z",
        "incident": {
            "title": "Vote deployment unhealthy",
            "severity": "critical",
            "namespace": "voting-app",
            "resource_type": "deployment",
            "resource_name": "vote",
            "summary": "Deployment has unavailable replicas."
        },
        "diagnosis": {
            "probable_cause": "Pods are failing readiness checks.",
            "confidence": 0.91,
            "evidence_refs": [
                "prometheus://evidence/123",
                "loki://evidence/456"
            ]
        },
        "proposed_action": {
            "action_id": "act-001",
            "action_type": "restart_deployment",
            "parameters": {
                "namespace": "voting-app",
                "deployment": "vote"
            },
            "reason": "Restart unhealthy deployment."
        }
    }


def test_valid_remediation_request(valid_request):
    request = RemediationRequest.model_validate(valid_request)

    assert request.request_id == "req-001"
    assert request.proposed_action.action_type == "restart_deployment"


def test_invalid_severity(valid_request):
    valid_request["incident"]["severity"] = "emergency"

    with pytest.raises(ValidationError):
        RemediationRequest.model_validate(valid_request)


def test_invalid_confidence(valid_request):
    valid_request["diagnosis"]["confidence"] = 1.5

    with pytest.raises(ValidationError):
        RemediationRequest.model_validate(valid_request)


def test_expiration_before_creation(valid_request):
    valid_request["expires_at"] = "2026-11-06T12:00:00Z"

    with pytest.raises(ValidationError):
        RemediationRequest.model_validate(valid_request)


def test_namespace_mismatch(valid_request):
    valid_request["proposed_action"]["parameters"]["namespace"] = "default"

    with pytest.raises(ValidationError):
        RemediationRequest.model_validate(valid_request)


def test_extra_field_rejected(valid_request):
    valid_request["unexpected_field"] = "not-allowed"

    with pytest.raises(ValidationError):
        RemediationRequest.model_validate(valid_request)
 