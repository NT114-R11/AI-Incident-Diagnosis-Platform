
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.evidence_validation import EvidenceValidationResult


@pytest.fixture
def valid_data():
    return {
        "is_sufficient": True,
        "available_sources": ["loki", "kubernetes"],
        "unavailable_sources": ["prometheus"],
        "warnings": ["Prometheus evidence is unavailable."],
        "validated_at": datetime.now(timezone.utc),
    }


def test_create_valid_result(valid_data):
    result = EvidenceValidationResult(**valid_data)

    assert result.is_sufficient is True
    assert result.available_sources == ["loki", "kubernetes"]
    assert result.unavailable_sources == ["prometheus"]


def test_allow_empty_source_lists():
    result = EvidenceValidationResult(
        is_sufficient=False,
        validated_at=datetime.now(timezone.utc),
    )

    assert result.available_sources == []
    assert result.unavailable_sources == []
    assert result.warnings == []


def test_reject_invalid_source(valid_data):
    valid_data["available_sources"] = ["unknown"]

    with pytest.raises(ValidationError):
        EvidenceValidationResult(**valid_data)


def test_reject_unexpected_field(valid_data):
    valid_data["unexpected"] = "value"

    with pytest.raises(ValidationError):
        EvidenceValidationResult(**valid_data)


def test_reject_invalid_validated_at(valid_data):
    valid_data["validated_at"] = "not-a-datetime"

    with pytest.raises(ValidationError):
        EvidenceValidationResult(**valid_data)
