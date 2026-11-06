
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from .base import ContractBase


class ApproverInfo(ContractBase):
    telegram_user_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[0-9]+$",
    )
    username: str | None = Field(
        default=None,
        max_length=64,
    )


class ApprovalDecision(ContractBase):
    schema_version: Literal["1.0"] = "1.0"

    decision_id: str = Field(min_length=1, max_length=100)
    request_id: str = Field(min_length=1, max_length=100)
    incident_id: str = Field(min_length=1, max_length=100)
    action_id: str = Field(min_length=1, max_length=100)

    decision: Literal["approved", "rejected"]

    approver: ApproverInfo

    decided_at: datetime

    approval_token: str = Field(
        min_length=32,
        max_length=512,
    )

    @field_validator("decided_at")
    @classmethod
    def validate_decided_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("decided_at must include timezone")
        return value
