
from sqlalchemy.orm import Session

from app.schemas.alertmanager import AlertmanagerWebhook
from app.services.incident_service import IncidentService


def process_alertmanager_webhook(payload: AlertmanagerWebhook,db: Session) -> dict:
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

        processed_alerts.append({
            "fingerprint": alert.fingerprint,
            "alertname": alert.labels.get("alertname"),
            "namespace": alert.labels.get("namespace"),
            "pod": alert.labels.get("pod"),
            "status": alert.status,
            "action": action,
            "incident_id": str(incident.id) if incident else None,
        })

    return {
        "receiver": payload.receiver,
        "group_status": payload.status,
        "total_alerts": len(payload.alerts),
        **counts,
        "processed_alerts": processed_alerts,
    }
