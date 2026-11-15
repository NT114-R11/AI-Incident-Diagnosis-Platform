from datetime import datetime, timezone

from app.schemas.evidence_validation import ( EvidenceSource, EvidenceValidationResult)
from app.schemas.incident_context import IncidentContext

from app.services.evidence_validators.common import (latest_timestamp, parse_datetime)
from app.services.evidence_validators.prometheus_validator import (validate_prometheus)
from app.services.evidence_validators.loki_validator import (validate_loki)
from app.services.evidence_validators.kubernetes_validator import (validate_kubernetes)


class EvidenceValidator:
    SOURCES: tuple[EvidenceSource, ...] = (
        "prometheus",
        "loki",
        "kubernetes",
    )

    def validate(
        self,
        context: IncidentContext,
    ) -> EvidenceValidationResult:
        available_sources = []
        unavailable_sources = []
        matched_sources = []
        warnings = []

        # 1. Check evidence collection status.
        for source in self.SOURCES:
            status = getattr(context.collection_status, source)

            if status == "success":
                available_sources.append(source)
            else:
                unavailable_sources.append(source)
                warnings.append(
                    f"{source.capitalize()} evidence collection failed."
                )

        # 2. Determine incident timestamp.
        incident = context.incident

        first_seen = parse_datetime(incident.first_seen_at)
        last_seen = parse_datetime(incident.last_seen_at)

        invalid_time_range = (
            first_seen is not None
            and last_seen is not None
            and last_seen < first_seen
        )

        if invalid_time_range:
            warnings.append("invalid_incident_time_range")
            incident_time = None
        else:
            incident_time = latest_timestamp(first_seen, last_seen)

        if incident_time is None and not invalid_time_range:
            warnings.append("missing_incident_timestamp")

        # 3. Validate evidence from each available source.
        evidence = context.evidence

        validators = {
            "prometheus": validate_prometheus,
            "loki": validate_loki,
            "kubernetes": validate_kubernetes,
        }

        for source in self.SOURCES:
            if source not in available_sources:
                continue

            is_valid = validators[source](
                evidence.get(source, {}),
                incident.namespace,
                incident.pod,
                incident_time,
            )

            if is_valid:
                matched_sources.append(source)
            else:
                warnings.append(
                    f"No relevant {source.capitalize()} evidence found."
                )

        # 4. Return validation result.
        return EvidenceValidationResult(
            is_sufficient=bool(matched_sources),
            available_sources=available_sources,
            unavailable_sources=unavailable_sources,
            matched_sources=matched_sources,
            warnings=warnings,
            validated_at=datetime.now(timezone.utc),
        )

"""
- Validator chỉ kiểm tra evidence có liên quan về namespace, Pod và thời gian.
- Nó chưa xác định nguyên nhân sự cố.
- is_sufficient=True nghĩa là có ít nhất một evidence phù hợp, không có nghĩa đã đủ bằng chứng để kết luận một nguyên nhân cụ thể.
- Kubernetes Pod snapshot chỉ được sử dụng khi thời điểm thu thập đủ gần incident.
- Warning Event phải có timestamp hợp lệ và khớp đối tượng.
- Incident có timestamp đảo ngược sẽ được ghi warning; validator không tự sửa dữ liệu gốc.
Một giới hạn cần nhớ: Collector hiện chỉ truy vấn namespace voting-app. Vì vậy, khi incident không có namespace và Pod,
 validator không thể biến dữ liệu giới hạn đó thành bằng chứng toàn cluster. 
 Phạm vi chẩn đoán vẫn phải giới hạn theo những gì Collector thực sự thu thập.
"""