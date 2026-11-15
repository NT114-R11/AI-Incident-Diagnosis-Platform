
import asyncio
from app.database.connection import SessionLocal
from app.models.incident import Incident
from app.services.diagnosis_service import DiagnosisService


INCIDENT_FINGERPRINT = "diagnosis-loki-error-test-001"


async def main():
    db = SessionLocal()

    try:
        incident = (
            db.query(Incident)
            .filter(Incident.fingerprint == INCIDENT_FINGERPRINT)
            .order_by(Incident.last_seen_at.desc())
            .first()
        )

        if incident is None:
            print("INCIDENT_NOT_FOUND")
            return

        print("INCIDENT:")
        print({
            "id": str(incident.id),
            "fingerprint": incident.fingerprint,
            "alert_name": incident.alert_name,
            "namespace": incident.namespace,
            "pod": incident.pod,
            "severity": incident.severity,
            "status": incident.status,
        })

        print("\nRUNNING DIAGNOSIS...")

        diagnosis = await DiagnosisService().diagnose(incident)

        print("\nDIAGNOSIS RESULT:")
        print(diagnosis.model_dump_json(indent=2))

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
