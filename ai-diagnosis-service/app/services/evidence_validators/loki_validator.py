from datetime import datetime, timezone
from typing import Any

from app.services.evidence_validators.common import (
    is_fresh,
    is_relevant_target,
)


def validate_loki(data: dict[str, Any], namespace: str | None, pod: str | None, incident_time: datetime | None) -> bool:
    logs = data.get("logs", {})

    for log_type in ("all", "errors", "warnings"):
        log_data = logs.get(log_type, {})
        streams = log_data.get("result", [])

        for stream in streams:
            labels = stream.get("stream", {})

            if not is_relevant_target(
                namespace,
                pod,
                labels.get("namespace"),
                labels.get("pod"),
            ):
                continue

            values = stream.get("values", [])

            for value in values:
                if len(value) < 2:
                    continue

                try:
                    timestamp_ns = int(value[0])
                    timestamp = datetime.fromtimestamp(
                        timestamp_ns / 1_000_000_000,
                        tz=timezone.utc,
                    )
                except (ValueError, TypeError, OverflowError, OSError):
                    continue

                if is_fresh(timestamp, incident_time):
                    return True

    return False