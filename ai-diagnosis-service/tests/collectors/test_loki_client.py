from datetime import datetime, timezone
from unittest.mock import patch

import httpx
import pytest

from app.collectors.loki.client import (
    LokiAPIError,
    LokiClient,
)


def mock_loki_http(transport):
    original_async_client = httpx.AsyncClient

    return patch(
        "app.collectors.loki.client.httpx.AsyncClient",
        side_effect=lambda **kwargs: original_async_client(
            transport=transport,
            **kwargs,
        ),
    )


@pytest.fixture
def client():
    return LokiClient()


@pytest.mark.asyncio
async def test_query_success(client):
    expected_data = {
        "resultType": "streams",
        "result": [
            {
                "stream": {
                    "container": "vote",
                    "namespace": "voting-app",
                },
                "values": [
                    ["1794218400000000000", "Vote service started"]
                ],
            }
        ],
    }

    def handler(request):
        assert request.url.path == "/loki/api/v1/query"
        assert request.url.params["query"] == '{namespace="voting-app"}'
        assert request.url.params["limit"] == "100"
        assert request.url.params["direction"] == "backward"

        return httpx.Response(
            200,
            json={"status": "success", "data": expected_data},
        )

    transport = httpx.MockTransport(handler)

    with mock_loki_http(transport):
        result = await client.query('{namespace="voting-app"}')

    assert result == expected_data


@pytest.mark.asyncio
async def test_query_range_success(client):
    expected_data = {
        "resultType": "streams",
        "result": [],
    }

    start = datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 9, 10, 5, tzinfo=timezone.utc)

    def handler(request):
        assert request.url.path == "/loki/api/v1/query_range"
        assert request.url.params["query"] == '{namespace="voting-app"}'
        assert request.url.params["start"] == str(
            int(start.timestamp() * 1_000_000_000)
        )
        assert request.url.params["end"] == str(
            int(end.timestamp() * 1_000_000_000)
        )
        assert request.url.params["limit"] == "1000"
        assert request.url.params["direction"] == "backward"

        return httpx.Response(
            200,
            json={"status": "success", "data": expected_data},
        )

    transport = httpx.MockTransport(handler)

    with mock_loki_http(transport):
        result = await client.query_range(
            '{namespace="voting-app"}',
            start,
            end,
        )

    assert result == expected_data


@pytest.mark.asyncio
async def test_query_http_error(client):
    def handler(request):
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)

    with mock_loki_http(transport):
        with pytest.raises(
            LokiAPIError,
            match="HTTP 500",
        ):
            await client.query("up")


@pytest.mark.asyncio
async def test_query_connection_error(client):
    def handler(request):
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(handler)

    with mock_loki_http(transport):
        with pytest.raises(
            LokiAPIError,
            match="Could not connect to Loki",
        ):
            await client.query("up")


@pytest.mark.asyncio
async def test_query_loki_api_error(client):
    def handler(request):
        return httpx.Response(
            200,
            json={
                "status": "error",
                "errorType": "parse",
                "error": "invalid LogQL expression",
            },
        )

    transport = httpx.MockTransport(handler)

    with mock_loki_http(transport):
        with pytest.raises(
            LokiAPIError,
            match="invalid LogQL expression",
        ):
            await client.query("invalid query")


@pytest.mark.asyncio
async def test_query_invalid_json(client):
    def handler(request):
        return httpx.Response(
            200,
            content=b"not-json",
        )

    transport = httpx.MockTransport(handler)

    with mock_loki_http(transport):
        with pytest.raises(
            LokiAPIError,
            match="invalid JSON",
        ):
            await client.query("up")


@pytest.mark.asyncio
async def test_query_invalid_response_structure(client):
    def handler(request):
        return httpx.Response(
            200,
            json=["unexpected", "response"],
        )

    transport = httpx.MockTransport(handler)

    with mock_loki_http(transport):
        with pytest.raises(
            LokiAPIError,
            match="invalid response structure",
        ):
            await client.query("up")


@pytest.mark.asyncio
async def test_query_missing_data(client):
    def handler(request):
        return httpx.Response(
            200,
            json={"status": "success"},
        )

    transport = httpx.MockTransport(handler)

    with mock_loki_http(transport):
        with pytest.raises(
            LokiAPIError,
            match="missing valid data",
        ):
            await client.query("up")


@pytest.mark.asyncio
async def test_query_range_rejects_naive_datetime(client):
    start = datetime(2026, 11, 9, 10, 0)
    end = datetime(2026, 11, 9, 10, 5)

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        await client.query_range("up", start, end)


@pytest.mark.asyncio
async def test_query_range_rejects_invalid_time_range(client):
    start = datetime(2026, 11, 9, 10, 5, tzinfo=timezone.utc)
    end = datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc)

    with pytest.raises(
        ValueError,
        match="earlier than end",
    ):
        await client.query_range("up", start, end)
