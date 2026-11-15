
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EvidenceSource = Literal[
    "prometheus",
    "loki",
    "kubernetes",
]


class EvidenceValidationBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class EvidenceValidationResult(EvidenceValidationBase):
    is_sufficient: bool

    available_sources: list[EvidenceSource] = Field(default_factory=list)

    unavailable_sources: list[EvidenceSource] = Field(default_factory=list)

    matched_sources: list[EvidenceSource] = Field(default_factory=list)

    warnings: list[str] = Field(default_factory=list)

    validated_at: datetime
    
