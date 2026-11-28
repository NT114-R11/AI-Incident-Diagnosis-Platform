#!/usr/bin/env bash
# ==========================================================
# Deploy AI Incident Diagnosis Platform lên k3s
#
# Chạy sau scripts/bootstrap-ec2.sh:
#   bash scripts/deploy-platform.sh
#
# Yêu cầu các biến môi trường sau:
#   GEMINI_API_KEY
#   TELEGRAM_BOT_TOKEN
#   TELEGRAM_CHAT_ID
#   TELEGRAM_ADMIN_IDS
# ==========================================================

set -Eeuo pipefail

log() { printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }
die() { echo "[ERROR] $*" >&2; exit 1; }

# ==========================================================
# 1. Tạo namespace
# ==========================================================
log "Creating namespaces..."
kubectl create namespace voting-app --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

# ==========================================================
# 2. Tạo Secrets (không commit lên Git)
# ==========================================================
if [[ -n "${GEMINI_API_KEY:-}" && -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" && -n "${TELEGRAM_ADMIN_IDS:-}" ]]; then
  log "Creating/updating secrets..."
  kubectl create secret generic ai-diagnosis-secret \
    --namespace voting-app \
    --from-literal=GEMINI_API_KEY="${GEMINI_API_KEY}" \
    --from-literal=TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}" \
    --from-literal=TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID}" \
    --from-literal=TELEGRAM_ADMIN_IDS="${TELEGRAM_ADMIN_IDS}" \
    --dry-run=client -o yaml | kubectl apply -f -
  log "Secrets created/updated"
elif kubectl get secret ai-diagnosis-secret -n voting-app >/dev/null 2>&1; then
  log "Secret ai-diagnosis-secret already exists in voting-app, skipping creation."
else
  : "${GEMINI_API_KEY:?Need to set GEMINI_API_KEY (or create secret ai-diagnosis-secret first)}"
  : "${TELEGRAM_BOT_TOKEN:?Need to set TELEGRAM_BOT_TOKEN}"
  : "${TELEGRAM_CHAT_ID:?Need to set TELEGRAM_CHAT_ID}"
  : "${TELEGRAM_ADMIN_IDS:?Need to set TELEGRAM_ADMIN_IDS}"
fi

# ==========================================================
# 3. Cài Monitoring Stack
# ==========================================================
log "Adding/updating Helm repos..."
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1 || true
helm repo add grafana-community https://grafana-community.github.io/helm-charts >/dev/null 2>&1 || true
helm repo add grafana https://grafana.github.io/helm-charts >/dev/null 2>&1 || true
helm repo update

log "Installing Prometheus Stack..."
helm upgrade --install prometheus-stack \
  prometheus-community/kube-prometheus-stack \
  --version 92.20.0 \
  --namespace monitoring \
  -f k8s/monitoring/prometheus-stack/values-production.yaml \
  --wait --timeout 10m

log "Applying Loki alert rules ConfigMap..."
kubectl apply -k k8s/monitoring/loki

log "Applying Prometheus alert rules..."
kubectl apply -f k8s/monitoring/prometheus-stack/prometheus-rules.yaml 2>/dev/null || true

log "Installing Loki..."
helm upgrade --install loki \
  grafana-community/loki \
  --version 21.0.0 \
  --namespace monitoring \
  -f k8s/monitoring/loki/values-production.yaml \
  --wait --timeout 10m

log "Installing Alloy..."
helm upgrade --install alloy \
  grafana/alloy \
  --version 1.15.0 \
  --namespace monitoring \
  -f k8s/monitoring/alloy/values-local.yaml \
  --wait --timeout 10m

log "Monitoring stack installed"

# ==========================================================
# 4. Tạo ArgoCD Application (kết nối Git repo → k3s)
# ==========================================================
log "Deploying ArgoCD Application..."

kubectl apply -f k8s/argocd/app-platform.yaml

log "ArgoCD Application created. Syncing..."
sleep 10

# Hiển thị trạng thái
kubectl get application -n argocd

# ==========================================================
# 5. Summary
# ==========================================================
EC2_PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "N/A")
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" 2>/dev/null | base64 -d || echo "N/A")

echo ""
echo "======================================================"
echo "  Deployment Complete!"
echo "  EC2 Public IP: ${EC2_PUBLIC_IP}"
echo ""
echo "  ArgoCD Dashboard:"
echo "    kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo "    URL: https://localhost:8080"
echo "    User: admin | Pass: ${ARGOCD_PASSWORD}"
echo ""
echo "  Voting App (sau khi ArgoCD sync xong ~2-3 phút):"
echo "    Vote:   http://${EC2_PUBLIC_IP}:30080  (cần thêm Host header: voting.local)"
echo "    Result: http://${EC2_PUBLIC_IP}:30080  (cần thêm Host header: result.voting.local)"
echo ""
echo "  Kiểm tra pods:"
echo "    kubectl get pods -n voting-app"
echo "    kubectl get pods -n monitoring"
echo "======================================================"
