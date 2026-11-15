
from typing import Literal
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


DiagnosisStatus = Literal[
    "diagnosed",
    "no_issue_detected",
    "insufficient_evidence",
]

DiagnosisCategory = Literal[
    "pod_crash_loop",
    "oom_killed",
    "high_cpu",
    "high_memory",
    "application_error",
    "application_exception",
    "application_warning",
    "dependency_failure",
    "pod_not_ready",
]


Severity = Literal[
    "critical",
    "high",
    "medium",
    "low",
]


class DiagnosisBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class DiagnosisFinding(DiagnosisBase):
    rule_id: str
    category: DiagnosisCategory
    title: str
    description: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(
        default_factory=list,
        max_length=50,
    )


class DiagnosisResult(DiagnosisBase):
    incident_id: UUID
    status: DiagnosisStatus
    analyzed_at: datetime

    probable_cause: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Severity | None = None

    summary: str
    findings: list[DiagnosisFinding] = Field(
        default_factory=list,
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        max_length=50,
    )
