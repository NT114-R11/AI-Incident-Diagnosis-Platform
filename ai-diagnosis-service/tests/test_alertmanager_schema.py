from datetime import datetime, timezone
from app.schemas.alertmanager import AlertmanagerWebhook


def valid_payload():
    return {
        "version": "4",
        "groupKey": "{}:{alertname=\"PodCrashLooping\"}",
        "status": "firing",
        "receiver": "ai-diagnosis",
        "groupLabels": {
            "alertname": "PodCrashLooping",
        },
        "commonLabels": {
            "alertname": "PodCrashLooping",
            "namespace": "voting-app",
            "pod": "vote-7d9f8b6c5-x2k4p",
            "severity": "critical",
        },
        "commonAnnotations": {
            "summary": "Pod is restarting frequently",
            "description": "Pod has restarted multiple times.",
        },
        "externalURL": "http://alertmanager:9093",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "PodCrashLooping",
                    "namespace": "voting-app",
                    "pod": "vote-7d9f8b6c5-x2k4p",
                    "container": "vote",
                    "job": "kube-state-metrics",
                    "severity": "critical",
                },
                "annotations": {
                    "summary": "Pod is restarting frequently",
                    "description": "Pod has restarted multiple times.",
                },
                "startsAt": "2026-11-07T10:00:00Z",
                "endsAt": "0001-01-01T00:00:00Z",
                "generatorURL": "http://prometheus:9090/graph",
                "fingerprint": "abc123def456",
            }
        ],
        "truncatedAlerts": 0,
    }


def test_valid_alertmanager_payload():
    payload = AlertmanagerWebhook.model_validate(valid_payload())

    assert payload.status == "firing"
    assert len(payload.alerts) == 1
    assert payload.alerts[0].fingerprint == "abc123def456"


def test_unknown_labels_are_accepted():
    data = valid_payload()
    data["alerts"][0]["labels"]["custom_label"] = "custom_value"

    payload = AlertmanagerWebhook.model_validate(data)

    assert payload.alerts[0].labels["custom_label"] == "custom_value"


def test_unknown_root_fields_are_ignored():
    data = valid_payload()
    data["new_alertmanager_field"] = "some_value"

    payload = AlertmanagerWebhook.model_validate(data)

    assert not hasattr(payload, "new_alertmanager_field")


def test_default_ends_at_becomes_none():
    payload = AlertmanagerWebhook.model_validate(valid_payload())

    assert payload.alerts[0].endsAt is None


def test_multiple_alerts_are_supported():
    data = valid_payload()
    second_alert = data["alerts"][0].copy()
    second_alert["fingerprint"] = "second-fingerprint"

    data["alerts"].append(second_alert)

    payload = AlertmanagerWebhook.model_validate(data)

    assert len(payload.alerts) == 2


def test_truncated_alerts_defaults_to_zero():
    data = valid_payload()
    del data["truncatedAlerts"]

    payload = AlertmanagerWebhook.model_validate(data)

    assert payload.truncatedAlerts == 0


def test_resolved_alert_is_supported():
    data = valid_payload()
    data["status"] = "resolved"
    data["alerts"][0]["status"] = "resolved"
    data["alerts"][0]["endsAt"] = "2026-11-07T10:05:00Z"

    payload = AlertmanagerWebhook.model_validate(data)

    assert payload.alerts[0].status == "resolved"
    assert payload.alerts[0].endsAt is not None
def test_starts_at_must_be_timezone_aware():
    data = valid_payload()
    data["alerts"][0]["startsAt"] = "2026-11-07T10:00:00"

    from pydantic import ValidationError
    import pytest

    with pytest.raises(ValidationError):
        AlertmanagerWebhook.model_validate(data)


def test_fingerprint_is_required():
    data = valid_payload()
    del data["alerts"][0]["fingerprint"]

    from pydantic import ValidationError
    import pytest

    with pytest.raises(ValidationError):
        AlertmanagerWebhook.model_validate(data)


def test_ends_at_with_fractional_seconds_is_normalized():
    data = valid_payload()
    data["alerts"][0]["endsAt"] = "0001-01-01T00:00:00.000Z"

    payload = AlertmanagerWebhook.model_validate(data)

    assert payload.alerts[0].endsAt is None