
import hashlib
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.repositories.incident_repository import IncidentRepository
from app.schemas.alertmanager import Alert


class IncidentService:
    ACTIVE_FINGERPRINT_CONSTRAINT = "uq_incident_active_fingerprint"

    def __init__(self, db: Session):
        self.db = db
        self.repository = IncidentRepository(db)

    @staticmethod
    def _fingerprint_lock_key(fingerprint: str) -> int:
        digest = hashlib.sha256(fingerprint.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], byteorder="big", signed=True)

    def _acquire_fingerprint_lock(self, fingerprint: str) -> None:
        lock_key = self._fingerprint_lock_key(fingerprint)

        self.db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": lock_key},
        )

    def _is_active_fingerprint_conflict(
        self,
        error: IntegrityError,
    ) -> bool:
        original_error = error.orig
        diagnostics = getattr(original_error, "diag", None)
        constraint_name = getattr(
            diagnostics,
            "constraint_name",
            None,
        )

        return constraint_name == self.ACTIVE_FINGERPRINT_CONSTRAINT

    def _recover_duplicate_firing(
        self,
        alert: Alert,
    ) -> tuple[Incident, str]:
        with self.db.begin():
            self._acquire_fingerprint_lock(alert.fingerprint)

            incident = self.repository.get_active_by_fingerprint(
                alert.fingerprint
            )

            if incident is None:
                raise RuntimeError(
                    "Active incident not found after unique constraint conflict"
                )

            now = datetime.now(timezone.utc)

            self.repository.update_last_seen(incident, now)

            return incident, "updated"

    def process_alert(self, alert: Alert) -> tuple[Incident | None, str]:
        try:
            if self.db.in_transaction():
                self.db.commit()

            with self.db.begin():
                self._acquire_fingerprint_lock(alert.fingerprint)

                incident = self.repository.get_active_by_fingerprint(
                    alert.fingerprint
                )

                now = datetime.now(timezone.utc)

                if alert.status == "firing":
                    if incident is None:
                        incident = Incident(
                            fingerprint=alert.fingerprint,
                            alert_name=alert.labels.get(
                                "alertname", "unknown"
                            ),
                            namespace=alert.labels.get("namespace"),
                            pod=alert.labels.get("pod"),
                            severity=alert.labels.get("severity"),
                            status="open",
                            first_seen_at=alert.startsAt,
                            last_seen_at=now,
                        )

                        return self.repository.create(incident), "created"

                    self.repository.update_last_seen(incident, now)

                    return incident, "updated"

                if alert.status == "resolved":
                    if incident is None:
                        return None, "ignored"

                    self.repository.resolve(
                        incident,
                        alert.endsAt or now,
                    )

                    return incident, "resolved"

                return None, "ignored"

        except IntegrityError as error:
            self.db.rollback()

            if (
                alert.status != "firing"
                or not self._is_active_fingerprint_conflict(error)
            ):
                raise

            return self._recover_duplicate_firing(alert)

        except Exception:
            self.db.rollback()
            raise
