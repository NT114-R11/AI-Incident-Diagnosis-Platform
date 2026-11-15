
from datetime import datetime, timezone
from types import SimpleNamespace

from app.collectors.kubernetes.collector import KubernetesCollector


def make_container(
    state=None,
    last_state=None,
    restart_count=0,
    ready=True,
):
    return SimpleNamespace(
        name="vote",
        ready=ready,
        restart_count=restart_count,
        state=SimpleNamespace(
            waiting=None,
            running=None,
            terminated=None,
        ) if state is None else state,
        last_state=last_state or SimpleNamespace(
            waiting=None,
            running=None,
            terminated=None,
        ),
    )


def make_pod(container):
    now = datetime.now(timezone.utc)

    return SimpleNamespace(
        metadata=SimpleNamespace(
            name="vote-abc123",
            namespace="voting-app",
            labels={"app": "vote"},
        ),
        spec=SimpleNamespace(node_name="worker-1"),
        status=SimpleNamespace(
            phase="Running",
            conditions=[],
            container_statuses=[container],
        ),
    )


def test_collect_pod_container_state():
    waiting = SimpleNamespace(
        reason="CrashLoopBackOff",
        message="Back-off restarting failed container",
    )

    container = make_container(
        state=SimpleNamespace(
            waiting=waiting,
            running=None,
            terminated=None,
        ),
    )

    result = KubernetesCollector._collect_pods([
        make_pod(container)
    ])

    assert len(result) == 1
    assert result[0]["name"] == "vote-abc123"
    assert result[0]["namespace"] == "voting-app"
    assert result[0]["containers"][0]["state"] == {
        "type": "waiting",
        "reason": "CrashLoopBackOff",
        "message": "Back-off restarting failed container",
    }


def test_collect_pod_last_state_oom_killed():
    terminated = SimpleNamespace(
        reason="OOMKilled",
        message="Container killed due to memory usage",
        exit_code=137,
    )

    container = make_container(
        state=SimpleNamespace(
            waiting=None,
            running=SimpleNamespace(started_at=datetime.now(timezone.utc)),
            terminated=None,
        ),
        last_state=SimpleNamespace(
            waiting=None,
            running=None,
            terminated=terminated,
        ),
        restart_count=3,
    )

    result = KubernetesCollector._collect_pods([
        make_pod(container)
    ])

    collected_container = result[0]["containers"][0]

    assert collected_container["restart_count"] == 3
    assert collected_container["last_state"] == {
        "type": "terminated",
        "reason": "OOMKilled",
        "message": "Container killed due to memory usage",
        "exit_code": 137,
    }
