#!/usr/bin/env bash
# ==========================================================
# EC2 Bootstrap Script for AI Incident Diagnosis Platform
# 
# Cài đặt: k3s, kubectl, helm, argocd CLI
# Chạy 1 lần sau khi SSH vào EC2:
#   bash scripts/bootstrap-ec2.sh
# ==========================================================

set -Eeuo pipefail

log() { printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }
die() { echo "[ERROR] $*" >&2; exit 1; }

# ==========================================================
# 1. Cài k3s (Kubernetes nhẹ, 1 lệnh)
# ==========================================================
log "Installing k3s..."

# --disable=traefik vì chúng ta dùng NGINX Ingress
curl -sfL https://get.k3s.io | sh -s - \
  --disable=traefik \
  --write-kubeconfig-mode=644

log "Waiting for k3s to be ready..."
sleep 30
k3s kubectl get nodes

# Cấu hình kubeconfig cho user hiện tại
mkdir -p ~/.kube
cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
chmod 600 ~/.kube/config
sed -i "s/127.0.0.1/$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)/g" ~/.kube/config

log "k3s installed successfully"

# ==========================================================
# 2. Cài Helm
# ==========================================================
log "Installing Helm..."

curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

helm version
log "Helm installed successfully"

# ==========================================================
# 3. Cài ArgoCD CLI (tùy chọn, để quản lý từ terminal)
# ==========================================================
log "Installing ArgoCD CLI..."

ARGOCD_VERSION=$(curl -s https://api.github.com/repos/argoproj/argo-cd/releases/latest \
  | grep tag_name | cut -d '"' -f 4)

curl -sSL -o /usr/local/bin/argocd \
  "https://github.com/argoproj/argo-cd/releases/download/${ARGOCD_VERSION}/argocd-linux-amd64"

chmod +x /usr/local/bin/argocd
argocd version --client
log "ArgoCD CLI installed successfully"

# ==========================================================
# 4. Thêm Helm Repositories
# ==========================================================
log "Adding Helm repositories..."

helm repo add nginx-stable https://helm.nginx.com/stable
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

log "Helm repositories added"

# ==========================================================
# 5. Cài NGINX Ingress Controller
# ==========================================================
log "Installing NGINX Ingress Controller..."

helm upgrade --install nginx-ingress nginx-stable/nginx-ingress \
  --version 2.8.1 \
  --namespace nginx-ingress \
  --create-namespace \
  --set controller.service.type=NodePort \
  --set controller.service.httpPort.nodePort=30080 \
  --set controller.service.httpsPort.nodePort=30443 \
  --wait \
  --timeout 5m

kubectl get pods -n nginx-ingress
log "NGINX Ingress installed successfully"

# ==========================================================
# 6. Cài ArgoCD
# ==========================================================
log "Installing ArgoCD..."

kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

log "Waiting for ArgoCD pods to be ready (up to 3 minutes)..."
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=180s

# Lấy mật khẩu admin
ARGOCD_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d)

echo ""
echo "======================================================"
echo "  ArgoCD Setup Complete!"
echo "  Access: kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo "  Username: admin"
echo "  Password: ${ARGOCD_PASSWORD}"
echo "======================================================"
echo ""

# ==========================================================
# 7. Summary
# ==========================================================
EC2_PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "N/A")

echo "======================================================"
echo "  EC2 Bootstrap Complete!"
echo "  EC2 Public IP: ${EC2_PUBLIC_IP}"
echo ""
echo "  Installed:"
echo "    ✅ k3s (Kubernetes)"
echo "    ✅ Helm"
echo "    ✅ ArgoCD CLI"
echo "    ✅ NGINX Ingress (NodePort 30080/30443)"
echo "    ✅ ArgoCD (namespace: argocd)"
echo ""
echo "  Next steps: Run scripts/deploy-platform.sh"
echo "======================================================"
