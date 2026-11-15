
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from app.services.diagnosis_rules.kubernetes_rules import (
    detect_pod_crash_loop,
    detect_pod_oom_killed,
    detect_pod_not_ready,
)

from app.services.diagnosis_rules.prometheus_rules import (
    detect_high_cpu,
    detect_high_memory,
)

from app.schemas.incident_context import (
    IncidentContext,
    IncidentContextIncident,
    EvidenceCollectionStatus,
)
from app.services.diagnosis_service import DiagnosisService


def make_incident_context(pod_state, pod_name="vote-abc123",last_state=None,conditions=None):
    now = datetime.now(timezone.utc)

    incident = IncidentContextIncident(
        id=uuid4(),
        fingerprint="test-fingerprint",
        alert_name="PodCrashLooping",
        namespace="voting-app",
        pod=pod_name,
        severity="warning",
        status="open",
        summary="Pod is restarting",
        first_seen_at=now,
        last_seen_at=now,
    )

    return IncidentContext(
        incident=incident,
        evidence={
            "kubernetes": {
                "source": "kubernetes",
                "namespace": "voting-app",
                "collected_at": now.isoformat(),
                "pods": [
                    {
                        "name": pod_name,
                        "namespace": "voting-app",
                        "phase": "Running",
                        "conditions": conditions or [],
                        "containers": [
                            {
                                "name": "vote",
                                "ready": False,
                                "restart_count": 5,
                                "state": pod_state,
                                "last_state": last_state
                            }
                        ],
                    }
                ],
                "events": [],
                "deployments": [],
            }
        },
        collection_status=EvidenceCollectionStatus(
            prometheus="failed",
            loki="failed",
            kubernetes="success",
        ),
        collected_at=now,
    )


def test_detect_pod_crash_loop():
    context = make_incident_context({
        "type": "waiting",
        "reason": "CrashLoopBackOff",
        "message": "Back-off restarting failed container",
    })

    # Rule implementation will be added to DiagnosisService.
    # This test specifies the expected behavior.
    service = DiagnosisService()

    findings = detect_pod_crash_loop(context)

    assert len(findings) == 1
    assert findings[0].rule_id == "POD_CRASH_LOOP"
    assert findings[0].category == "pod_crash_loop"
    assert findings[0].severity == "critical"


def test_do_not_detect_crash_loop_from_restart_count_alone():
    context = make_incident_context({
        "type": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    })

    service = DiagnosisService()

    findings = detect_pod_crash_loop(context)

    assert findings == []


def test_detect_pod_oom_killed_from_last_state():
    context = make_incident_context(
        pod_state={
            "type": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        },
        last_state={
            "type": "terminated",
            "reason": "OOMKilled",
            "message": "Container killed due to memory usage",
            "exit_code": 137,
        },
    )

    service = DiagnosisService()

    findings = detect_pod_oom_killed(context)

    assert len(findings) == 1
    assert findings[0].rule_id == "POD_OOM_KILLED"
    assert findings[0].category == "oom_killed"
    assert findings[0].severity == "critical"


def test_do_not_detect_oom_from_restart_count_alone():
    context = make_incident_context(
        pod_state={
            "type": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        },
        last_state=None,
    )

    service = DiagnosisService()

    findings = detect_pod_oom_killed(context)

    assert findings == []


def test_detect_pod_not_ready():
    context = make_incident_context(
        pod_state={
            "type": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        },
        conditions=[
            {
                "type": "Ready",
                "status": "False",
                "reason": "ContainersNotReady",
                "message": "containers with unready status",
            }
        ],
    )

    service = DiagnosisService()
    findings = detect_pod_not_ready(context)

    assert len(findings) == 1
    assert findings[0].rule_id == "POD_NOT_READY"
    assert findings[0].category == "pod_not_ready"
    assert findings[0].severity == "high"


def test_do_not_detect_pod_not_ready_when_ready_true():
    context = make_incident_context(
        pod_state={
            "type": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        },
        conditions=[
            {
                "type": "Ready",
                "status": "True",
                "reason": None,
                "message": None,
            }
        ],
    )

    service = DiagnosisService()
    findings = detect_pod_not_ready(context)

    assert findings == []


def test_do_not_detect_pod_not_ready_without_ready_condition():
    context = make_incident_context(
        pod_state={
            "type": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        },
        conditions=[
            {
                "type": "Initialized",
                "status": "True",
                "reason": None,
                "message": None,
            }
        ],
    )

    service = DiagnosisService()
    findings = detect_pod_not_ready(context)

    assert findings == []

def make_prometheus_context(
    cpu_value="0.1",
    memory_value="104857600",
    pod_name="vote-abc123",
    container_name="vote",
):
    return SimpleNamespace(
        incident=SimpleNamespace(
            namespace="voting-app",
            pod=pod_name,
        ),
        evidence={
            "prometheus": {
                "metrics": {
                    "cpu": {
                        "resultType": "vector",
                        "result": [
                            {
                                "metric": {
                                    "namespace": "voting-app",
                                    "pod": pod_name,
                                    "container": container_name,
                                },
                                "value": [
                                    1794504122.967,
                                    cpu_value,
                                ],
                            }
                        ],
                    },
                    "memory": {
                        "resultType": "vector",
                        "result": [
                            {
                                "metric": {
                                    "namespace": "voting-app",
                                    "pod": pod_name,
                                    "container": container_name,
                                },
                                "value": [
                                    1794504122.967,
                                    memory_value,
                                ],
                            }
                        ],
                    },
                },
            },
        },
    )



def test_detect_high_cpu():
    service = DiagnosisService()
    context = make_prometheus_context(cpu_value="0.95")

    findings = detect_high_cpu(context)

    assert len(findings) == 1
    assert findings[0].rule_id == "HIGH_CPU"
    assert findings[0].category == "high_cpu"
    assert findings[0].severity == "high"


def test_do_not_detect_high_cpu_below_threshold():
    service = DiagnosisService()
    context = make_prometheus_context(cpu_value="0.5")

    findings = detect_high_cpu(context)

    assert findings == []


def test_detect_high_memory():
    service = DiagnosisService()

    # 600 MiB
    context = make_prometheus_context(
        memory_value=str(600 * 1024 * 1024)
    )

    findings = detect_high_memory(context)

    assert len(findings) == 1
    assert findings[0].rule_id == "HIGH_MEMORY"
    assert findings[0].category == "high_memory"
    assert findings[0].severity == "high"


def test_do_not_detect_high_memory_below_threshold():
    service = DiagnosisService()

    # 256 MiB
    context = make_prometheus_context(
        memory_value=str(256 * 1024 * 1024)
    )

    findings = detect_high_memory(context)

    assert findings == []
