
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .base import ContractBase
from .approval_decision import ApproverInfo
from .remediation_request import ProposedAction


class ApprovalMetadata(ContractBase):
    decision_id: str
    approver: ApproverInfo
    approved_at: datetime
    approval_token: str = Field(min_length=32, max_length=512)

    @model_validator(mode="after")
    def validate_approved_at(self):
        if self.approved_at.tzinfo is None:
            raise ValueError("approved_at must include timezone")
        return self


class ExecutionPolicy(ContractBase):
    timeout_seconds: int = Field(ge=1, le=300)
    max_attempts: Literal[1] = 1


class ApprovedAction(ContractBase):
    schema_version: Literal["1.0"] = "1.0"

    execution_id: str = Field(min_length=1, max_length=100)
    incident_id: str = Field(min_length=1, max_length=100)
    request_id: str = Field(min_length=1, max_length=100)
    action_id: str = Field(min_length=1, max_length=100)

    approval: ApprovalMetadata
    action: ProposedAction
    execution_policy: ExecutionPolicy

    issued_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def validate_action(self):
        for field_name in ("issued_at", "expires_at"):
            value = getattr(self, field_name)

            if value.tzinfo is None:
                raise ValueError(
                    f"{field_name} must include timezone"
                )

        if self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be after issued_at")

        if self.approval.approved_at > self.issued_at:
            raise ValueError("Action cannot be issued before approval")

        if self.action.action_id != self.action_id:
            raise ValueError("Action ID mismatch")

        return self
