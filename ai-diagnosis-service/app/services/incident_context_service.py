
import asyncio
from datetime import datetime, timezone

from app.models.incident import Incident
from app.schemas.incident_context import (
    IncidentContext,
    IncidentContextIncident,
    EvidenceCollectionStatus,
)
from app.collectors.prometheus.collector import PrometheusCollector
from app.collectors.loki.collector import LokiCollector
from app.collectors.kubernetes.collector import KubernetesCollector


class IncidentContextService:
    def __init__(
        self,
        prometheus_collector: PrometheusCollector | None = None,
        loki_collector: LokiCollector | None = None,
        kubernetes_collector: KubernetesCollector | None = None,
    ):
        self.prometheus_collector = (
            prometheus_collector or PrometheusCollector()
        )
        self.loki_collector = loki_collector or LokiCollector()
        self.kubernetes_collector = (
            kubernetes_collector or KubernetesCollector()
        )

    async def collect(
        self,
        incident: Incident,
    ) -> IncidentContext:
        results = await asyncio.gather(
            self.prometheus_collector.collect(),
            self.loki_collector.collect(),
            self.kubernetes_collector.collect(),
            return_exceptions=True,
        )

        evidence = {}
        statuses = {}

        sources = ("prometheus", "loki", "kubernetes")

        for source, result in zip(sources, results):
            if isinstance(result, Exception):
                evidence[source] = {
                    "error": str(result),
                }
                statuses[source] = "failed"
            else:
                evidence[source] = result
                statuses[source] = "success"

        return IncidentContext(
            incident=IncidentContextIncident.model_validate(
                incident,
                from_attributes=True,
            ),
            evidence=evidence,
            collection_status=EvidenceCollectionStatus(
                **statuses
            ),
            collected_at=datetime.now(timezone.utc),
        )
