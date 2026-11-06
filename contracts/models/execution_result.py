
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .base import ContractBase


class ExecutionTarget(ContractBase):
    namespace: str = Field(min_length=1, max_length=63)

    resource_type: Literal[
        "deployment",
        "statefulset",
        "daemonset",
        "pod",
    ]

    resource_name: str = Field(min_length=1, max_length=253)


class ExecutionOutput(ContractBase):
    message: str = Field(min_length=1, max_length=2000)


class AuditInfo(ContractBase):
    executor_id: str = Field(min_length=1, max_length=100)


class ExecutionResult(ContractBase):
    schema_version: Literal["1.0"] = "1.0"

    execution_id: str = Field(min_length=1, max_length=100)
    incident_id: str = Field(min_length=1, max_length=100)
    action_id: str = Field(min_length=1, max_length=100)

    status: Literal[
        "succeeded",
        "failed",
        "rejected",
        "timeout",
        "already_executed",
    ]

    target: ExecutionTarget

    started_at: datetime
    completed_at: datetime

    result: ExecutionOutput
    audit: AuditInfo

    @model_validator(mode="after")
    def validate_execution(self):
        for field_name in ("started_at", "completed_at"):
            value = getattr(self, field_name)

            if value.tzinfo is None:
                raise ValueError(
                    f"{field_name} must include timezone"
                )

        if self.completed_at < self.started_at:
            raise ValueError(
                "completed_at cannot be before started_at"
            )

        return self
