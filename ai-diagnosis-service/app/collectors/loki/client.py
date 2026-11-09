
from datetime import datetime
from typing import Any
import httpx
from app.config import settings


class LokiAPIError(Exception):
    """Raised when Loki returns an API error."""


class LokiClient:
    def __init__(self):
        self.base_url = settings.loki_url.rstrip("/")
        self.timeout = settings.loki_timeout_seconds

    async def query(self, logql: str, limit: int = 100, direction: str = "backward") -> dict[str, Any]:
        return await self._request(
            "/loki/api/v1/query",
            {
                "query": logql,
                "limit": limit,
                "direction": direction,
            },
        )

    async def query_range(self, logql: str, start: datetime, end: datetime, limit: int = 1000, direction: str = "backward") -> dict[str, Any]:
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start and end must be timezone-aware")

        if start >= end:
            raise ValueError("start must be earlier than end")

        return await self._request(
            "/loki/api/v1/query_range",
            {
                "query": logql,
                "start": int(start.timestamp() * 1_000_000_000),
                "end": int(end.timestamp() * 1_000_000_000),
                "limit": limit,
                "direction": direction,
            },
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
            raise LokiAPIError(
                f"Loki returned HTTP {exc.response.status_code}"
            ) from exc

        except httpx.RequestError as exc:
            raise LokiAPIError(
                f"Could not connect to Loki: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise LokiAPIError(
                "Loki returned invalid JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise LokiAPIError(
                "Loki returned an invalid response structure"
            )

        if payload.get("status") != "success":
            error = payload.get("error", "Unknown Loki error")
            raise LokiAPIError(str(error))

        data = payload.get("data")

        if not isinstance(data, dict):
            raise LokiAPIError(
                "Loki response is missing valid data"
            )

        return data
