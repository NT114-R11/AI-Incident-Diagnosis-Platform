
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.schemas.incident_context import (
    IncidentContext,
    IncidentContextIncident,
    EvidenceCollectionStatus,
)
from app.services.evidence_validator import EvidenceValidator


@pytest.fixture
def incident_time():
    return datetime.now(timezone.utc)


def make_context(
    incident_time,
    *,
    namespace="voting-app",
    pod="vote-123",
    collection_status=None,
    evidence=None,
    first_seen_at=None,
    last_seen_at=None,
):
    return IncidentContext(
        incident=IncidentContextIncident(
            id=uuid4(),
            fingerprint="test-fingerprint",
            alert_name="PodCrashLooping",
            namespace=namespace,
            pod=pod,
            severity="warning",
            status="open",
            summary=None,
            first_seen_at=first_seen_at or incident_time,
            last_seen_at=last_seen_at or incident_time,
        ),
        evidence=evidence or {},
        collection_status=EvidenceCollectionStatus(
            **(
                collection_status
                or {
                    "prometheus": "failed",
                    "loki": "failed",
                    "kubernetes": "failed",
                }
            )
        ),
        collected_at=datetime.now(timezone.utc),
    )


def prometheus_evidence(
    timestamp,
    *,
    namespace="voting-app",
    pod="vote-123",
):
    return {
        "source": "prometheus",
        "metrics": {
            "cpu": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {
                            "namespace": namespace,
                            "pod": pod,
                            "container": "vote",
                        },
                        "value": [
                            timestamp.timestamp(),
                            "0.001",
                        ],
                    }
                ],
            }
        },
    }


def loki_evidence(
    timestamp,
    *,
    namespace="voting-app",
    pod="vote-123",
):
    timestamp_ns = str(int(timestamp.timestamp() * 1_000_000_000))

    return {
        "source": "loki",
        "logs": {
            "all": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {
                            "namespace": namespace,
                            "pod": pod,
                            "container": "vote",
                        },
                        "values": [
                            [timestamp_ns, "Application running"],
                        ],
                    }
                ],
            }
        },
    }


class TestEvidenceValidator:

    def test_accept_matching_prometheus_evidence(self, incident_time):
        context = make_context(
            incident_time,
            collection_status={
                "prometheus": "success",
                "loki": "failed",
                "kubernetes": "failed",
            },
            evidence={
                "prometheus": prometheus_evidence(incident_time),
            },
        )

        result = EvidenceValidator().validate(context)

        assert result.is_sufficient is True
        assert result.available_sources == ["prometheus"]
        assert result.unavailable_sources == ["loki", "kubernetes"]

    def test_reject_evidence_from_different_pod(self, incident_time):
        context = make_context(
            incident_time,
            collection_status={
                "prometheus": "success",
                "loki": "failed",
                "kubernetes": "failed",
            },
            evidence={
                "prometheus": prometheus_evidence(
                    incident_time,
                    pod="vote-5875fdd985-c9bgd",
                ),
            },
        )

        result = EvidenceValidator().validate(context)

        assert result.is_sufficient is False
        assert any(
            "No relevant Prometheus evidence" in warning
            for warning in result.warnings
        )

    def test_reject_evidence_from_different_namespace(self, incident_time):
        context = make_context(
            incident_time,
            collection_status={
                "prometheus": "success",
                "loki": "failed",
                "kubernetes": "failed",
            },
            evidence={
                "prometheus": prometheus_evidence(
                    incident_time,
                    namespace="default",
                ),
            },
        )

        result = EvidenceValidator().validate(context)

        assert result.is_sufficient is False

    def test_reject_stale_prometheus_evidence(self, incident_time):
        old_timestamp = incident_time - timedelta(minutes=11)

        context = make_context(
            incident_time,
            collection_status={
                "prometheus": "success",
                "loki": "failed",
                "kubernetes": "failed",
            },
            evidence={
                "prometheus": prometheus_evidence(old_timestamp),
            },
        )

        result = EvidenceValidator().validate(context)

        assert result.is_sufficient is False

    def test_accept_matching_loki_evidence(self, incident_time):
        context = make_context(
            incident_time,
            collection_status={
                "prometheus": "failed",
                "loki": "success",
                "kubernetes": "failed",
            },
            evidence={
                "loki": loki_evidence(incident_time),
            },
        )

        result = EvidenceValidator().validate(context)

        assert result.is_sufficient is True
        assert result.available_sources == ["loki"]

    def test_accept_matching_kubernetes_snapshot(self, incident_time):
        context = make_context(
            incident_time,
            collection_status={
                "prometheus": "failed",
                "loki": "failed",
                "kubernetes": "success",
            },
            evidence={
                "kubernetes": {
                    "source": "kubernetes",
                    "collected_at": incident_time.isoformat(),
                    "pods": [
                        {
                            "name": "vote-123",
                            "namespace": "voting-app",
                            "phase": "Running",
                            "containers": [],
                        }
                    ],
                    "events": [],
                    "deployments": [],
                }
            },
        )

        result = EvidenceValidator().validate(context)

        assert result.is_sufficient is True
        assert result.available_sources == ["kubernetes"]

    def test_insufficient_when_all_sources_failed(self, incident_time):
        context = make_context(incident_time)

        result = EvidenceValidator().validate(context)

        assert result.is_sufficient is False
        assert result.available_sources == []
        assert result.unavailable_sources == [
            "prometheus",
            "loki",
            "kubernetes",
        ]

    def test_namespace_only_accepts_any_pod_in_namespace(
        self,
        incident_time,
    ):
        context = make_context(
            incident_time,
            namespace="voting-app",
            pod=None,
            collection_status={
                "prometheus": "success",
                "loki": "failed",
                "kubernetes": "failed",
            },
            evidence={
                "prometheus": prometheus_evidence(
                    incident_time,
                    pod="redis-8569c9b7bd-c2b75",
                ),
            },
        )

        result = EvidenceValidator().validate(context)

        assert result.is_sufficient is True

    def test_warn_when_incident_time_range_is_invalid(
        self,
        incident_time,
    ):
        context = make_context(
            incident_time,
            first_seen_at=incident_time,
            last_seen_at=incident_time - timedelta(seconds=1),
        )

        result = EvidenceValidator().validate(context)

        assert "invalid_incident_time_range" in result.warnings
        assert result.is_sufficient is False
        assert "invalid_incident_time_range" in result.warnings
