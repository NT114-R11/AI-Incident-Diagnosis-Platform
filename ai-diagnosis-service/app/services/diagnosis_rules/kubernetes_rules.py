from app.schemas.diagnosis import DiagnosisFinding
from app.schemas.incident_context import IncidentContext

def detect_pod_crash_loop(context: IncidentContext) -> list[DiagnosisFinding]:
    incident = context.incident

    kubernetes = context.evidence.get("kubernetes", {})
    pods = kubernetes.get("pods", [])

    findings = []

    for pod in pods:
        if pod.get("namespace") != incident.namespace:
            continue

        if incident.pod and pod.get("name") != incident.pod:
            continue

        for container in pod.get("containers", []):
            state = container.get("state") or {}

            if (
                state.get("type") != "waiting"
                or state.get("reason") != "CrashLoopBackOff"
            ):
                continue

            findings.append(
                DiagnosisFinding(
                    rule_id="POD_CRASH_LOOP",
                    category="pod_crash_loop",
                    title="Pod is in CrashLoopBackOff",
                    description=(
                        f"Container '{container.get('name')}' "
                        f"in Pod '{pod.get('name')}' is in "
                        "CrashLoopBackOff state. "
                        f"Reason: {state.get('message') or 'Not provided'}"
                    ),
                    severity="critical",
                    confidence=0.95,
                    evidence_refs=[
                        f"kubernetes.pods.{pod.get('name')}"
                    ],
                )
            )

    return findings


def detect_pod_oom_killed(context: IncidentContext) -> list[DiagnosisFinding]:
    incident = context.incident

    kubernetes = context.evidence.get("kubernetes", {})
    pods = kubernetes.get("pods", [])

    findings = []

    for pod in pods:
        if pod.get("namespace") != incident.namespace:
            continue

        if incident.pod and pod.get("name") != incident.pod:
            continue

        for container in pod.get("containers", []):
            states = [
                container.get("state") or {},
                container.get("last_state") or {},
            ]

            oom_state = next(
                (
                    state
                    for state in states
                    if state.get("type") == "terminated"
                    and state.get("reason") == "OOMKilled"
                ),
                None,
            )

            if oom_state is None:
                continue

            findings.append(
                DiagnosisFinding(
                    rule_id="POD_OOM_KILLED",
                    category="oom_killed",
                    title="Container was terminated by OOM Killer",
                    description=(
                        f"Container '{container.get('name')}' "
                        f"in Pod '{pod.get('name')}' was terminated "
                        "because it exceeded its memory limit. "
                        f"Exit code: {oom_state.get('exit_code')}"
                    ),
                    severity="critical",
                    confidence=0.99,
                    evidence_refs=[
                        f"kubernetes.pods.{pod.get('name')}"
                    ],
                )
            )

    return findings

def detect_pod_not_ready(context: IncidentContext) -> list[DiagnosisFinding]:
    incident = context.incident

    kubernetes = context.evidence.get("kubernetes", {})
    pods = kubernetes.get("pods", [])

    findings = []

    for pod in pods:
        if pod.get("namespace") != incident.namespace:
            continue

        if incident.pod and pod.get("name") != incident.pod:
            continue

        ready_condition = next(
            (
                condition
                for condition in pod.get("conditions", [])
                if condition.get("type") == "Ready"
            ),
            None,
        )

        if ready_condition is None:
            continue

        if ready_condition.get("status") != "False":
            continue

        findings.append(
            DiagnosisFinding(
                rule_id="POD_NOT_READY",
                category="pod_not_ready",
                title="Pod is not Ready",
                description=(
                    f"Pod '{pod.get('name')}' is not Ready. "
                    f"Reason: {ready_condition.get('reason') or 'Not provided'}. "
                    f"Message: {ready_condition.get('message') or 'Not provided'}"
                ),
                severity="high",
                confidence=0.95,
                evidence_refs=[
                    f"kubernetes.pods.{pod.get('name')}.conditions"
                ],
            )
        )

    return findings

def detect_kubernetes_issues(context: IncidentContext) -> list[DiagnosisFinding]:
    findings = []

    findings.extend(detect_pod_crash_loop(context))
    findings.extend(detect_pod_oom_killed(context))
    findings.extend(detect_pod_not_ready(context))

    return findings