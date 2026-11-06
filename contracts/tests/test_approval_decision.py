import pytest
from pydantic import ValidationError

from models import ApprovalDecision


@pytest.fixture
def valid_decision():
    return {
        "schema_version": "1.0",
        "decision_id": "dec-001",
        "request_id": "req-001",
        "incident_id": "inc-001",
        "action_id": "act-001",
        "decision": "approved",
        "approver": {
            "telegram_user_id": "123456789",
            "username": "manager",
        },
        "decided_at": "2026-11-06T13:03:00Z",
        "approval_token": "a" * 64,
    }


def test_valid_approval_decision(valid_decision):
    decision = ApprovalDecision.model_validate(valid_decision)

    assert decision.decision == "approved"
    assert decision.approver.telegram_user_id == "123456789"


def test_valid_rejection_decision(valid_decision):
    valid_decision["decision"] = "rejected"

    decision = ApprovalDecision.model_validate(valid_decision)

    assert decision.decision == "rejected"


def test_invalid_decision_type(valid_decision):
    valid_decision["decision"] = "pending"

    with pytest.raises(ValidationError):
        ApprovalDecision.model_validate(valid_decision)


def test_invalid_telegram_user_id(valid_decision):
    valid_decision["approver"]["telegram_user_id"] = "manager123"

    with pytest.raises(ValidationError):
        ApprovalDecision.model_validate(valid_decision)


def test_empty_approval_token(valid_decision):
    valid_decision["approval_token"] = ""

    with pytest.raises(ValidationError):
        ApprovalDecision.model_validate(valid_decision)


def test_short_approval_token(valid_decision):
    valid_decision["approval_token"] = "short"

    with pytest.raises(ValidationError):
        ApprovalDecision.model_validate(valid_decision)


def test_timezone_required(valid_decision):
    valid_decision["decided_at"] = "2026-11-06T13:03:00"

    with pytest.raises(ValidationError):
        ApprovalDecision.model_validate(valid_decision)


def test_username_is_optional(valid_decision):
    valid_decision["approver"].pop("username")

    decision = ApprovalDecision.model_validate(valid_decision)

    assert decision.approver.username is None


def test_extra_field_rejected(valid_decision):
    valid_decision["unexpected_field"] = "not-allowed"

    with pytest.raises(ValidationError):
        ApprovalDecision.model_validate(valid_decision)
