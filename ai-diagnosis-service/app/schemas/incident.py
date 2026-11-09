import uuid
from datetime import datetime
from pydantic import ConfigDict
from app.schemas.base import WebhookBase


class IncidentResponse(WebhookBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fingerprint: str
    alert_name: str
    namespace: str | None
    pod: str | None
    severity: str | None
    status: str
    summary: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class IncidentListResponse(WebhookBase):
    total: int
    limit: int
    offset: int
    items: list[IncidentResponse]


class IncidentSummaryResponse(WebhookBase):
    total: int
    open: int
    acknowledged: int
    resolved: int
