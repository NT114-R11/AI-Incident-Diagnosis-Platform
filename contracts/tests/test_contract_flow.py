
from models import (
    RemediationRequest,
    ApprovalDecision,
    ApprovedAction,
    ExecutionResult,
)


def test_complete_remediation_contract_flow():
    # 1. AI Diagnosis creates a remediation request
    request = RemediationRequest.model_validate({
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
            "summary": "Deployment has unavailable replicas.",
        },
        "diagnosis": {
            "probable_cause": "Pods are failing readiness checks.",
            "confidence": 0.91,
            "evidence_refs": ["prometheus://evidence/123"],
        },
        "proposed_action": {
            "action_id": "act-001",
            "action_type": "restart_deployment",
            "parameters": {
                "namespace": "voting-app",
                "deployment": "vote",
            },
            "reason": "Restart unhealthy deployment.",
        },
    })

    # 2. Manager approves the proposed action
    decision = ApprovalDecision.model_validate({
        "decision_id": "dec-001",
        "request_id": request.request_id,
        "incident_id": request.incident_id,
        "action_id": request.proposed_action.action_id,
        "decision": "approved",
        "approver": {
            "telegram_user_id": "123456789",
            "username": "manager",
        },
        "decided_at": "2026-11-06T13:03:00Z",
        "approval_token": "a" * 64,
    })

    assert decision.decision == "approved"
    assert decision.request_id == request.request_id
    assert decision.incident_id == request.incident_id
    assert decision.action_id == request.proposed_action.action_id

    # 3. AI Diagnosis creates an approved action
    approved_action = ApprovedAction.model_validate({
        "execution_id": "exec-001",
        "incident_id": decision.incident_id,
        "request_id": decision.request_id,
        "action_id": decision.action_id,
        "approval": {
            "decision_id": decision.decision_id,
            "approver": decision.approver.model_dump(),
            "approved_at": decision.decided_at,
            "approval_token": decision.approval_token,
        },
        "action": request.proposed_action.model_dump(),
        "execution_policy": {
            "timeout_seconds": 60,
            "max_attempts": 1,
        },
        "issued_at": "2026-11-06T13:03:05Z",
        "expires_at": "2026-11-06T13:05:00Z",
    })

    assert approved_action.request_id == request.request_id
    assert approved_action.incident_id == request.incident_id
    assert approved_action.action_id == request.proposed_action.action_id
    assert approved_action.approval.decision_id == decision.decision_id
    assert approved_action.approval.approver.telegram_user_id == (
        decision.approver.telegram_user_id
    )

    # 4. Executor returns execution result
    execution_result = ExecutionResult.model_validate({
        "execution_id": approved_action.execution_id,
        "incident_id": approved_action.incident_id,
        "action_id": approved_action.action_id,
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
    })

    assert execution_result.execution_id == approved_action.execution_id
    assert execution_result.incident_id == approved_action.incident_id
    assert execution_result.action_id == approved_action.action_id
    assert execution_result.status == "succeeded"

    # 5. Verify execution target matches the approved action
    expected_parameters = approved_action.action.parameters
    actual_target = execution_result.target

    assert actual_target.namespace == expected_parameters.namespace
    assert actual_target.resource_type == "deployment"
    assert actual_target.resource_name == expected_parameters.deployment
