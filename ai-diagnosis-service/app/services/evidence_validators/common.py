from datetime import datetime, timezone
from typing import Any

from app.config import settings


def is_relevant_target(namespace: str | None,pod: str | None,target_namespace: str | None,target_pod: str | None) -> bool:
    if namespace and target_namespace != namespace:
        return False

    if pod and target_pod != pod:
        return False

    return True


def is_fresh(timestamp: datetime | None,incident_time: datetime | None) -> bool:
    if timestamp is None or incident_time is None:
        return False

    age_seconds = abs(
        (timestamp - incident_time).total_seconds()
    )

    max_age_seconds = settings.max_evidence_age_minutes * 60

    return age_seconds <= max_age_seconds


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, str):
        try:
            result = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except ValueError:
            return None
    else:
        return None

    if result.tzinfo is None:
        return result.replace(tzinfo=timezone.utc)

    return result.astimezone(timezone.utc)


def latest_timestamp(first: datetime | None,second: datetime | None) -> datetime | None:
    timestamps = [
        value for value in (first, second)
        if value is not None
    ]

    return max(timestamps) if timestamps else None
