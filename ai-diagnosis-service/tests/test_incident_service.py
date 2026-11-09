import uuid
from datetime import datetime, timezone, timedelta
from app.repositories.incident_repository import IncidentRepository
import pytest
from sqlalchemy import func, select
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import IntegrityError
from app.database.connection import SessionLocal
from app.models.incident import Incident
from app.schemas.alertmanager import Alert
from app.services.incident_service import IncidentService
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

@pytest.fixture
def db_session():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def service(db_session):
    return IncidentService(db_session)


@pytest.fixture
def alert_data():
    return {
        "status": "firing",
        "labels": {
            "alertname": "PodCrashLooping",
            "namespace": "voting-app",
            "pod": "vote-123",
            "severity": "warning",
        },
        "startsAt": datetime.now(timezone.utc).isoformat(),
        "fingerprint": f"test-{uuid.uuid4()}",
    }


def count_incidents(db_session, fingerprint):
    statement = (
        select(func.count())
        .select_from(Incident)
        .where(Incident.fingerprint == fingerprint)
    )
    return db_session.scalar(statement)



def test_firing_creates_incident(service, db_session, alert_data):
    alert = Alert(**alert_data)

    incident, action = service.process_alert(alert)

    assert action == "created"
    assert incident is not None
    assert incident.fingerprint == alert_data["fingerprint"]
    assert incident.alert_name == "PodCrashLooping"
    assert incident.status == "open"
    assert count_incidents(db_session, alert_data["fingerprint"]) == 1


def test_duplicate_firing_updates_last_seen(service, db_session, alert_data):
    alert = Alert(**alert_data)

    first_incident, first_action = service.process_alert(alert)
    original_first_seen = first_incident.first_seen_at
    original_id = first_incident.id

    second_incident, second_action = service.process_alert(alert)

    assert first_action == "created"
    assert second_action == "updated"
    assert second_incident.id == original_id
    assert second_incident.first_seen_at == original_first_seen
    assert second_incident.last_seen_at >= first_incident.last_seen_at
    assert count_incidents(db_session, alert_data["fingerprint"]) == 1


def test_resolved_closes_incident(service, db_session, alert_data):
    firing_alert = Alert(**alert_data)
    incident, _ = service.process_alert(firing_alert)

    resolved_alert = Alert(
        **{
            **alert_data,
            "status": "resolved",
            "endsAt": datetime.now(timezone.utc).isoformat(),
        }
    )

    resolved_incident, action = service.process_alert(resolved_alert)

    assert action == "resolved"
    assert resolved_incident is not None
    assert resolved_incident.id == incident.id
    assert resolved_incident.status == "resolved"
    assert resolved_incident.resolved_at is not None


def test_firing_after_resolved_creates_new_incident(service, db_session, alert_data):
    firing_alert = Alert(**alert_data)
    first_incident, _ = service.process_alert(firing_alert)

    resolved_alert = Alert(
        **{
            **alert_data,
            "status": "resolved",
            "endsAt": datetime.now(timezone.utc).isoformat(),
        }
    )
    service.process_alert(resolved_alert)

    new_firing_alert = Alert(
        **{
            **alert_data,
            "startsAt": (
                datetime.now(timezone.utc) + timedelta(seconds=1)
            ).isoformat(),
        }
    )
    second_incident, action = service.process_alert(new_firing_alert)

    assert action == "created"
    assert second_incident.id != first_incident.id
    assert second_incident.status == "open"
    assert count_incidents(db_session, alert_data["fingerprint"]) == 2


def test_resolved_without_active_incident_returns_none(service, db_session):
    resolved_alert = Alert(
        status="resolved",
        labels={"alertname": "PodCrashLooping"},
        startsAt=datetime.now(timezone.utc),
        endsAt=datetime.now(timezone.utc),
        fingerprint="nonexistent-fingerprint",
    )

    incident, action = service.process_alert(resolved_alert)

    assert incident is None
    assert action == "ignored"
    assert count_incidents(
        db_session, "nonexistent-fingerprint"
    ) == 0

