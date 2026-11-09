
from datetime import datetime, timezone
from unittest.mock import patch

import httpx
import pytest

from app.collectors.prometheus.client import (
    PrometheusAPIError,
    PrometheusClient,
)


def mock_prometheus_http(transport):
    original_async_client = httpx.AsyncClient

    return patch(
        "app.collectors.prometheus.client.httpx.AsyncClient",
        side_effect=lambda **kwargs: original_async_client(
            transport=transport,
            **kwargs,
        ),
    )

@pytest.fixture
def client():
    return PrometheusClient()


@pytest.mark.asyncio
async def test_query_success(client):
    expected_data = {
        "resultType": "vector",
        "result": [
            {
                "metric": {"container": "vote"},
                "value": [1, "0.5"],
            }
        ],
    }

    def handler(request):
        assert request.url.path == "/api/v1/query"
        assert request.url.params["query"] == "up"
        return httpx.Response(
            200,
            json={"status": "success", "data": expected_data},
        )

    transport = httpx.MockTransport(handler)

    with mock_prometheus_http(transport):
        result = await client.query("up")

    assert result == expected_data


@pytest.mark.asyncio
async def test_query_range_success(client):
    expected_data = {
        "resultType": "matrix",
        "result": [],
    }

    start = datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 9, 10, 5, tzinfo=timezone.utc)

    def handler(request):
        assert request.url.path == "/api/v1/query_range"
        assert request.url.params["query"] == "up"
        assert request.url.params["step"] == "15s"
        return httpx.Response(
            200,
            json={"status": "success", "data": expected_data},
        )

    transport = httpx.MockTransport(handler)
    
    with mock_prometheus_http(transport):
        result = await client.query_range(
            "up",
            start,
            end,
        )

    assert result == expected_data


@pytest.mark.asyncio
async def test_query_http_error(client):
    def handler(request):
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)

    with mock_prometheus_http(transport):
        with pytest.raises(
            PrometheusAPIError,
            match="HTTP 500",
        ):
            await client.query("up")


@pytest.mark.asyncio
async def test_query_connection_error(client):
    def handler(request):
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(handler)

    with mock_prometheus_http(transport):
        with pytest.raises(
            PrometheusAPIError,
            match="Could not connect to Prometheus",
        ):
            await client.query("up")


@pytest.mark.asyncio
async def test_query_prometheus_api_error(client):
    def handler(request):
        return httpx.Response(
            200,
            json={
                "status": "error",
                "errorType": "bad_data",
                "error": "invalid PromQL expression",
            },
        )

    transport = httpx.MockTransport(handler)

    with mock_prometheus_http(transport):
        with pytest.raises(
            PrometheusAPIError,
            match="invalid PromQL expression",
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

    with mock_prometheus_http(transport):
        with pytest.raises(
            PrometheusAPIError,
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

    with mock_prometheus_http(transport):
        with pytest.raises(
            PrometheusAPIError,
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

    with mock_prometheus_http(transport):
        with pytest.raises(
            PrometheusAPIError,
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
