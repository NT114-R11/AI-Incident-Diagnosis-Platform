from datetime import datetime
from typing import Any
import httpx
from app.config import settings


class PrometheusAPIError(Exception):
    """Raised when Prometheus returns an API error."""


class PrometheusClient:
    def __init__(self):
        self.base_url = settings.prometheus_url.rstrip("/")
        self.timeout = settings.prometheus_timeout_seconds

    async def query(self, promql: str) -> dict[str, Any]:
        return await self._request(
            "/api/v1/query",
            {"query": promql},
        )

    async def query_range(self, promql: str,start: datetime,end: datetime,step: str = "15s") -> dict[str, Any]:
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start and end must be timezone-aware")

        if start >= end:
            raise ValueError("start must be earlier than end")

        return await self._request(
            "/api/v1/query_range",
            {
                "query": promql,
                "start": start.timestamp(),
                "end": end.timestamp(),
                "step": step,
            }
        )

    async def _request(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            raise PrometheusAPIError(f"Prometheus returned HTTP {exc.response.status_code}") from exc

        except httpx.RequestError as exc:
            raise PrometheusAPIError(f"Could not connect to Prometheus: {exc}") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise PrometheusAPIError("Prometheus returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise PrometheusAPIError(
                "Prometheus returned an invalid response structure")

        if payload.get("status") != "success":
            error = payload.get("error", "Unknown Prometheus error")
            raise PrometheusAPIError(str(error))

        data = payload.get("data")

        if not isinstance(data, dict):
            raise PrometheusAPIError(
                "Prometheus response is missing valid data")

        return data
