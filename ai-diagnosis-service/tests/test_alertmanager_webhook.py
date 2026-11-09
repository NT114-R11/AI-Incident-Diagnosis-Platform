
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.incident import Incident
from app.database.connection import SessionLocal


def make_alert(status="firing", fingerprint="abc123"):
    return {
        "status": status,
        "labels": {
            "alertname": "PodCrashLooping",
            "namespace": "voting-app",
            "pod": "vote-7d9f8b6c5-x2k4p",
            "severity": "critical",
        },
        "annotations": {
            "summary": "Pod is restarting frequently",
            "description": "Pod has restarted multiple times.",
        },
        "startsAt": "2026-11-08T01:00:00Z",
        "endsAt": (
            "0001-01-01T00:00:00Z"
            if status == "firing"
            else "2026-11-08T01:05:00Z"
        ),
        "generatorURL": "http://prometheus:9090/graph",
        "fingerprint": fingerprint,
    }


def make_payload(alerts):
    return {
        "version": "4",
        "groupKey": "{}:{alertname=\"PodCrashLooping\"}",
        "status": "firing",
        "receiver": "ai-diagnosis",
        "groupLabels": {
            "alertname": "PodCrashLooping",
        },
        "commonLabels": {},
        "commonAnnotations": {},
        "externalURL": "http://alertmanager:9093",
        "alerts": alerts,
        "truncatedAlerts": 0,
    }


def get_incident(fingerprint):
    with SessionLocal() as db:
        statement = select(Incident).where(
            Incident.fingerprint == fingerprint
        )
        return db.scalar(statement)


def test_receive_firing_alert():
    fingerprint = f"webhook-test-{uuid.uuid4()}"

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/alertmanager",
            json=make_payload([make_alert(fingerprint=fingerprint)]),
        )

    assert response.status_code == 200

    data = response.json()

    assert data["total_alerts"] == 1
    assert data["created_count"] == 1
    assert data["updated_count"] == 0
    assert data["resolved_count"] == 0
    assert data["ignored_count"] == 0

    processed = data["processed_alerts"][0]
    assert processed["fingerprint"] == fingerprint
    assert processed["action"] == "created"
    assert processed["incident_id"] is not None

    incident = get_incident(fingerprint)
    assert incident is not None
    assert incident.status == "open"


def test_receive_resolved_alert_without_active_incident():
    fingerprint = f"webhook-test-{uuid.uuid4()}"

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/alertmanager",
            json=make_payload([
                make_alert("resolved", fingerprint)
            ]),
        )

    assert response.status_code == 200

    data = response.json()

    assert data["total_alerts"] == 1
    assert data["resolved_count"] == 0
    assert data["ignored_count"] == 1
    assert data["processed_alerts"][0]["action"] == "ignored"
    assert data["processed_alerts"][0]["incident_id"] is None

    assert get_incident(fingerprint) is None


def test_receive_duplicate_firing_alert():
    fingerprint = f"webhook-test-{uuid.uuid4()}"
    payload = make_payload([make_alert(fingerprint=fingerprint)])

    with TestClient(app) as client:
        first_response = client.post(
            "/webhooks/alertmanager",
            json=payload,
        )
        second_response = client.post(
            "/webhooks/alertmanager",
            json=payload,
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_data = first_response.json()
    second_data = second_response.json()

    assert first_data["created_count"] == 1
    assert second_data["updated_count"] == 1

    assert (
        first_data["processed_alerts"][0]["incident_id"]
        == second_data["processed_alerts"][0]["incident_id"]
    )


def test_receive_multiple_alerts():
    fingerprints = [
        f"webhook-test-{uuid.uuid4()}"
        for _ in range(3)
    ]

    alerts = [
        make_alert("firing", fingerprints[0]),
        make_alert("firing", fingerprints[1]),
        make_alert("resolved", fingerprints[2]),
    ]

    with TestClient(app) as client:
        response = client.post(
            "/webhooks/alertmanager",
            json=make_payload(alerts),
        )

    assert response.status_code == 200

    data = response.json()

    assert data["total_alerts"] == 3
    assert data["created_count"] == 2
    assert data["updated_count"] == 0
    assert data["resolved_count"] == 0
    assert data["ignored_count"] == 1

    assert get_incident(fingerprints[0]) is not None
    assert get_incident(fingerprints[1]) is not None
    assert get_incident(fingerprints[2]) is None


def test_invalid_payload_returns_422():
    with TestClient(app) as client:
        response = client.post(
            "/webhooks/alertmanager",
            json={"invalid": "payload"},
        )

    assert response.status_code == 422


def test_empty_alert_list():
    with TestClient(app) as client:
        response = client.post(
            "/webhooks/alertmanager",
            json=make_payload([]),
        )

    assert response.status_code == 200

    data = response.json()

    assert data["total_alerts"] == 0
    assert data["created_count"] == 0
    assert data["updated_count"] == 0
    assert data["resolved_count"] == 0
    assert data["ignored_count"] == 0
    assert data["processed_alerts"] == []
