import json
from pathlib import Path

from models import (
    RemediationRequest,
    ApprovalDecision,
    ApprovedAction,
    ExecutionResult,
)

SCHEMAS_DIR = Path(__file__).parent / "schemas"
SCHEMAS_DIR.mkdir(exist_ok=True)

schemas = {
    "remediation-request.schema.json": RemediationRequest,
    "approval-decision.schema.json": ApprovalDecision,
    "approved-action.schema.json": ApprovedAction,
    "execution-result.schema.json": ExecutionResult,
}

for filename, model in schemas.items():
    schema = model.model_json_schema()

    output_path = SCHEMAS_DIR / filename
    output_path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Generated: {output_path}")
