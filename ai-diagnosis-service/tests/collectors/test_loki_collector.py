
import pytest
from unittest.mock import AsyncMock

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
async def test_collect_calls_all_queries(collector, mock_client):
    mock_client.query_range.return_value = {
        "resultType": "streams",
        "result": [],
    }

    result = await collector.collect()

    assert mock_client.query_range.call_count == 3

    calls = mock_client.query_range.call_args_list
    queries = [call.args[0] for call in calls]

    assert ALL_LOGS_QUERY in queries
    assert ERROR_LOGS_QUERY in queries
    assert WARNING_LOGS_QUERY in queries

    for call in calls:
        assert call.args[1] < call.args[2]

    assert result["source"] == "loki"
    assert result["namespace"] == "voting-app"
    assert result["logs"]["all"]["result"] == []
    assert result["logs"]["errors"]["result"] == []
    assert result["logs"]["warnings"]["result"] == []


@pytest.mark.asyncio
async def test_collect_raises_when_query_fails(collector, mock_client):
    mock_client.query_range.side_effect = Exception("Loki unavailable")

    with pytest.raises(Exception, match="Loki unavailable"):
        await collector.collect()
