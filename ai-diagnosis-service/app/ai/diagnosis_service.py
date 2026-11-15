import logging
from google.genai import errors
from pydantic import ValidationError
from app.ai.model_manager import ModelManager
from app.ai.prompts.diagnosis_prompt import DiagnosisPromptBuilder
from app.schemas.ai_diagnosis import AIDiagnosis
from app.schemas.diagnosis_analysis import DiagnosisAnalysis


logger = logging.getLogger(__name__)


class AIDiagnosisService:
    def __init__(self, model_manager: ModelManager | None = None):
        self.model_manager = model_manager or ModelManager()

    async def diagnose(self, analysis: DiagnosisAnalysis) -> AIDiagnosis:
        # Build prompt from the existing evidence snapshot.
        prompt = DiagnosisPromptBuilder.build(analysis)

        try:
            result = await self.model_manager.generate(
                prompt,
                response_schema=AIDiagnosis,
            )

            if not isinstance(result, AIDiagnosis):
                raise TypeError(
                    "ModelManager returned an unexpected response type"
                )

            if result.status != "success":
                raise ValueError(
                    "AI model returned an invalid diagnosis status"
                )

            return result

        except (
            errors.APIError,
            TimeoutError,
            ConnectionError,
            OSError,
            RuntimeError,
            ValidationError,
            ValueError,
        ):
            logger.exception(
                "AI diagnosis failed for incident %s",
                analysis.context.incident.id,
            )

            return AIDiagnosis(
                status="unavailable",
                probable_cause=None,
                explanation=None,
                confidence=None,
                supporting_evidence=[],
                investigation_steps=[],
            )
