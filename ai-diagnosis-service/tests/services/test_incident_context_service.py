
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.incident_context_service import IncidentContextService


@pytest.fixture
def incident():
    now = datetime.now(timezone.utc)

    return SimpleNamespace(
        id=uuid4(),
        fingerprint="test-fingerprint",
        alert_name="HighContainerCPU",
        namespace="voting-app",
        pod="vote-pod",
        severity="warning",
        status="open",
        summary="High CPU usage",
        first_seen_at=now,
        last_seen_at=now,
    )


@pytest.mark.asyncio
async def test_collect_all_sources_success(incident):
    prometheus = AsyncMock()
    prometheus.collect.return_value = {
        "source": "prometheus",
        "metrics": {"cpu": []},
    }

    loki = AsyncMock()
    loki.collect.return_value = {
        "source": "loki",
        "logs": {"errors": []},
    }

    kubernetes = AsyncMock()
    kubernetes.collect.return_value = {
        "source": "kubernetes",
        "pods": [],
    }

    service = IncidentContextService(
        prometheus_collector=prometheus,
        loki_collector=loki,
        kubernetes_collector=kubernetes,
    )

    context = await service.collect(incident)

    assert context.incident.id == incident.id
    assert context.collection_status.prometheus == "success"
    assert context.collection_status.loki == "success"
    assert context.collection_status.kubernetes == "success"

    assert "prometheus" in context.evidence
    assert "loki" in context.evidence
    assert "kubernetes" in context.evidence


@pytest.mark.asyncio
async def test_collect_partial_failure(incident):
    prometheus = AsyncMock()
    prometheus.collect.return_value = {
        "source": "prometheus",
        "metrics": {"cpu": []},
    }

    loki = AsyncMock()
    loki.collect.side_effect = RuntimeError("Loki unavailable")

    kubernetes = AsyncMock()
    kubernetes.collect.return_value = {
        "source": "kubernetes",
        "pods": [],
    }

    service = IncidentContextService(
        prometheus_collector=prometheus,
        loki_collector=loki,
        kubernetes_collector=kubernetes,
    )

    context = await service.collect(incident)

    assert context.collection_status.prometheus == "success"
    assert context.collection_status.loki == "failed"
    assert context.collection_status.kubernetes == "success"

    assert context.evidence["loki"]["error"] == "Loki unavailable"
    assert "metrics" in context.evidence["prometheus"]
    assert "pods" in context.evidence["kubernetes"]
