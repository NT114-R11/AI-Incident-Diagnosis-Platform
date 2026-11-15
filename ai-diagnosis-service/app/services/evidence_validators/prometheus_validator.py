from datetime import datetime, timezone
from typing import Any

from app.services.evidence_validators.common import (is_fresh,is_relevant_target)


def validate_prometheus(data: dict[str, Any], namespace: str | None, pod: str | None, incident_time: datetime | None) -> bool:
    metrics = data.get("metrics", {})

    for metric_name in ("cpu", "memory", "restarts", "pod_phases", "waiting"):
        metric_data = metrics.get(metric_name, {})
        results = metric_data.get("result", [])

        for item in results:
            labels = item.get("metric", {})

            if not is_relevant_target(
                namespace,
                pod,
                labels.get("namespace"),
                labels.get("pod"),
            ):
                continue

            values = item.get("value", [])

            if len(values) < 2:
                continue

            try:
                timestamp = datetime.fromtimestamp(
                    float(values[0]),
                    tz=timezone.utc,
                )
            except (TypeError, ValueError, OverflowError, OSError):
                continue

            if is_fresh(timestamp, incident_time):
                return True

    return False