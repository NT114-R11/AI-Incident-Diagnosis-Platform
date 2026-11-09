NAMESPACE = "voting-app"

ALL_LOGS_QUERY = """
{namespace="voting-app"}
"""

ERROR_LOGS_QUERY = """
{namespace="voting-app"} |~ "(?i)(error:|exception|failed|failure|fatal|panic|traceback)"
"""

WARNING_LOGS_QUERY = """
{namespace="voting-app"} |~ "(?i)(warn|warning)"
"""


def pod_logs_query(pod: str) -> str:
    return f'{{namespace="{NAMESPACE}", pod="{pod}"}}'


def container_logs_query(container: str) -> str:
    return f'{{namespace="{NAMESPACE}", container="{container}"}}'
