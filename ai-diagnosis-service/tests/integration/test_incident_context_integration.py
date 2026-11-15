
import pytest

from app.database.session import SessionLocal
from app.models.incident import Incident
from app.services.incident_context_service import IncidentContextService


@pytest.mark.asyncio
async def test_collect_incident_context_from_real_sources():
    db = SessionLocal()

    try:
        incident = (
            db.query(Incident)
            .filter(Incident.status.in_(["open", "acknowledged"]))
            .order_by(Incident.created_at.desc())
            .first()
        )

        assert incident is not None, "No active incident found in database"

        service = IncidentContextService()
        context = await service.collect(incident)

        print("\nIncident:", context.incident.model_dump())
        print("\nCollection status:", context.collection_status.model_dump())

        for source, evidence in context.evidence.items():
            print(f"\n{source} evidence:")
            print(evidence)

        assert context.incident.id == incident.id

        assert set(context.collection_status.model_dump().keys()) == {
            "prometheus",
            "loki",
            "kubernetes",
        }

        assert any(
            status == "success"
            for status in context.collection_status.model_dump().values()
        )

    finally:
        db.close()