def test_get_summary_counts_unexpected_status(db_session):
    fingerprint = f"summary-test-{uuid.uuid4()}"
    now = datetime.now(timezone.utc)

    incidents = [
        Incident(
            fingerprint=fingerprint,
            alert_name="TestAlert",
            status="open",
            first_seen_at=now,
            last_seen_at=now,
        ),
        Incident(
            fingerprint=fingerprint,
            alert_name="TestAlert",
            status="resolved",
            first_seen_at=now,
            last_seen_at=now,
        ),
        Incident(
            fingerprint=fingerprint,
            alert_name="TestAlert",
            status="unexpected",
            first_seen_at=now,
            last_seen_at=now,
        ),
    ]

    try:
        repository = IncidentRepository(db_session)
        before_summary = repository.get_summary()

        db_session.add_all(incidents)
        db_session.commit()

        summary = repository.get_summary()

        assert summary["total"] == before_summary["total"] + 3
        assert summary["open"] == before_summary["open"] + 1
        assert summary["acknowledged"] == before_summary["acknowledged"]
        assert summary["resolved"] == before_summary["resolved"] + 1

    finally:
        db_session.rollback()
        db_session.query(Incident).filter(
            Incident.fingerprint == fingerprint
        ).delete(synchronize_session=False)
        db_session.commit()

def test_integrity_error_recovers_existing_active_incident(service, db_session, alert_data):
    alert = Alert(**alert_data)

    incident = Incident(
        fingerprint=alert.fingerprint,
        alert_name="PodCrashLooping",
        status="open",
        first_seen_at=alert.startsAt,
        last_seen_at=datetime.now(timezone.utc),
    )

    integrity_error = IntegrityError(
        statement="INSERT INTO incidents",
        params={},
        orig=MagicMock(),
    )
    integrity_error.orig.diag = MagicMock(
        constraint_name="uq_incident_active_fingerprint"
    )

    with patch.object(
        service,
        "_acquire_fingerprint_lock",
    ), patch.object(
        service.repository,
        "create",
        side_effect=integrity_error,
    ), patch.object(
        service.repository,
        "get_active_by_fingerprint",
        return_value=incident,
    ), patch.object(
        service.repository,
        "update_last_seen",
        return_value=incident,
    ):
        result, action = service.process_alert(alert)

    assert result is incident
    assert action == "updated"
    assert not db_session.in_transaction()

def test_integrity_error_from_other_constraint_is_raised(service, db_session, alert_data):
    alert = Alert(**alert_data)

    integrity_error = IntegrityError(
        statement="INSERT INTO incidents",
        params={},
        orig=MagicMock(),
    )
    integrity_error.orig.diag = MagicMock(
        constraint_name="incidents_pkey"
    )

    with patch.object(
        service,
        "_acquire_fingerprint_lock",
    ), patch.object(
        service.repository,
        "create",
        side_effect=integrity_error,
    ):
        with pytest.raises(IntegrityError):
            service.process_alert(alert)

    assert not db_session.in_transaction()


def test_concurrent_firing_creates_only_one_active_incident(alert_data):
    fingerprint = f"concurrent-test-{uuid.uuid4()}"

    alert = Alert(
        **{
            **alert_data,
            "fingerprint": fingerprint,
        }
    )

    barrier = Barrier(2)

    def process_concurrently():
        db = SessionLocal()

        try:
            barrier.wait(timeout=10)

            service = IncidentService(db)
            incident, action = service.process_alert(alert)

            return incident.id, action

        finally:
            db.close()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(process_concurrently)
                for _ in range(2)
            ]

            results = [
                future.result(timeout=30)
                for future in futures
            ]

        actions = sorted(action for _, action in results)
        incident_ids = {incident_id for incident_id, _ in results}

        assert actions == ["created", "updated"]
        assert len(incident_ids) == 1

        with SessionLocal() as db:
            active_incidents = (
                db.query(Incident)
                .filter(
                    Incident.fingerprint == fingerprint,
                    Incident.status.in_(["open", "acknowledged"]),
                )
                .all()
            )

            assert len(active_incidents) == 1
            assert active_incidents[0].id in incident_ids

    finally:
        with SessionLocal() as db:
            db.query(Incident).filter(
                Incident.fingerprint == fingerprint
            ).delete(synchronize_session=False)
            db.commit()
