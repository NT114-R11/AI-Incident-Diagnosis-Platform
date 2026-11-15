from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class AIDiagnosis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["success", "unavailable"]

    probable_cause: str | None = None

    explanation: str | None = None

    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    supporting_evidence: list[str] = Field(
        default_factory=list,
    )

    investigation_steps: list[str] = Field(
        default_factory=list,
    )