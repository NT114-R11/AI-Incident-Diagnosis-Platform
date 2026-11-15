from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IncidentContextBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class IncidentContextIncident(IncidentContextBase):
    id: UUID
    fingerprint: str
    alert_name: str
    namespace: str | None = None
    pod: str | None = None
    severity: str | None = None
    status: str
    summary: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime


class EvidenceCollectionStatus(IncidentContextBase):
    prometheus: Literal["success", "failed"]
    loki: Literal["success", "failed"]
    kubernetes: Literal["success", "failed"]


class IncidentContext(IncidentContextBase):
    incident: IncidentContextIncident
    evidence: dict[str, Any] = Field(default_factory=dict)
    collection_status: EvidenceCollectionStatus
    collected_at: datetime
