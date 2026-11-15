from datetime import datetime
from typing import Any

from app.services.evidence_validators.common import (
    is_fresh,
    is_relevant_target,
    latest_timestamp,
    parse_datetime,
)


def validate_kubernetes(data: dict[str, Any], namespace: str | None, pod: str | None, incident_time: datetime | None) -> bool:
    collected_at = parse_datetime(data.get("collected_at"))

    # Pod and Deployment data represent a current snapshot.
    if collected_at and is_fresh(collected_at, incident_time):
        pods = data.get("pods", [])

        for item in pods:
            if is_relevant_target(
                namespace,
                pod,
                item.get("namespace"),
                item.get("name"),
            ):
                return True

        deployments = data.get("deployments", [])

        if namespace and not pod:
            for item in deployments:
                if item.get("namespace") == namespace:
                    return True

    # Events have their own timestamps.
    for event in data.get("events", []):
        involved_object = event.get("involved_object", {})

        if not is_relevant_target(
            namespace,
            pod,
            event.get("namespace"),
            (
                involved_object.get("name")
                if involved_object.get("kind") == "Pod"
                else None
            )):
            continue

        event_time = latest_timestamp(
            parse_datetime(event.get("first_timestamp")),
            parse_datetime(event.get("last_timestamp")),
        )

        if is_fresh(event_time, incident_time):
            return True

    return False