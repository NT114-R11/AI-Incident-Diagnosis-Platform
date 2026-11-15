
import re
from typing import Any

from app.schemas.diagnosis import DiagnosisFinding
from app.schemas.incident_context import IncidentContext


LOG_PATTERNS = (
    (
        "APPLICATION_EXCEPTION",
        "application_exception",
        re.compile(r"exception|traceback|panic", re.IGNORECASE),
        "Application exception detected",
        "critical",
        0.95,
    ),
    (
        "APPLICATION_ERROR",
        "application_error",
        re.compile(r"\berror\b|failed|failure|\bfatal\b", re.IGNORECASE),
        "Application error detected",
        "high",
        0.90,
    ),
    (
        "APPLICATION_WARNING",
        "application_warning",
        re.compile(r"\bwarn(?:ing)?\b", re.IGNORECASE),
        "Application warning detected",
        "medium",
        0.80,
    ),
)


def detect_loki_issues(
    context: IncidentContext,
) -> list[DiagnosisFinding]:
    incident = context.incident
    loki = context.evidence.get("loki", {})
    logs = loki.get("logs", {})

    # Deduplicate log entries across all, errors and warnings.
    unique_entries = {}

    for log_type in ("all", "errors", "warnings"):
        log_data = logs.get(log_type, {})
        
        for stream in log_data.get("result", []):
            labels = stream.get("stream", {})

            namespace = labels.get("namespace")
            pod_name = labels.get("pod")
            container_name = labels.get("container")

            if incident.namespace and namespace != incident.namespace:
                continue

            if incident.pod and pod_name != incident.pod:
                continue

            for entry in stream.get("values", []):
                if len(entry) < 2:
                    continue

                timestamp, message = entry[0], entry[1]

                dedup_key = (
                    namespace,
                    pod_name,
                    container_name,
                    timestamp,
                    message,
                )

                unique_entries[dedup_key] = {
                    "namespace": namespace,
                    "pod": pod_name,
                    "container": container_name,
                    "timestamp": timestamp,
                    "message": str(message).strip(),
                }

    # Group findings by rule, Pod and container.
    grouped_findings = {}

    for entry in unique_entries.values():
        message = entry["message"]

        if not message:
            continue

        for (
            rule_id,
            category,
            pattern,
            title,
            severity,
            confidence,
        ) in LOG_PATTERNS:
            if not pattern.search(message):
                continue

            group_key = (
                rule_id,
                entry["namespace"],
                entry["pod"],
                entry["container"],
            )

            group = grouped_findings.setdefault(
                group_key,
                {
                    "rule_id": rule_id,
                    "category": category,
                    "title": title,
                    "severity": severity,
                    "confidence": confidence,
                    "pod": entry["pod"],
                    "container": entry["container"],
                    "count": 0,
                    "samples": [],
                },
            )

            group["count"] += 1

            if len(group["samples"]) < 3:
                group["samples"].append(message)

            # One log entry belongs to only one category.
            break

    findings = []

    for group in grouped_findings.values():
        pod_name = group["pod"] or "unknown"
        container_name = group["container"] or "unknown"

        samples = "\n".join(
            f"- {sample}" for sample in group["samples"]
        )

        findings.append(
            DiagnosisFinding(
                rule_id=group["rule_id"],
                category=group["category"],
                title=group["title"],
                description=(
                    f"Detected {group['count']} matching log "
                    f"entry/entries in container '{container_name}' "
                    f"of Pod '{pod_name}'.\n"
                    f"Sample logs:\n{samples}"
                ),
                severity=group["severity"],
                confidence=group["confidence"],
                evidence_refs=[
                    f"loki.logs.{pod_name}.{container_name}"
                ],
            )
        )

    return findings


