import asyncio
from datetime import datetime, timezone
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
        all_logs, error_logs, warning_logs = await asyncio.gather(
            self.client.query(ALL_LOGS_QUERY),
            self.client.query(ERROR_LOGS_QUERY),
            self.client.query(WARNING_LOGS_QUERY),
        )

        return {
            "source": "loki",
            "namespace": self.NAMESPACE,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "logs": {
                "all": all_logs,
                "errors": error_logs,
                "warnings": warning_logs,
            }
        }
