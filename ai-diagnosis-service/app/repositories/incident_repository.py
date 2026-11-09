
import uuid
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.incident import Incident


class IncidentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, incident_id: uuid.UUID) -> Incident | None:
        statement = select(Incident).where(Incident.id == incident_id)
        return self.db.scalar(statement)

    def get_active_by_fingerprint(self,fingerprint: str) -> Incident | None:
        statement = (
            select(Incident)
            .where(
                Incident.fingerprint == fingerprint,
                Incident.status.in_(["open", "acknowledged"]),
            )
            .order_by(Incident.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(statement)

    def create(self, incident: Incident) -> Incident:
        self.db.add(incident)
        self.db.flush()
        return incident

    def update_last_seen(self,incident: Incident,last_seen_at: datetime) -> Incident:
        incident.last_seen_at = last_seen_at
        self.db.flush()
        return incident

    def resolve(self,incident: Incident,resolved_at: datetime) -> Incident:
        incident.status = "resolved"
        incident.resolved_at = resolved_at
        self.db.flush()
        return incident

    def list_incidents(self,
                        status: str | None = None,
                        severity: str | None = None,
                        namespace: str | None = None,
                        limit: int = 20,
                        offset: int = 0) -> tuple[list[Incident], int]:
        filters = []

        if status is not None:
            filters.append(Incident.status == status)

        if severity is not None:
            filters.append(Incident.severity == severity)

        if namespace is not None:
            filters.append(Incident.namespace == namespace)

        count_statement = (
            select(func.count())
            .select_from(Incident)
            .where(*filters)
        )

        data_statement = (
            select(Incident)
            .where(*filters)
            .order_by(Incident.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        total = self.db.scalar(count_statement) or 0
        incidents = list(self.db.scalars(data_statement).all())

        return incidents, total


    def get_summary(self) -> dict[str, int]:
        statement = (
            select(Incident.status, func.count(Incident.id))
            .group_by(Incident.status)
        )

        results = self.db.execute(statement).all()

        summary = {
            "open": 0,
            "acknowledged": 0,
            "resolved": 0,
        }

        total = 0

        for status, count in results:
            total += count

            if status in summary:
                summary[status] = count

        return {
            "total": total,
            **summary,
        }

