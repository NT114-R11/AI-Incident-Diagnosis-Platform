
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException
from kubernetes.client.exceptions import ApiException


class KubernetesAPIError(Exception):
    """Raised when a Kubernetes API request fails."""


class KubernetesClient:
    def __init__(self):
        self._load_configuration()

        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1Api()

    @staticmethod
    def _load_configuration() -> None:
        """Load in-cluster config or local kubeconfig."""
        try:
            config.load_incluster_config()
        except ConfigException:
            try:
                config.load_kube_config()
            except ConfigException as exc:
                raise KubernetesAPIError(
                    "Unable to load Kubernetes configuration"
                ) from exc

    @staticmethod
    def _handle_api_error(exc: ApiException) -> KubernetesAPIError:
        return KubernetesAPIError(
            f"Kubernetes API error: status={exc.status}, "
            f"reason={exc.reason}"
        )

    def list_pods(self, namespace: str):
        try:
            return self.core_api.list_namespaced_pod(
                namespace=namespace
            )
        except ApiException as exc:
            raise self._handle_api_error(exc) from exc

    def list_events(self, namespace: str):
        try:
            return self.core_api.list_namespaced_event(
                namespace=namespace
            )
        except ApiException as exc:
            raise self._handle_api_error(exc) from exc

    def list_deployments(self, namespace: str):
        try:
            return self.apps_api.list_namespaced_deployment(
                namespace=namespace
            )
        except ApiException as exc:
            raise self._handle_api_error(exc) from exc
