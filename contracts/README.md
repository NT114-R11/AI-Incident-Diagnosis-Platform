# Incident Platform Contracts

**Version:** 1.0.0

## 1. Overview

This package defines the shared data contracts used for communication between the AI Diagnosis Service, Telegram Approval Handler, and Remediation Executor.

The contracts establish a consistent data format, validation rules, and service boundaries across the platform.

## 2. Architecture

The remediation workflow follows this sequence:

1. AI Diagnosis Service creates a `RemediationRequest`.
2. Telegram Approval Handler presents the proposed remediation to a manager.
3. Manager approves or rejects the request.
4. Telegram Approval Handler sends an `ApprovalDecision`.
5. AI Diagnosis Service validates the decision and creates an `ApprovedAction`.
6. Remediation Executor validates and executes the approved action.
7. Remediation Executor returns an `ExecutionResult`.
8. AI Diagnosis Service independently verifies whether the incident has been resolved.

## 3. Contracts

| Contract | Producer | Consumer | Purpose |
|---|---|---|---|
| RemediationRequest | AI Diagnosis Service | Telegram Approval Handler | Propose a remediation |
| ApprovalDecision | Telegram Approval Handler | AI Diagnosis Service | Communicate manager decision |
| ApprovedAction | AI Diagnosis Service | Remediation Executor | Request an approved operation |
| ExecutionResult | Remediation Executor | AI Diagnosis Service | Report execution outcome |

### 3.1 RemediationRequest

Contains:
- Request and incident identifiers
- Incident metadata
- Diagnosis information
- Evidence references
- Proposed remediation action
- Request expiration time

### 3.2 ApprovalDecision

Contains:
- Decision, request, incident and action identifiers
- Approval or rejection status
- Approver information
- Decision timestamp
- Approval token reference

Only authorized managers can approve or reject remediation requests.

### 3.3 ApprovedAction

Contains:
- Execution and incident identifiers
- Approval metadata
- Allowlisted action and parameters
- Execution timeout policy
- Issue and expiration timestamps

The Executor must independently validate the action and enforce its execution policy.

### 3.4 ExecutionResult

Contains:
- Execution and incident identifiers
- Execution status
- Target resource
- Execution timestamps
- Result details
- Audit information

Execution success does not guarantee incident resolution. Incident verification belongs to the AI Diagnosis Service.

## 4. Security Principles

- AI Diagnosis Service has read-only Kubernetes access.
- Telegram Approval Handler does not have Kubernetes execution credentials.
- Remediation Executor has restricted Kubernetes permissions.
- LLM-generated arbitrary shell commands are never executed.
- Only allowlisted remediation actions are accepted.
- Approval decisions must be authenticated, time-limited, and bound to the original request and action.
- Execution requests must be protected against replay and duplicate execution.
- All remediation operations must be auditable.

## 5. Technology Stack

- Python 3.12+
- Pydantic v2
- JSON Schema
- pytest

## 6. Project Structure

```text
contracts/
├── schemas/
│   ├── remediation-request.schema.json
│   ├── approval-decision.schema.json
│   ├── approved-action.schema.json
│   └── execution-result.schema.json
├── models/
│   ├── remediation_request.py
│   ├── approval_decision.py
│   ├── approved_action.py
│   └── execution_result.py
├── tests/
├── pyproject.toml
└── README.md
```

## 7. Development

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

## 8. JSON Schema Generation

JSON Schemas are generated from Pydantic models.

Regenerate schemas whenever the models change to keep both representations synchronized.

## 9. Scope and Limitations

Version 1.0 initially supports the `restart_deployment` remediation action.

The contracts validate data structure and local consistency. Authentication, authorization, approval-token verification, replay prevention, Kubernetes permissions, and incident-state validation must be enforced by the respective services.

## 10. Versioning

The package uses semantic versioning.

Breaking changes to contract structures or semantics require a new contract version and coordinated updates to consuming services.