
import asyncio
from pprint import pprint

from app.database.connection import SessionLocal
from app.models.incident import Incident
from app.services.incident_context_service import IncidentContextService


async def main():
    db = SessionLocal()

    try:
        incident = (
            db.query(Incident)
            .filter(
                Incident.fingerprint == "diagnosis-loki-error-test-001"
            )
            .first()
        )

        if incident is None:
            print("INCIDENT_NOT_FOUND")
            return

        context = await IncidentContextService().collect(incident)

        print("COLLECTION STATUS:")
        pprint(context.collection_status.model_dump())

        for source, evidence in context.evidence.items():
            print(f"\n--- {source.upper()} ---")

            if isinstance(evidence, dict) and "error" in evidence:
                print("ERROR:", repr(evidence["error"]))
            else:
                print("Collection successful")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
