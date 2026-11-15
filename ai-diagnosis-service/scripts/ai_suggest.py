
import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4
from app.notifications.telegram_notifier import TelegramNotifier
from app.ai.diagnosis_service import AIDiagnosisService
from app.schemas.diagnosis import DiagnosisResult, DiagnosisFinding
from app.schemas.diagnosis_analysis import DiagnosisAnalysis
from app.schemas.incident_context import (
    IncidentContext,
    IncidentContextIncident,
    EvidenceCollectionStatus,
)


async def main():
    now = datetime.now(timezone.utc)
    incident_id = uuid4()

    incident = IncidentContextIncident(
        id=incident_id,
        fingerprint="gemini-live-test-oom",
        alert_name="PodCrashLooping",
        namespace="voting-app",
        pod="vote-7d9f8b6c5-x2k4p",
        severity="critical",
        status="open",
        summary="Container repeatedly restarted due to suspected memory exhaustion",
        first_seen_at=now,
        last_seen_at=now,
    )

    context = IncidentContext(
        incident=incident,
        evidence={
            "kubernetes": {
                "pod_status": "CrashLoopBackOff",
                "container_restart_count": 12,
                "last_termination_reason": "OOMKilled",
            },
            "prometheus": {
                "container_memory_working_set_bytes": 503316480,
                "container_memory_limit_bytes": 536870912,
            },
            "loki": {
                "logs": [
                    "Container terminated: OOMKilled",
                    "Container restarting",
                ],
            },
        },
        collection_status=EvidenceCollectionStatus(
            prometheus="success",
            loki="success",
            kubernetes="success",
        ),
        collected_at=now,
    )

    diagnosis = DiagnosisResult(
        incident_id=incident_id,
        status="diagnosed",
        analyzed_at=now,
        probable_cause="Container memory limit exceeded",
        confidence=0.90,
        severity="critical",
        summary="Container repeatedly terminated due to memory exhaustion.",
        findings=[
            DiagnosisFinding(
                rule_id="K8S-OOM-001",
                category="oom_killed",
                title="Container OOMKilled",
                description="Container was terminated after exceeding its memory limit.",
                severity="critical",
                confidence=0.95,
                evidence_refs=[
                    "kubernetes.last_termination_reason",
                    "prometheus.container_memory_working_set_bytes",
                    "prometheus.container_memory_limit_bytes",
                ],
            )
        ],
        evidence_refs=[
            "kubernetes.pod_status",
            "kubernetes.container_restart_count",
            "kubernetes.last_termination_reason",
            "prometheus.container_memory_working_set_bytes",
            "prometheus.container_memory_limit_bytes",
            "loki.logs",
        ],
    )

    analysis = DiagnosisAnalysis(
        diagnosis=diagnosis,
        context=context,
    )

    ai_service = AIDiagnosisService()

    try:
        # Run Gemini diagnosis
        result = await ai_service.diagnose(analysis)

        # Attach Gemini result to DiagnosisAnalysis
        analysis.ai_diagnosis = result

        print(json.dumps(
            analysis.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        ))

        # Send Telegram notification
        notifier = TelegramNotifier()
        await notifier.send_diagnosis(analysis)

        print("Telegram notification sent successfully.")

    finally:
        await ai_service.model_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
