from app.collectors.loki.queries import (
    NAMESPACE,
    ALL_LOGS_QUERY,
    ERROR_LOGS_QUERY,
    WARNING_LOGS_QUERY,
    pod_logs_query,
    container_logs_query,
)


def test_namespace():
    assert NAMESPACE == "voting-app"


def test_all_logs_query():
    assert '{namespace="voting-app"}' in ALL_LOGS_QUERY


def test_error_logs_query():
    assert '{namespace="voting-app"}' in ERROR_LOGS_QUERY
    assert "exception" in ERROR_LOGS_QUERY
    assert "traceback" in ERROR_LOGS_QUERY


def test_warning_logs_query():
    assert '{namespace="voting-app"}' in WARNING_LOGS_QUERY
    assert "warning" in WARNING_LOGS_QUERY


def test_pod_logs_query():
    query = pod_logs_query("vote-123")

    assert query == '{namespace="voting-app", pod="vote-123"}'


def test_container_logs_query():
    query = container_logs_query("postgres")

    assert query == '{namespace="voting-app", container="postgres"}'
