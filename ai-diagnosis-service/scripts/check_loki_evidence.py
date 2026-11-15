
import asyncio
from pprint import pprint

from app.database.connection import SessionLocal
from app.models.incident import Incident
from app.collectors.loki.collector import LokiCollector


INCIDENT_FINGERPRINT = "diagnosis-loki-error-test-001"


async def main():
    db = SessionLocal()

    try:
        incident = (
            db.query(Incident)
            .filter(Incident.fingerprint == INCIDENT_FINGERPRINT)
            .first()
        )

        if incident is None:
            print("INCIDENT_NOT_FOUND")
            return

        print("INCIDENT:")
        print({
            "id": str(incident.id),
            "namespace": incident.namespace,
            "pod": incident.pod,
            "first_seen_at": incident.first_seen_at,
            "last_seen_at": incident.last_seen_at,
        })

        print("\nCOLLECTING LOKI EVIDENCE...")

        result = await LokiCollector().collect()

        print("\nCOLLECTOR RESULT:")
        pprint(result, sort_dicts=False)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
