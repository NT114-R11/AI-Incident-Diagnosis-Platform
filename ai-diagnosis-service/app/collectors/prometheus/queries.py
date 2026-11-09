
# Resource usage
CPU_USAGE_QUERY = """
rate(container_cpu_usage_seconds_total{
    namespace="voting-app",
    container!=""
}[5m])
"""

MEMORY_USAGE_QUERY = """
container_memory_working_set_bytes{
    namespace="voting-app",
    container!=""
}
"""

# Kubernetes container status
CONTAINER_RESTARTS_QUERY = """
kube_pod_container_status_restarts_total{
    namespace="voting-app"
}
"""

POD_PHASE_QUERY = """
kube_pod_status_phase{
    namespace="voting-app"
} == 1
"""

CONTAINER_WAITING_QUERY = """
kube_pod_container_status_waiting_reason{
    namespace="voting-app"
}
"""
