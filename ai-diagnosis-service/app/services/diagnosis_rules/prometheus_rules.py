from app.schemas.diagnosis import DiagnosisFinding
from app.schemas.incident_context import IncidentContext


def detect_high_cpu(context: IncidentContext) -> list[DiagnosisFinding]:
    incident = context.incident

    prometheus = context.evidence.get("prometheus", {})
    metrics = prometheus.get("metrics", {})
    cpu_metrics = metrics.get("cpu", {}).get("result", [])

    findings = []

    for item in cpu_metrics:
        metric = item.get("metric", {})

        if metric.get("namespace") != incident.namespace:
            continue

        if incident.pod and metric.get("pod") != incident.pod:
            continue

        value = item.get("value", [])

        if len(value) < 2:
            continue

        try:
            cpu_usage = float(value[1])
        except (TypeError, ValueError):
            continue

        if cpu_usage < 0.8:
            continue

        pod_name = metric.get("pod")
        container_name = metric.get("container")

        findings.append(
            DiagnosisFinding(
                rule_id="HIGH_CPU",
                category="high_cpu",
                title="Container CPU usage is high",
                description=(
                    f"Container '{container_name}' in Pod "
                    f"'{pod_name}' is using {cpu_usage:.3f} CPU cores, "
                    "which meets or exceeds the 0.8 core threshold."
                ),
                severity="high",
                confidence=0.90,
                evidence_refs=[
                    f"prometheus.metrics.cpu.{pod_name}.{container_name}"
                ],
            )
        )

    return findings



def detect_high_memory(context: IncidentContext) -> list[DiagnosisFinding]:
    incident = context.incident

    prometheus = context.evidence.get("prometheus", {})
    metrics = prometheus.get("metrics", {})
    memory_metrics = metrics.get("memory", {}).get("result", [])

    findings = []

    threshold_bytes = 512 * 1024 * 1024

    for item in memory_metrics:
        metric = item.get("metric", {})

        if metric.get("namespace") != incident.namespace:
            continue

        if incident.pod and metric.get("pod") != incident.pod:
            continue

        value = item.get("value", [])

        if len(value) < 2:
            continue

        try:
            memory_usage = float(value[1])
        except (TypeError, ValueError):
            continue

        if memory_usage < threshold_bytes:
            continue

        pod_name = metric.get("pod")
        container_name = metric.get("container")
        memory_mib = memory_usage / (1024 * 1024)

        findings.append(
            DiagnosisFinding(
                rule_id="HIGH_MEMORY",
                category="high_memory",
                title="Container memory usage is high",
                description=(
                    f"Container '{container_name}' in Pod "
                    f"'{pod_name}' is using {memory_mib:.2f} MiB, "
                    "which meets or exceeds the 512 MiB threshold."
                ),
                severity="high",
                confidence=0.90,
                evidence_refs=[
                    f"prometheus.metrics.memory.{pod_name}.{container_name}"
                ],
            )
        )

    return findings

def detect_prometheus_issues(context: IncidentContext) -> list[DiagnosisFinding]:
    findings = []

    findings.extend(detect_high_cpu(context))
    findings.extend(detect_high_memory(context))

    return findings