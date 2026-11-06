from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .base import ContractBase

class IncidentInfo(ContractBase):
    title: str = Field(min_length=1, max_length=200)
    severity: Literal["critical", "high", "medium", "low"]
    namespace: str = Field(min_length=1, max_length=63)
    resource_type: Literal[
        "deployment",
        "statefulset",
        "daemonset",
        "pod",
    ]
    resource_name: str = Field(min_length=1, max_length=253)
    summary: str = Field(min_length=1, max_length=2000)


class DiagnosisInfo(ContractBase):
    probable_cause: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(min_length=1, max_length=50)


class RestartDeploymentParameters(ContractBase):
    namespace: str = Field(min_length=1, max_length=63)
    deployment: str = Field(min_length=1, max_length=253)


class ProposedAction(ContractBase):
    action_id: str = Field(min_length=1, max_length=100)
    action_type: Literal["restart_deployment"]
    parameters: RestartDeploymentParameters
    reason: str = Field(min_length=1, max_length=1000)


class RemediationRequest(ContractBase):
    schema_version: Literal["1.0"] = "1.0"

    request_id: str = Field(min_length=1, max_length=100)
    incident_id: str = Field(min_length=1, max_length=100)

    created_at: datetime
    expires_at: datetime

    incident: IncidentInfo
    diagnosis: DiagnosisInfo
    proposed_action: ProposedAction

    @model_validator(mode="after")
    def validate_request(self):
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must include timezone")

        if self.expires_at.tzinfo is None:
            raise ValueError("expires_at must include timezone")

        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")

        if (
            self.proposed_action.parameters.namespace
            != self.incident.namespace
        ):
            raise ValueError(
                "Action namespace must match incident namespace"
            )

        return self
