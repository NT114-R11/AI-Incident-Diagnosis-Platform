
import pytest
from unittest.mock import AsyncMock

from app.collectors.prometheus.client import PrometheusClient
from app.collectors.prometheus.collector import PrometheusCollector
from app.collectors.prometheus.queries import (
    CPU_USAGE_QUERY,
    MEMORY_USAGE_QUERY,
    CONTAINER_RESTARTS_QUERY,
    POD_PHASE_QUERY,
    CONTAINER_WAITING_QUERY,
)


@pytest.fixture
def mock_client():
    client = AsyncMock(spec=PrometheusClient)

    client.query.side_effect = [
        {"resultType": "vector", "result": [{"metric": {"container": "vote"}, "value": [1, "0.5"]}]},
        {"resultType": "vector", "result": [{"metric": {"container": "vote"}, "value": [1, "1000"]}]},
        {"resultType": "vector", "result": [{"metric": {"container": "vote"}, "value": [1, "2"]}]},
        {"resultType": "vector", "result": [{"metric": {"pod": "vote"}, "value": [1, "1"]}]},
        {"resultType": "vector", "result": []},
    ]

    return client


@pytest.mark.asyncio
async def test_collect_returns_all_evidence(mock_client):
    collector = PrometheusCollector(client=mock_client)

    result = await collector.collect()
    assert result["source"] == "prometheus"
    assert result["namespace"] == "voting-app"
    assert "collected_at" in result
    metrics = result["metrics"]
    assert set(metrics.keys()) == {
        "cpu",
        "memory",
        "restarts",
        "pod_phases",
        "waiting",
    }

    assert metrics["cpu"]["result"][0]["metric"]["container"] == "vote"
    assert metrics["memory"]["result"][0]["value"][1] == "1000"
    assert metrics["restarts"]["result"][0]["value"][1] == "2"
    assert metrics["pod_phases"]["result"][0]["metric"]["pod"] == "vote"
    assert metrics["waiting"]["result"] == []


@pytest.mark.asyncio
async def test_collect_calls_all_prometheus_queries(mock_client):
    collector = PrometheusCollector(client=mock_client)

    await collector.collect()

    assert mock_client.query.call_count == 5

    called_queries = {
        call.args[0]
        for call in mock_client.query.call_args_list
    }

    assert called_queries == {
        CPU_USAGE_QUERY,
        MEMORY_USAGE_QUERY,
        CONTAINER_RESTARTS_QUERY,
        POD_PHASE_QUERY,
        CONTAINER_WAITING_QUERY,
    }


@pytest.mark.asyncio
async def test_collect_raises_when_a_query_fails(mock_client):
    mock_client.query.side_effect = RuntimeError("Prometheus unavailable")

    collector = PrometheusCollector(client=mock_client)

    with pytest.raises(RuntimeError, match="Prometheus unavailable"):
        await collector.collect()
