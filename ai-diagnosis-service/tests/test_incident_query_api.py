
import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database.connection import SessionLocal
from app.main import app
from app.models.incident import Incident


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def query_test_data():
    namespace = f"query-test-{uuid.uuid4()}"
    now = datetime.now(timezone.utc)

    incidents = [
        Incident(
            fingerprint=f"query-test-{uuid.uuid4()}",
            alert_name="TestOpenAlert",
            namespace=namespace,
            pod="vote-test-1",
            severity="warning",
            status="open",
            first_seen_at=now,
            last_seen_at=now,
        ),
        Incident(
            fingerprint=f"query-test-{uuid.uuid4()}",
            alert_name="TestResolvedAlert",
            namespace=namespace,
            pod="vote-test-2",
            severity="critical",
            status="resolved",
            first_seen_at=now,
            last_seen_at=now,
            resolved_at=now,
        ),
    ]

    with SessionLocal() as db:
        db.add_all(incidents)
        db.commit()

        for incident in incidents:
            db.refresh(incident)

        incident_ids = [incident.id for incident in incidents]

    yield {
        "namespace": namespace,
        "incident_ids": incident_ids,
    }

    with SessionLocal() as db:
        db.query(Incident).filter(
            Incident.namespace == namespace
        ).delete(synchronize_session=False)
        db.commit()


def test_list_incidents(client, query_test_data):
    response = client.get(
        "/incidents",
        params={"namespace": query_test_data["namespace"]},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["limit"] == 20
    assert data["offset"] == 0


def test_list_incidents_with_filters(client, query_test_data):
    response = client.get(
        "/incidents",
        params={
            "namespace": query_test_data["namespace"],
            "status": "open",
            "severity": "warning",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["status"] == "open"
    assert data["items"][0]["severity"] == "warning"


def test_list_incidents_pagination(client, query_test_data):
    response = client.get(
        "/incidents",
        params={
            "namespace": query_test_data["namespace"],
            "limit": 1,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert len(data["items"]) == 1
    assert data["limit"] == 1
    assert data["offset"] == 0


def test_get_incident_by_id(client, query_test_data):
    incident_id = query_test_data["incident_ids"][0]

    response = client.get(f"/incidents/{incident_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(incident_id)


def test_get_nonexistent_incident_returns_404(client):
    response = client.get(f"/incidents/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Incident not found"


def test_get_invalid_incident_id_returns_422(client):
    response = client.get("/incidents/not-a-uuid")

    assert response.status_code == 422


def test_get_incident_summary(client):
    response = client.get("/incidents/summary")

    assert response.status_code == 200

    data = response.json()

    assert "total" in data
    assert "open" in data
    assert "acknowledged" in data
    assert "resolved" in data


def test_list_incidents_invalid_status_returns_422(client):
    response = client.get(
        "/incidents",
        params={"status": "invalid"},
    )

    assert response.status_code == 422


def test_list_incidents_invalid_pagination_returns_422(client):
    response = client.get(
        "/incidents",
        params={"limit": 101},
    )

    assert response.status_code == 422
