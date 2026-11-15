
import logging

from sqlalchemy.orm import Session

from app.ai.diagnosis_service import AIDiagnosisService
from app.notifications.telegram_notifier import TelegramNotifier
from app.schemas.alertmanager import AlertmanagerWebhook
from app.services.diagnosis_service import DiagnosisService
from app.services.incident_service import IncidentService

logger = logging.getLogger(__name__)


async def process_alertmanager_webhook(payload: AlertmanagerWebhook, db: Session) -> dict:
    incident_service = IncidentService(db)

    counts = {
        "created_count": 0,
        "updated_count": 0,
        "resolved_count": 0,
        "ignored_count": 0,
    }

    processed_alerts = []

    for alert in payload.alerts:
        incident, action = incident_service.process_alert(alert)

        counts[f"{action}_count"] += 1

        processed_alert = {
            "fingerprint": alert.fingerprint,
            "alertname": alert.labels.get("alertname"),
            "namespace": alert.labels.get("namespace"),
            "pod": alert.labels.get("pod"),
            "status": alert.status,
            "action": action,
            "incident_id": str(incident.id) if incident else None,
        }

        if action == "created" and incident is not None:
            try:
                diagnosis_service = DiagnosisService(
                    ai_diagnosis_service=AIDiagnosisService())

                analysis = await diagnosis_service.diagnose_with_context(incident)

                processed_alert["diagnosis"] = analysis.model_dump(mode="json")

                try:
                    notifier = TelegramNotifier()
                    await notifier.send_diagnosis(analysis)
                    processed_alert["notification"] = "sent"

                except Exception:
                    logger.exception(
                        "Telegram notification failed for incident %s",
                        incident.id,
                    )
                    processed_alert["notification_error"] = (
                        "Telegram notification failed"
                    )

            except Exception:
                logger.exception(
                    "Diagnosis failed for incident %s",
                    incident.id,
                )
                processed_alert["diagnosis_error"] = (
                    "Diagnosis pipeline failed"
                )

        processed_alerts.append(processed_alert)

    return {
        "receiver": payload.receiver,
        "group_status": payload.status,
        "total_alerts": len(payload.alerts),
        **counts,
        "processed_alerts": processed_alerts,
    }
