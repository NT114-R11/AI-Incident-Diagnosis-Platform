from pydantic import BaseModel, ConfigDict

from app.schemas.diagnosis import DiagnosisResult
from app.schemas.incident_context import IncidentContext
from app.schemas.ai_diagnosis import AIDiagnosis


class DiagnosisAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnosis: DiagnosisResult
    context: IncidentContext
    ai_diagnosis: AIDiagnosis | None = None