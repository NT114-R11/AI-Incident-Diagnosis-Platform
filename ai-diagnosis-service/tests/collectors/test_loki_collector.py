from unittest.mock import AsyncMock

import pytest

from app.collectors.loki.collector import LokiCollector
from app.collectors.loki.queries import (
    ALL_LOGS_QUERY,
    ERROR_LOGS_QUERY,
    WARNING_LOGS_QUERY,
)


@pytest.fixture
def mock_client():
    return AsyncMock()


@pytest.fixture
def collector(mock_client):
    return LokiCollector(client=mock_client)


@pytest.mark.asyncio
async def test_collect_returns_all_evidence(collector, mock_client):
    mock_client.query.side_effect = [
        {"resultType": "streams", "result": [{"stream": {"container": "vote"}, "values": []}]},
        {"resultType": "streams", "result": []},
        {"resultType": "streams", "result": []},
    ]

    result = await collector.collect()

    assert result["source"] == "loki"
    assert result["namespace"] == "voting-app"
    assert "collected_at" in result

    assert "all" in result["logs"]
    assert "errors" in result["logs"]
    assert "warnings" in result["logs"]


@pytest.mark.asyncio
async def test_collect_calls_all_queries(collector, mock_client):
    mock_client.query.return_value = {
        "resultType": "streams",
        "result": [],
    }

    await collector.collect()

    assert mock_client.query.call_count == 3

    called_queries = [
        call.args[0]
        for call in mock_client.query.call_args_list
    ]

    assert ALL_LOGS_QUERY in called_queries
    assert ERROR_LOGS_QUERY in called_queries
    assert WARNING_LOGS_QUERY in called_queries


@pytest.mark.asyncio
async def test_collect_raises_when_query_fails(collector, mock_client):
    mock_client.query.side_effect = Exception("Loki unavailable")

    with pytest.raises(Exception, match="Loki unavailable"):
        await collector.collect()
