
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from app.collectors.loki.client import LokiClient
from app.collectors.loki.queries import (
    NAMESPACE,
    ALL_LOGS_QUERY,
    ERROR_LOGS_QUERY,
    WARNING_LOGS_QUERY,
)


class LokiCollector:
    NAMESPACE = NAMESPACE

    def __init__(self, client: LokiClient | None = None):
        self.client = client or LokiClient()

    async def collect(self) -> dict[str, Any]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=15)

        all_logs, error_logs, warning_logs = await asyncio.gather(
            self.client.query_range(ALL_LOGS_QUERY, start, end),
            self.client.query_range(ERROR_LOGS_QUERY, start, end),
            self.client.query_range(WARNING_LOGS_QUERY, start, end),
        )

        return {
            "source": "loki",
            "namespace": self.NAMESPACE,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "time_range": {
                "start": start.isoformat(),
                "end": end.isoformat(),
            },
            "logs": {
                "all": all_logs,
                "errors": error_logs,
                "warnings": warning_logs,
            },
        }
