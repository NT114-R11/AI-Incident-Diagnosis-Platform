import json

from app.schemas.diagnosis_analysis import DiagnosisAnalysis


class DiagnosisPromptBuilder:
    SYSTEM_INSTRUCTION = """
You are an AI assistant specialized in diagnosing incidents
in Kubernetes-based containerized infrastructure.

Your task is to analyze incident context, observability evidence,
and rule-based diagnosis results.

Rules:
1. Use only the evidence provided in the input.
2. Never invent metrics, logs, Kubernetes events, or system states.
3. Treat unavailable or failed evidence sources as unknown,
   not as evidence that the system is healthy.
4. Distinguish observed facts from hypotheses.
5. Consider rule-based findings as supporting information,
   not unquestionable truth.
6. If evidence is insufficient, explicitly state the uncertainty.
7. Do not claim that an investigation command has been executed.
8. Suggest read-only investigation steps only.
9. Never suggest destructive operations or automatic remediation.
10. Return a valid JSON object matching the requested schema.

Your response must contain:
- status: success
- probable_cause: most likely explanation, or null
- explanation: concise reasoning based on evidence
- confidence: number between 0 and 1
- supporting_evidence: list of evidence references
- investigation_steps: list of suggested read-only investigation steps
"""

    @classmethod
    def build(cls, analysis: DiagnosisAnalysis) -> str:
        payload = {
            "incident": analysis.context.incident.model_dump(mode="json"),
            "evidence": analysis.context.evidence,
            "collection_status": (
                analysis.context.collection_status.model_dump()
            ),
            "collected_at": (
                analysis.context.collected_at.isoformat()
            ),
            "rule_based_diagnosis": (
                analysis.diagnosis.model_dump(mode="json")
            ),
        }

        return (
            f"{cls.SYSTEM_INSTRUCTION}\n\n"
            "Analyze the following incident data:\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2, default=str)}"
        )
