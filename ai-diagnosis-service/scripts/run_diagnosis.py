import asyncio
import json
from uuid import UUID

from app.database.connection import SessionLocal
from app.models.incident import Incident
from app.services.diagnosis_service import DiagnosisService
from app.ai.diagnosis_service import AIDiagnosisService


INCIDENT_ID = UUID("26c7ab46-ddfd-4fcb-a2b7-de791a8c3e1a")


async def main():
    db = SessionLocal()

    try:
        incident = db.get(Incident, INCIDENT_ID)

        if incident is None:
            print("Incident not found.")
            return

        print(f"Diagnosing incident: {incident.id}")
        print(f"Alert: {incident.alert_name}")
        print(f"Namespace: {incident.namespace}")
        print(f"Pod: {incident.pod}")
        print("-" * 60)

        diagnosis_service = DiagnosisService(ai_diagnosis_service=AIDiagnosisService())
        result = await diagnosis_service.diagnose(incident)

        print(
            json.dumps(
                result.model_dump(mode="json"),
                indent=2,
                ensure_ascii=False,
            )
        )

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())