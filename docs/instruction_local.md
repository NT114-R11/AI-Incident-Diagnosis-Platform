# Local Environment Setup Guide

## AI Incident Diagnosis Platform

This document describes how to deploy the Voting App and its observability stack on a local Kubernetes cluster using Kind.

## 1. Prerequisites

Required tools:

- Docker
- Kind
- kubectl
- Helm
- Kustomize

Verify installations:

```bash
docker --version
kind version
kubectl version --client
helm version
```

## 2. Create the Kind cluster and bootstrap Kubernetes metrics

Run the bootstrap script from the repository root:

```bash
bash k8s/kind/bootstrap-metrics.sh
```

The script creates the `voting-local` Kind cluster if it does not already exist, then configures the Kubernetes control-plane and kube-proxy metrics endpoints. There is no need to run `kind create cluster` separately.

Verify:

```bash
kind get clusters
kubectl get nodes -o wide
kubectl config current-context
```

Expected cluster name: `voting-local`.

## 3. Install NGINX Ingress Controller

### 3.1. Label the selected worker node

The current cluster uses `voting-local-worker` as the ingress node.

```bash
kubectl label node voting-local-worker ingress-ready=true
kubectl get nodes --show-labels
```

### 3.2. Add the Helm repository

```bash
helm repo add nginx-stable https://helm.nginx.com/stable
helm repo update
```

### 3.3. Install the controller

This project uses the F5 NGINX Ingress Controller chart, not the community `ingress-nginx` chart.

```bash
helm upgrade --install nginx-ingress nginx-stable/nginx-ingress \
  --version 2.8.1 \
  --namespace nginx-ingress \
  --create-namespace \
  -f k8s/kind/nginx-values.yaml \
  --wait \
  --timeout 5m
```

Verify:

```bash
kubectl get pods -n nginx-ingress -o wide
kubectl get ingressclass
```

The controller configuration in `k8s/kind/nginx-values.yaml` should select the worker node labelled `ingress-ready=true`.

## 4. Pull Voting App images

```bash
docker pull ghcr.io/nt114-r11/ai-incident-diagnosis-platform-vote:latest

docker pull ghcr.io/nt114-r11/ai-incident-diagnosis-platform-worker:latest

docker pull ghcr.io/nt114-r11/ai-incident-diagnosis-platform-result:latest

docker pull ghcr.io/nt114-r11/ai-incident-diagnosis-platform-ai-diagnosis-service:latest
```

## 5. Deploy the Voting App

Apply the local Kustomize overlay:

```bash
kubectl apply -k k8s/overlays/local
```

Verify workloads and services:

```bash
kubectl get pods -n voting-app -o wide
kubectl get services -n voting-app
kubectl get ingress -n voting-app
```
- Check domain
```
grep -E 'voting.local|result.voting.local' /etc/hosts
```
Add if no exists
```
echo "127.0.0.1 voting.local result.voting.local" | sudo tee -a /etc/hosts
```

Wait until the application Pods are healthy before installing the monitoring stack.

## 6. Configure Helm repositories

```bash
helm repo add prometheus-community \
  https://prometheus-community.github.io/helm-charts

helm repo add grafana \
  https://grafana.github.io/helm-charts

helm repo add grafana-community \
  https://grafana-community.github.io/helm-charts

helm repo update
```

Inspect available chart versions when necessary:

```bash
helm search repo prometheus-community/kube-prometheus-stack -l | head -10
helm search repo grafana-community/loki -l | head -10
helm search repo grafana/alloy -l | head -10
```

The following pinned versions are used by this local environment:

| Component | Helm chart | Version |
|---|---|---:|
| Prometheus Stack | prometheus-community/kube-prometheus-stack | 92.20.0 |
| Loki | grafana-community/loki | 21.0.0 |
| Alloy | grafana/alloy | 1.15.0 |

## 7. Install Prometheus Stack

```bash
helm upgrade --install prometheus-stack \
  prometheus-community/kube-prometheus-stack \
  --version 92.20.0 \
  --namespace monitoring \
  -f k8s/monitoring/prometheus-stack/values-local.yaml \
  --wait \
  --timeout 10m
```
```
kubectl apply -f k8s/monitoring/prometheus-stack prometheus-rules.yaml 
```
### 7.1. Retrieve the Grafana admin password

```bash
kubectl get secret prometheus-stack-grafana \
  -n monitoring \
  -o jsonpath="{.data.admin-password}" | base64 -d

echo
```

Default username: `admin`.

### 7.2. Local resource configuration

| Component | Persistent storage | Memory limit |
|---|---:|---:|
| Prometheus | 5 GiB | 1 GiB |
| Grafana | 2 GiB | 512 MiB |
| Alertmanager | No dedicated PVC | 256 MiB |

Configuration decisions:

- Prometheus retains metrics for 3 days to limit local storage consumption.
- Grafana uses a PVC to preserve dashboards and configuration.
- Alertmanager retains state for 24 hours. Its state is not persistent across Pod recreation in this local configuration.
- Node Exporter and kube-state-metrics are enabled to collect node and Kubernetes object metrics.
- The `standard` StorageClass is used for dynamic PVC provisioning.

Verify:

```bash
kubectl get pods -n monitoring
kubectl get pvc -n monitoring
kubectl get services -n monitoring
```

## 8. Install Loki

```
kubectl apply -k k8s/monitoring/loki
```
```bash
helm upgrade --install loki \
  grafana-community/loki \
  --version 21.0.0 \
  --namespace monitoring \
  -f k8s/monitoring/loki/values-local.yaml \
  --wait \
  --timeout 10m
```

