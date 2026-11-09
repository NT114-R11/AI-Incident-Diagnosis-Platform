
from datetime import datetime, timezone
from typing import Any
import asyncio

from app.collectors.prometheus.client import PrometheusClient
from app.collectors.prometheus.queries import (
    CPU_USAGE_QUERY,
    MEMORY_USAGE_QUERY,
    CONTAINER_RESTARTS_QUERY,
    POD_PHASE_QUERY,
    CONTAINER_WAITING_QUERY,
)


class PrometheusCollector:
    NAMESPACE = "voting-app"

    def __init__(self, client: PrometheusClient | None = None):
        self.client = client or PrometheusClient()

    async def collect(self) -> dict[str, Any]:
        cpu, memory, restarts, phases, waiting = await asyncio.gather(
            self.client.query(CPU_USAGE_QUERY),
            self.client.query(MEMORY_USAGE_QUERY),
            self.client.query(CONTAINER_RESTARTS_QUERY),
            self.client.query(POD_PHASE_QUERY),
            self.client.query(CONTAINER_WAITING_QUERY),
        )

        return {
            "source": "prometheus",
            "namespace": self.NAMESPACE,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "cpu": cpu,
                "memory": memory,
                "restarts": restarts,
                "pod_phases": phases,
                "waiting": waiting,
            },
        }
