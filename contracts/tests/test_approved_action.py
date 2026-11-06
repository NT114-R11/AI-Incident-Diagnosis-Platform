import pytest
from pydantic import ValidationError

from models import ApprovedAction


@pytest.fixture
def valid_action():
    return {
        "schema_version": "1.0",
        "execution_id": "exec-001",
        "incident_id": "inc-001",
        "request_id": "req-001",
        "action_id": "act-001",
        "approval": {
            "decision_id": "dec-001",
            "approver": {
                "telegram_user_id": "123456789",
                "username": "manager",
            },
            "approved_at": "2026-11-06T13:03:00Z",
            "approval_token": "a" * 64,
        },
        "action": {
            "action_id": "act-001",
            "action_type": "restart_deployment",
            "parameters": {
                "namespace": "voting-app",
                "deployment": "vote",
            },
            "reason": "Restart unhealthy deployment.",
        },
        "execution_policy": {
            "timeout_seconds": 60,
            "max_attempts": 1,
        },
        "issued_at": "2026-11-06T13:03:05Z",
        "expires_at": "2026-11-06T13:05:00Z",
    }


def test_valid_approved_action(valid_action):
    action = ApprovedAction.model_validate(valid_action)
    assert action.execution_id == "exec-001"


def test_invalid_action_type(valid_action):
    valid_action["action"]["action_type"] = "run_shell"
    with pytest.raises(ValidationError):
        ApprovedAction.model_validate(valid_action)


def test_invalid_timeout(valid_action):
    valid_action["execution_policy"]["timeout_seconds"] = 500
    with pytest.raises(ValidationError):
        ApprovedAction.model_validate(valid_action)


def test_retry_not_allowed(valid_action):
    valid_action["execution_policy"]["max_attempts"] = 3
    with pytest.raises(ValidationError):
        ApprovedAction.model_validate(valid_action)


def test_expiration_before_issue(valid_action):
    valid_action["expires_at"] = "2026-11-06T13:00:00Z"
    with pytest.raises(ValidationError):
        ApprovedAction.model_validate(valid_action)


def test_action_cannot_be_issued_before_approval(valid_action):
    valid_action["approval"]["approved_at"] = "2026-11-06T13:04:00Z"
    with pytest.raises(ValidationError):
        ApprovedAction.model_validate(valid_action)


def test_timezone_required(valid_action):
    valid_action["issued_at"] = "2026-11-06T13:03:05"
    with pytest.raises(ValidationError):
        ApprovedAction.model_validate(valid_action)


def test_extra_field_rejected(valid_action):
    valid_action["unexpected_field"] = "not-allowed"
    with pytest.raises(ValidationError):
        ApprovedAction.model_validate(valid_action)