Configuration decisions:

- Loki runs in Single Binary (Monolithic) mode.
- One Loki replica handles reads and writes.
- Separate read, write and backend workloads are disabled.
- Persistent storage is configured with a 5 GiB PVC.
- Log retention is configured for 72 hours.
- Retention deletion must be verified at runtime; configuring a retention period alone is not sufficient evidence that old data is being deleted.

Loki Gateway endpoint:

```text
http://loki-gateway.monitoring.svc.cluster.local
```

Push endpoint:

```text
http://loki-gateway.monitoring.svc.cluster.local/loki/api/v1/push
```

This local Loki configuration has multi-tenancy enabled. Requests must include the `X-Scope-OrgID` header. The local tenant used by Alloy and Grafana is `fake`.

Verify:

```bash
kubectl get pods -n monitoring
kubectl get pvc -n monitoring
kubectl get services -n monitoring
```

## 9. Install Alloy

Alloy collects Kubernetes Pod logs and forwards them to Loki.

```bash
helm upgrade --install alloy \
  grafana/alloy \
  --version 1.15.0 \
  --namespace monitoring \
  -f k8s/monitoring/alloy/values-local.yaml \
  --wait \
  --timeout 10m
```

### 9.1. Configuration overview

| Configuration | Purpose |
|---|---|
| `controller.type: daemonset` | Runs an Alloy agent on eligible nodes |
| `discovery.kubernetes` | Discovers Kubernetes Pods |
| `loki.source.kubernetes` | Reads Pod logs through the Kubernetes API |
| `stage.cri` | Parses container runtime log format |
| `stage.label_keep` | Retains the selected labels |
| `loki.write` | Sends logs to Loki Gateway |
| RBAC | Grants read-only Kubernetes permissions |

The selected labels are:

- `namespace`
- `pod`
- `container`
- `node`

Alloy uses the following tenant header when writing to Loki:

```river
headers = {
  "X-Scope-OrgID" = "fake",
}
```

The intended collection scope for this project is the `voting-app` namespace. Configure Kubernetes discovery accordingly when restricting collection to that namespace.

### 9.2. Node scheduling consideration

The Kind cluster has three nodes:

- `voting-local-control-plane`
- `voting-local-worker`
- `voting-local-worker2`

The control-plane node has the taint:

```text
node-role.kubernetes.io/control-plane:NoSchedule
```

Therefore, a DaemonSet without a matching toleration runs only on the two worker nodes.

If Alloy must run on all three nodes, configure the appropriate control-plane toleration in the Helm values. Do not remove the control-plane taint just to schedule Alloy.

Verify:

```bash
kubectl get daemonset alloy -n monitoring
kubectl get pods -n monitoring \
  -l app.kubernetes.io/name=alloy -o wide
```

Expected state for each scheduled Alloy Pod:

```text
READY   STATUS
2/2     Running
```
### 9.3 Set up incidents table

```
alembic upgrade head
```
Verify
```
alembic current
```


## 10. Connect Grafana to Loki

Port-forward Grafana:

```bash
kubectl port-forward -n monitoring \
  svc/prometheus-stack-grafana 3000:80
```

Open:

```text
http://localhost:3000
```

Add a Loki datasource with:

| Setting | Value |
|---|---|
| URL | `http://loki-gateway.monitoring.svc.cluster.local` |
| Header | `X-Scope-OrgID` |
| Header value | `fake` |

Test logs in Explore using LogQL:

```logql
{namespace="voting-app"}
```

Logs should appear only after Alloy has successfully collected and pushed them to Loki.

## 11. Operational verification

Check the monitoring workloads:

```bash
kubectl get pods -n monitoring -o wide
kubectl get pvc -n monitoring
kubectl get services -n monitoring
```

Check the application workloads:

```bash
kubectl get pods -n voting-app -o wide
kubectl get services -n voting-app
```

Check Helm releases:

```bash
helm list -n monitoring
helm list -n nginx-ingress
```

Do not consider the observability stack complete solely because Helm reports `STATUS: deployed`. Verify Pod readiness, persistent volumes, Prometheus targets, Alloy log collection and Loki queries.

## 12. Stop the local Kind cluster

To stop all containers belonging to the `voting-local` Kind cluster:

```bash
docker stop $(docker ps -q \
  --filter "label=io.x-k8s.kind.cluster=voting-local")
```

This stops the cluster containers but does not delete the Kind cluster.

To start it again:

```bash
docker start $(docker ps -aq \
  --filter "label=io.x-k8s.kind.cluster=voting-local")
```

Verify:

```bash
kubectl get nodes
```

To permanently delete the cluster instead:

```bash
kind delete cluster --name voting-local
```

**Warning:** Deleting the cluster removes its Kubernetes workloads and cluster-local persistent volumes. Do not use this command when you only intend to save RAM.

## 13. Current implementation notes

- The local environment uses Kind and Docker.
- The Voting App is deployed through Kustomize.
- Prometheus Stack, Loki and Alloy are installed through pinned Helm chart versions.
- Prometheus and Grafana have persistent storage.
- Loki has persistent storage.
- Alloy reads Kubernetes Pod logs through the Kubernetes API.
- The intended log collection scope is `voting-app`.
- The AI diagnosis service and incident diagnosis workflow are separate subsequent implementation phases.

```
kubectl port-forward -n voting-app svc/db 15432:5432
```