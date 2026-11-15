from datetime import datetime, timezone
from app.schemas.diagnosis_analysis import DiagnosisAnalysis
from app.services.evidence_validator import EvidenceValidator
from app.services.incident_context_service import IncidentContextService
from app.services.diagnosis_rules.kubernetes_rules import (detect_kubernetes_issues)
from app.services.diagnosis_rules.prometheus_rules import (detect_prometheus_issues)
from app.services.diagnosis_rules.loki_rules import (detect_loki_issues)
from app.schemas.diagnosis import DiagnosisResult
from app.ai.diagnosis_service import AIDiagnosisService

class DiagnosisService:
    def __init__(
        self,
        context_service: IncidentContextService | None = None,
        evidence_validator: EvidenceValidator | None = None,
        ai_diagnosis_service: AIDiagnosisService | None = None):

        self.context_service = (context_service or IncidentContextService())
        self.evidence_validator = (evidence_validator or EvidenceValidator())
        self.ai_diagnosis_service = ai_diagnosis_service


    async def diagnose(self, incident) -> DiagnosisResult:
        analysis = await self.diagnose_with_context(incident)
        return analysis.diagnosis

    async def diagnose_with_context(self,incident) -> DiagnosisAnalysis:
        # 1. Collect evidence exactly once
        context = await self.context_service.collect(incident)

        # 2. Run rule-based diagnosis
        diagnosis = self._diagnose_context(incident=incident, context=context)

        # 3. Build analysis using the collected evidence
        analysis = DiagnosisAnalysis(diagnosis=diagnosis, context=context)

        # 4. Run AI using the same analysis
        if self.ai_diagnosis_service is not None:
            ai_diagnosis = await self.ai_diagnosis_service.diagnose(analysis)

            analysis.ai_diagnosis = ai_diagnosis

        return analysis

    def _diagnose_context(self, incident, context ) -> DiagnosisResult:
        # 1. Validate evidence
        validation = self.evidence_validator.validate(context)

        # 2. Stop if evidence is insufficient
        if not validation.is_sufficient:
            warning_details = "; ".join(validation.warnings)

            summary = (
                "Insufficient evidence to diagnose this incident."
            )

            if warning_details:
                summary += f" Warnings: {warning_details}"

            return DiagnosisResult(
                incident_id=incident.id,
                status="insufficient_evidence",
                analyzed_at=datetime.now(timezone.utc),
                probable_cause=None,
                confidence=0.0,
                severity=None,
                summary=summary,
                findings=[],
                evidence_refs=[],
            )

        # 3. Run diagnosis rules based on matched evidence sources
        findings = []

        if "kubernetes" in validation.matched_sources:
            findings.extend(
                detect_kubernetes_issues(context)
            )

        if "prometheus" in validation.matched_sources:
            findings.extend(
                detect_prometheus_issues(context)
            )

        if "loki" in validation.matched_sources:
            findings.extend(
                detect_loki_issues(context)
            )

        # 4. Return when no known issue is detected
        if not findings:
            return DiagnosisResult(
                incident_id=incident.id,
                status="no_issue_detected",
                analyzed_at=datetime.now(timezone.utc),
                probable_cause=None,
                confidence=0.0,
                severity=None,
                summary=(
                    "No issue was detected by the available "
                    "diagnosis rules."
                ),
                findings=[],
                evidence_refs=[],
            )

        # 5. Aggregate diagnosis findings
        severity_order = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4,
        }

        highest_severity = max(
            findings,
            key=lambda finding: severity_order[finding.severity],
        ).severity

        evidence_refs = list(dict.fromkeys(
            ref
            for finding in findings
            for ref in finding.evidence_refs
        ))

        return DiagnosisResult(
            incident_id=incident.id,
            status="diagnosed",
            analyzed_at=datetime.now(timezone.utc),
            probable_cause=findings[0].title,
            confidence=max(
                finding.confidence for finding in findings
            ),
            severity=highest_severity,
            summary=f"Detected {len(findings)} issue(s).",
            findings=findings,
            evidence_refs=evidence_refs,
        )

    # async def diagnose(self, incident) -> DiagnosisResult:
    #     # 1. Collect evidence
    #     context = await self.context_service.collect(incident)

    #     # 2. Validate evidence
    #     validation = self.evidence_validator.validate(context)

    #     # 3. Stop if evidence is insufficient
    #     if not validation.is_sufficient:
    #         warning_details = "; ".join(validation.warnings)

    #         summary = (
    #             "Insufficient evidence to diagnose this incident."
    #         )

    #         if warning_details:
    #             summary += f" Warnings: {warning_details}"

    #         return DiagnosisResult(
    #             incident_id=incident.id,
    #             status="insufficient_evidence",
    #             analyzed_at=datetime.now(timezone.utc),
    #             probable_cause=None,
    #             confidence=0.0,
    #             severity=None,
    #             summary=summary,
    #             findings=[],
    #             evidence_refs=[],
    #         )

    #     # 4. Run diagnosis rules based on matched evidence sources
    #     findings = []

    #     if "kubernetes" in validation.matched_sources:
    #         findings.extend(
    #             detect_kubernetes_issues(context))

    #     if "prometheus" in validation.matched_sources:
    #         findings.extend(
    #             detect_prometheus_issues(context))

    #     if "loki" in validation.matched_sources:
    #         findings.extend(detect_loki_issues(context))

    #     # 5. Return when no known issue is detected
    #     if not findings:
    #         return DiagnosisResult(
    #             incident_id=incident.id,
    #             status="no_issue_detected",
    #             analyzed_at=datetime.now(timezone.utc),
    #             probable_cause=None,
    #             confidence=0.0,
    #             severity=None,
    #             summary=(
    #                 "No issue was detected by the available "
    #                 "diagnosis rules."
    #             ),
    #             findings=[],
    #             evidence_refs=[],
    #         )

    #     # 6. Aggregate diagnosis findings
    #     severity_order = {
    #         "low": 1,
    #         "medium": 2,
    #         "high": 3,
    #         "critical": 4,
    #     }

    #     highest_severity = max(
    #         findings,
    #         key=lambda finding: severity_order[finding.severity],
    #     ).severity

    #     evidence_refs = list(dict.fromkeys(
    #         ref
    #         for finding in findings
    #         for ref in finding.evidence_refs
    #     ))

    #     return DiagnosisResult(
    #         incident_id=incident.id,
    #         status="diagnosed",
    #         analyzed_at=datetime.now(timezone.utc),
    #         probable_cause=findings[0].title,
    #         confidence=max(
    #             finding.confidence for finding in findings
    #         ),
    #         severity=highest_severity,
    #         summary=f"Detected {len(findings)} issue(s).",
    #         findings=findings,
    #         evidence_refs=evidence_refs,
    #     )
