from typing import Literal
from pydantic import AwareDatetime, Field, field_validator
from app.schemas.base import WebhookBase


class Alert(WebhookBase):
    status: Literal["firing", "resolved"]

    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)

    startsAt: AwareDatetime
    endsAt: AwareDatetime | None = None

    generatorURL: str | None = None
    fingerprint: str


    @field_validator("endsAt", mode="before")
    @classmethod
    def normalize_ends_at(cls, value):
        if isinstance(value, str) and value.startswith("0001-01-01"):
            return None
        return value



class AlertmanagerWebhook(WebhookBase):
    version: str
    groupKey: str
    status: Literal["firing", "resolved"]
    receiver: str

    groupLabels: dict[str, str] = Field(default_factory=dict)
    commonLabels: dict[str, str] = Field(default_factory=dict)
    commonAnnotations: dict[str, str] = Field(default_factory=dict)

    externalURL: str

    alerts: list[Alert] = Field(default_factory=list)
    truncatedAlerts: int = 0
