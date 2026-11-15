
import asyncio
from datetime import datetime, timezone
from typing import Any

from app.collectors.kubernetes.client import KubernetesClient


class KubernetesCollector:
    def __init__(
        self,
        namespace: str = "voting-app",
        client: KubernetesClient | None = None,
    ):
        self.namespace = namespace
        self.client = client or KubernetesClient()

    async def collect(self) -> dict[str, Any]:
        pods, events, deployments = await asyncio.gather(
            asyncio.to_thread(
                self.client.list_pods,
                self.namespace,
            ),
            asyncio.to_thread(
                self.client.list_events,
                self.namespace,
            ),
            asyncio.to_thread(
                self.client.list_deployments,
                self.namespace,
            ),
        )

        return {
            "source": "kubernetes",
            "namespace": self.namespace,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "pods": self._collect_pods(pods.items),
            "events": self._collect_events(events.items),
            "deployments": self._collect_deployments(
                deployments.items
            ),
        }

    @staticmethod
    def _collect_pods(pods: list) -> list[dict[str, Any]]:
        results = []

        for pod in pods:
            pod_data = {
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "node": pod.spec.node_name,
                "phase": pod.status.phase,
                "labels": pod.metadata.labels or {},
                "conditions": [],
                "containers": [],
            }

            for condition in pod.status.conditions or []:
                pod_data["conditions"].append({
                    "type": condition.type,
                    "status": condition.status,
                    "reason": condition.reason,
                    "message": condition.message,
                })

            container_statuses = (
                pod.status.container_statuses or []
            )

            for container in container_statuses:
                state = None

                if container.state.waiting:
                    state = {
                        "type": "waiting",
                        "reason": container.state.waiting.reason,
                        "message": container.state.waiting.message,
                    }
                elif container.state.running:
                    state = {
                        "type": "running",
                        "started_at": (
                            container.state.running.started_at.isoformat()
                            if container.state.running.started_at
                            else None
                        ),
                    }
                elif container.state.terminated:
                    state = {
                        "type": "terminated",
                        "reason": container.state.terminated.reason,
                        "message": container.state.terminated.message,
                        "exit_code": container.state.terminated.exit_code,
                    }
                last_state = None

                if container.last_state.terminated:
                    last_state = {
                        "type": "terminated",
                        "reason": container.last_state.terminated.reason,
                        "message": container.last_state.terminated.message,
                        "exit_code": container.last_state.terminated.exit_code,
                    }
                elif container.last_state.waiting:
                    last_state = {
                        "type": "waiting",
                        "reason": container.last_state.waiting.reason,
                        "message": container.last_state.waiting.message,
                    }
                elif container.last_state.running:
                    last_state = {
                        "type": "running",
                        "started_at": (
                            container.last_state.running.started_at.isoformat()
                            if container.last_state.running.started_at
                            else None
                        ),
                    }


                pod_data["containers"].append({
                    "name": container.name,
                    "ready": container.ready,
                    "restart_count": container.restart_count,
                    "state": state,
                    "last_state": last_state,
                })

            results.append(pod_data)

        return results

    @staticmethod
    def _collect_events(events: list) -> list[dict[str, Any]]:
        results = []

        for event in events:
            if event.type != "Warning":
                continue

            results.append({
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "count": event.count,
                "namespace": event.metadata.namespace,
                "involved_object": {
                    "kind": event.involved_object.kind,
                    "name": event.involved_object.name,
                },
                "first_timestamp": (
                    event.first_timestamp.isoformat()
                    if event.first_timestamp
                    else None
                ),
                "last_timestamp": (
                    event.last_timestamp.isoformat()
                    if event.last_timestamp
                    else None
                ),
            })

        return results

    @staticmethod
    def _collect_deployments(
        deployments: list,
    ) -> list[dict[str, Any]]:
        results = []

        for deployment in deployments:
            spec = deployment.spec
            status = deployment.status

            results.append({
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace,
                "desired_replicas": spec.replicas or 0,
                "ready_replicas": status.ready_replicas or 0,
                "available_replicas": status.available_replicas or 0,
                "updated_replicas": status.updated_replicas or 0,
            })

        return results
