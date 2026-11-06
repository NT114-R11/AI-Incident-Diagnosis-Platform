
import pytest
from pydantic import ValidationError

from models import ExecutionResult


@pytest.fixture
def valid_result():
    return {
        "schema_version": "1.0",
        "execution_id": "exec-001",
        "incident_id": "inc-001",
        "action_id": "act-001",
        "status": "succeeded",
        "target": {
            "namespace": "voting-app",
            "resource_type": "deployment",
            "resource_name": "vote",
        },
        "started_at": "2026-11-06T13:03:10Z",
        "completed_at": "2026-11-06T13:03:18Z",
        "result": {
            "message": "Deployment restart command accepted.",
        },
        "audit": {
            "executor_id": "remediation-executor",
        },
    }


def test_valid_execution_result(valid_result):
    result = ExecutionResult.model_validate(valid_result)
    assert result.status == "succeeded"


@pytest.mark.parametrize(
    "status",
    ["failed", "rejected", "timeout", "already_executed"],
)
def test_other_valid_statuses(valid_result, status):
    valid_result["status"] = status

    result = ExecutionResult.model_validate(valid_result)

    assert result.status == status


def test_invalid_status(valid_result):
    valid_result["status"] = "pending"

    with pytest.raises(ValidationError):
        ExecutionResult.model_validate(valid_result)


def test_invalid_resource_type(valid_result):
    valid_result["target"]["resource_type"] = "service"

    with pytest.raises(ValidationError):
        ExecutionResult.model_validate(valid_result)


def test_completed_before_started(valid_result):
    valid_result["completed_at"] = "2026-11-06T13:00:00Z"

    with pytest.raises(ValidationError):
        ExecutionResult.model_validate(valid_result)


def test_timezone_required(valid_result):
    valid_result["started_at"] = "2026-11-06T13:03:10"

    with pytest.raises(ValidationError):
        ExecutionResult.model_validate(valid_result)


def test_extra_field_rejected(valid_result):
    valid_result["unexpected_field"] = "not-allowed"

    with pytest.raises(ValidationError):
        ExecutionResult.model_validate(valid_result)


def test_execution_result_serialization(valid_result):
    result = ExecutionResult.model_validate(valid_result)

    serialized = result.model_dump(mode="json")

    assert serialized["execution_id"] == "exec-001"
    assert serialized["status"] == "succeeded"
