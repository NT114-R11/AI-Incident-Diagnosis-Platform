import uuid
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.repositories.incident_repository import IncidentRepository


class IncidentQueryService:
    ALLOWED_STATUSES = {
        "open",
        "acknowledged",
        "resolved",
    }

    def __init__(self, db: Session):
        self.repository = IncidentRepository(db)

    def list_incidents(
        self,
        status: str | None = None,
        severity: str | None = None,
        namespace: str | None = None,
        limit: int = 20,
        offset: int = 0) -> tuple[list[Incident], int]:
        if status is not None and status not in self.ALLOWED_STATUSES:
            raise ValueError(f"Unsupported incident status: {status}")

        return self.repository.list_incidents(
            status=status,
            severity=severity,
            namespace=namespace,
            limit=limit,
            offset=offset,
        )

    def get_incident(self, incident_id: uuid.UUID) -> Incident | None:
        return self.repository.get_by_id(incident_id)

    def get_summary(self) -> dict[str, int]:
        return self.repository.get_summary()
