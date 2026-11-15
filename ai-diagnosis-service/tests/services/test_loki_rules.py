from types import SimpleNamespace
import pytest
from app.services.diagnosis_rules.loki_rules import detect_loki_issues


from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.incident_context import (
    IncidentContext,
    IncidentContextIncident,
    EvidenceCollectionStatus,
)


def make_context(
    logs: dict,
    namespace: str = "voting-app",
    pod: str | None = "vote-123",
):
    return SimpleNamespace(
        incident=SimpleNamespace(
            namespace=namespace,
            pod=pod,
        ),
        evidence={
            "loki": {
                "logs": logs,
            }
        },
    )


def make_stream(message: str, timestamp: str = "1794566363070069753", namespace: str = "voting-app", pod: str = "vote-123", container: str = "vote"):
    return {
        "stream": {
            "namespace": namespace,
            "pod": pod,
            "container": container,
        },
        "values": [
            [timestamp, message],
        ],
    }


def make_logs(all_logs: list | None = None, errors: list | None = None, warnings: list | None = None):
    return {
        "all": {"result": all_logs or []},
        "errors": {"result": errors or []},
        "warnings": {"result": warnings or []},
    }


def test_detect_application_exception():
    context = make_context(
        make_logs(
            all_logs=[
                make_stream(
                    "Traceback: DatabaseConnectionError"
                )
            ]
        )
    )

    findings = detect_loki_issues(context)

    assert len(findings) == 1
    assert findings[0].rule_id == "APPLICATION_EXCEPTION"
    assert findings[0].category == "application_exception"
    assert findings[0].severity == "critical"


def test_detect_application_error():
    context = make_context(
        make_logs(
            all_logs=[
                make_stream("Database connection failed")
            ]
        )
    )

    findings = detect_loki_issues(context)

    assert len(findings) == 1
    assert findings[0].rule_id == "APPLICATION_ERROR"
    assert findings[0].severity == "high"


def test_detect_application_warning():
    context = make_context(
        make_logs(
            all_logs=[
                make_stream("WARNING: Request took too long")
            ]
        )
    )

    findings = detect_loki_issues(context)

    assert len(findings) == 1
    assert findings[0].rule_id == "APPLICATION_WARNING"
    assert findings[0].severity == "medium"


def test_exception_has_priority_over_error_and_warning():
    context = make_context(
        make_logs(
            all_logs=[
                make_stream(
                    "Fatal exception occurred, warning detected"
                )
            ]
        )
    )

    findings = detect_loki_issues(context)

    assert len(findings) == 1
    assert findings[0].rule_id == "APPLICATION_EXCEPTION"


def test_duplicate_logs_are_counted_only_once():
    duplicated_stream = make_stream("Database connection failed")

    context = make_context(
        make_logs(
            all_logs=[duplicated_stream],
            errors=[duplicated_stream],
        )
    )

    findings = detect_loki_issues(context)

    assert len(findings) == 1
    assert "Detected 1 matching log" in findings[0].description


def test_logs_from_different_namespace_are_ignored():
    context = make_context(
        make_logs(
            all_logs=[
                make_stream(
                    "Database connection failed",
                    namespace="another-namespace",
                )
            ]
        )
    )

    findings = detect_loki_issues(context)

    assert findings == []


def test_logs_from_different_pod_are_ignored():
    context = make_context(
        make_logs(
            all_logs=[
                make_stream(
                    "Database connection failed",
                    pod="another-pod",
                )
            ]
        )
    )

    findings = detect_loki_issues(context)

    assert findings == []


def test_normal_logs_do_not_generate_findings():
    context = make_context(
        make_logs(
            all_logs=[
                make_stream("Connected to db"),
                make_stream("Waiting for db"),
                make_stream("Found redis at 10.96.9.26"),
            ]
        )
    )

    findings = detect_loki_issues(context)

    assert findings == []


def test_multiple_errors_in_same_container_are_grouped():
    context = make_context(
        make_logs(
            all_logs=[
                make_stream(
                    "Database connection failed",
                    timestamp="1794566363070069753",
                ),
                make_stream(
                    "Request failed",
                    timestamp="1794566363070069754",
                ),
            ]
        )
    )

    findings = detect_loki_issues(context)

    assert len(findings) == 1
    assert "Detected 2 matching log" in findings[0].description


def test_empty_loki_logs_return_no_findings():
    context = make_context(make_logs())

    findings = detect_loki_issues(context)

    assert findings == []

def test_detect_real_postgres_connection_error():
    from datetime import datetime, timezone
    from uuid import uuid4

    from app.schemas.incident import Incident
    from app.schemas.incident_context import IncidentContext

    incident = Incident(
        incident_id=uuid4(),
        namespace="voting-app",
        pod="result-6bb5cdc67f-vs22g",
    )

    real_loki_response = {
        "logs": {
            "all": {
                "result": [
                    {
                        "stream": {
                            "namespace": "voting-app",
                            "pod": "result-6bb5cdc67f-vs22g",
                            "container": "result",
                        },
                        "values": [
                            [
                                "1794569372344092162",
                                "error: terminating connection due to administrator command",
                            ],
                        ],
                    }
                ]
            }
        }
    }

    context = IncidentContext(
        incident=incident,
        evidence={"loki": real_loki_response},
    )

    findings = detect_loki_issues(context)

    assert len(findings) == 1

    finding = findings[0]

    assert finding.rule_id == "APPLICATION_ERROR"
    assert finding.category == "application_error"
    assert finding.severity == "high"
    assert finding.confidence == 0.90
    assert "terminating connection" in finding.description
    assert finding.evidence_refs == [
        "loki.logs.result-6bb5cdc67f-vs22g.result"
    ]
def test_detect_real_postgres_connection_error():
    now = datetime.now(timezone.utc)

    incident = IncidentContextIncident(
        id=uuid4(),
        fingerprint="postgres-connection-failure",
        alert_name="PostgresConnectionFailure",
        namespace="voting-app",
        pod="result-6bb5cdc67f-vs22g",
        severity="high",
        status="firing",
        summary="PostgreSQL connection terminated unexpectedly",
        first_seen_at=now,
        last_seen_at=now,
    )

    real_loki_response = {
        "logs": {
            "all": {
                "result": [
                    {
                        "stream": {
                            "namespace": "voting-app",
                            "pod": "result-6bb5cdc67f-vs22g",
                            "container": "result",
                        },
                        "values": [
                            [
                                "1794569372344092162",
                                "error: terminating connection due to administrator command",
                            ],
                        ],
                    }
                ]
            }
        }
    }

    context = IncidentContext(
        incident=incident,
        evidence={
            "loki": real_loki_response,
        },
        collection_status=EvidenceCollectionStatus(
            prometheus="success",
            loki="success",
            kubernetes="success",
        ),
        collected_at=now,
    )

    findings = detect_loki_issues(context)

    assert len(findings) == 1

    finding = findings[0]

    assert finding.rule_id == "APPLICATION_ERROR"
    assert finding.category == "application_error"
    assert finding.title == "Application error detected"
    assert finding.severity == "high"
    assert finding.confidence == 0.90

    assert "terminating connection" in finding.description

    assert finding.evidence_refs == [
        "loki.logs.result-6bb5cdc67f-vs22g.result"
    ]
