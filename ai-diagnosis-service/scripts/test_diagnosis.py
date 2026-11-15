
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from app.database.connection import SessionLocal
from app.models.incident import Incident
from app.services.diagnosis_service import DiagnosisService
from app.schemas.incident_context import (
    IncidentContext,
    IncidentContextIncident,
    EvidenceCollectionStatus,
)


INCIDENT_FINGERPRINT = "diagnosis-memory-test-001"

POD_NAME = "diagnosis-memory-test"
CONTAINER_NAME = "memory-stress"

# Historical memory usage: 564.85546875 MiB
MEMORY_USAGE_BYTES = 564.85546875 * 1024 * 1024

# Actual Prometheus sample timestamp: 2026-11-14T03:39:12Z
SAMPLE_TIMESTAMP = 1794627552


async def main():
    db = SessionLocal()

    try:
        incident = (
            db.query(Incident)
            .filter(
                Incident.fingerprint == INCIDENT_FINGERPRINT
            )
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

        # Use the actual historical Prometheus sample time.
        sample_datetime = datetime.fromtimestamp(
            SAMPLE_TIMESTAMP,
            tz=timezone.utc,
        )

        # Build test context using the historical evidence timestamp.
        context = IncidentContext(
            incident=IncidentContextIncident(
                id=incident.id,
                fingerprint=incident.fingerprint,
                alert_name=incident.alert_name,
                namespace="voting-app",
                pod=POD_NAME,
                severity=incident.severity,
                status=incident.status,
                summary=incident.summary,
                first_seen_at=sample_datetime,
                last_seen_at=sample_datetime,
            ),
            evidence={
                "prometheus": {
                    "source": "prometheus",
                    "namespace": "voting-app",
                    "collected_at": sample_datetime.isoformat(),
                    "metrics": {
                        "memory": {
                            "result": [
                                {
                                    "metric": {
                                        "namespace": "voting-app",
                                        "pod": POD_NAME,
                                        "container": CONTAINER_NAME,
                                    },
                                    "value": [
                                        str(SAMPLE_TIMESTAMP),
                                        str(MEMORY_USAGE_BYTES),
                                    ],
                                }
                            ]
                        }
                    },
                }
            },
            collection_status=EvidenceCollectionStatus(
                prometheus="success",
                loki="failed",
                kubernetes="failed",
            ),
            collected_at=sample_datetime,
        )

        # Mock only evidence collection.
        context_service = AsyncMock()
        context_service.collect.return_value = context

        diagnosis_service = DiagnosisService(
            context_service=context_service,
        )

        print("\nRUNNING DIAGNOSIS...")

        diagnosis = await diagnosis_service.diagnose(incident)

        print("\nDIAGNOSIS RESULT:")
        print(diagnosis.model_dump_json(indent=2))

        # Explicit verification
        print("\nTEST ASSERTIONS:")

        assert diagnosis.status == "diagnosed", (
            f"Expected diagnosed, got {diagnosis.status}"
        )

        high_memory_findings = [
            finding
            for finding in diagnosis.findings
            if finding.rule_id == "HIGH_MEMORY"
        ]

        assert high_memory_findings, (
            "HIGH_MEMORY finding was not detected"
        )

        finding = high_memory_findings[0]

        assert finding.severity == "high"
        assert finding.confidence == 0.90

        print("PASS: DiagnosisService diagnosed the incident")
        print("PASS: HIGH_MEMORY rule detected")
        print("PASS: Severity = high")
        print("PASS: Confidence = 0.90")

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
