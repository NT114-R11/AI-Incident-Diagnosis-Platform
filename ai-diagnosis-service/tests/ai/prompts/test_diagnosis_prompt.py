
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.ai.prompts.diagnosis_prompt import DiagnosisPromptBuilder


def test_build_includes_incident_and_evidence():
    incident_id = uuid4()

    analysis = SimpleNamespace(
        context=SimpleNamespace(
            incident=SimpleNamespace(
                model_dump=lambda **kwargs: {
                    "id": str(incident_id),
                    "alert_name": "PodCrashLoopBackOff",
                    "namespace": "ecommerce",
                    "pod": "order-service-123",
                }
            ),
            evidence={
                "kubernetes": {
                    "pod_phase": "Running",
                    "container_reason": "CrashLoopBackOff",
                },
                "loki": {
                    "errors": ["Database connection failed"]
                },
            },
            collection_status=SimpleNamespace(
                model_dump=lambda: {
                    "prometheus": "failed",
                    "loki": "success",
                    "kubernetes": "success",
                }
            ),
            collected_at=datetime.now(timezone.utc),
        ),
        diagnosis=SimpleNamespace(
            model_dump=lambda **kwargs: {
                "status": "diagnosed",
                "probable_cause": "Container repeatedly crashes",
                "findings": [],
            }
        ),
    )

    prompt = DiagnosisPromptBuilder.build(analysis)

    assert "PodCrashLoopBackOff" in prompt
    assert "CrashLoopBackOff" in prompt
    assert "Database connection failed" in prompt
    assert "prometheus" in prompt
    assert "failed" in prompt


def test_build_returns_valid_json_payload():
    analysis = SimpleNamespace(
        context=SimpleNamespace(
            incident=SimpleNamespace(
                model_dump=lambda **kwargs: {"alert_name": "TestAlert"}
            ),
            evidence={"kubernetes": {"pods": []}},
            collection_status=SimpleNamespace(
                model_dump=lambda: {
                    "prometheus": "success",
                    "loki": "success",
                    "kubernetes": "success",
                }
            ),
            collected_at=datetime.now(timezone.utc),
        ),
        diagnosis=SimpleNamespace(
            model_dump=lambda **kwargs: {
                "status": "no_issue_detected",
                "findings": [],
            }
        ),
    )

    prompt = DiagnosisPromptBuilder.build(analysis)

    marker = "Analyze the following incident data:\n"
    payload = prompt.split(marker, 1)[1]

    parsed = json.loads(payload)

    assert parsed["incident"]["alert_name"] == "TestAlert"
    assert parsed["evidence"]["kubernetes"]["pods"] == []
    assert parsed["collection_status"]["prometheus"] == "success"
    assert parsed["rule_based_diagnosis"]["status"] == "no_issue_detected"
