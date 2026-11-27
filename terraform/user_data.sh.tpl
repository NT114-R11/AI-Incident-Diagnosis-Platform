#!/usr/bin/env bash
# ==============================================================================
# Automated Bootstrap Script for AI Incident Diagnosis Platform on AWS EC2
# Managed by Terraform
# ==============================================================================

set -Eeuo pipefail

LOG_FILE="/var/log/k3s-bootstrap.log"
exec > >(tee -a "$LOG_FILE") 2>&1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

log "=== Bắt đầu khởi tạo máy chủ Kubernetes (k3s) & ArgoCD ==="

# 1. Cập nhật hệ thống & cài các gói cần thiết
log "1. Cài đặt các gói tiện ích..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y curl git jq apt-transport-https ca-certificates gnupg lsb-release

# 2. Cài đặt k3s (Kubernetes lightweight)
# Tắt Traefik mặc định để sử dụng NGINX Ingress Controller chuẩn của đề tài
log "2. Cài đặt k3s cluster..."
curl -sfL https://get.k3s.io | sh -s - \
  --disable=traefik \
  --write-kubeconfig-mode=644

# Đợi k3s sẵn sàng
log "Đợi k3s node sẵn sàng..."
for i in {1..30}; do
  if k3s kubectl get nodes | grep -q "Ready"; then
    log "k3s Node đã ở trạng thái Ready!"
    break
  fi
  sleep 3
done

# Thiết lập kubeconfig cho cả root và user ubuntu
mkdir -p /root/.kube /home/ubuntu/.kube
cp /etc/rancher/k3s/k3s.yaml /root/.kube/config
cp /etc/rancher/k3s/k3s.yaml /home/ubuntu/.kube/config
chown -R ubuntu:ubuntu /home/ubuntu/.kube
chmod 600 /root/.kube/config /home/ubuntu/.kube/config

# Export KUBECONFIG hệ thống để Helm và kubectl luôn nhận diện cluster
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
echo "export KUBECONFIG=/etc/rancher/k3s/k3s.yaml" >> /etc/environment
echo "export KUBECONFIG=/etc/rancher/k3s/k3s.yaml" >> /home/ubuntu/.bashrc
echo "export KUBECONFIG=/etc/rancher/k3s/k3s.yaml" >> /root/.bashrc

# Alias kubectl cho tiện sử dụng
ln -sf /usr/local/bin/k3s /usr/local/bin/kubectl

# 3. Cài đặt Helm 3
log "3. Cài đặt Helm 3..."
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Thêm sẵn tất cả các Helm repos cần thiết
helm repo add nginx-stable https://helm.nginx.com/stable
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm upgrade --install nginx-ingress nginx-stable/nginx-ingress \
  --version 2.8.1 \
  --namespace nginx-ingress \
  --create-namespace \
  --set controller.service.type=NodePort \
  --set controller.service.httpPort.nodePort=30080 \
  --set controller.service.httpsPort.nodePort=30443 \
  --wait \
  --timeout 5m

# 5. Cài đặt ArgoCD
log "5. Cài đặt ArgoCD GitOps Controller..."
kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Đợi ArgoCD server sẵn sàng
log "Đợi ArgoCD pods khởi động..."
kubectl rollout status deployment/argocd-server -n argocd --timeout=300s || true

# Mở cổng ArgoCD qua NodePort 30088 và bật mode insecure để truy cập HTTP trực tiếp
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "NodePort", "ports": [{"port": 80, "targetPort": 8080, "nodePort": 30088, "name": "http"}]}}'

# Cài đặt ArgoCD CLI
ARGOCD_VERSION=$(curl -s https://api.github.com/repos/argoproj/argo-cd/releases/latest | grep tag_name | cut -d '"' -f 4)
curl -sSL -o /usr/local/bin/argocd "https://github.com/argoproj/argo-cd/releases/download/$${ARGOCD_VERSION}/argocd-linux-amd64"
chmod +x /usr/local/bin/argocd

# 6. Clone mã nguồn đề tài về máy
log "6. Clone repository đề tài..."
TARGET_DIR="/home/ubuntu/AI-Incident-Diagnosis-Platform"
if [ ! -d "$TARGET_DIR" ]; then
  git clone https://github.com/NT114-R11/AI-Incident-Diagnosis-Platform.git "$TARGET_DIR"
  chown -R ubuntu:ubuntu "$TARGET_DIR"
fi

# 7. Lấy mật khẩu ban đầu của ArgoCD và lưu ra file cho tiện tra cứu
log "7. Thu thập thông tin truy cập..."
sleep 10
ARGOCD_PASS=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>/dev/null | base64 -d || echo "Chưa tạo xong, xem bằng kubectl sau")
echo "$ARGOCD_PASS" > /home/ubuntu/argocd-admin-password.txt
chown ubuntu:ubuntu /home/ubuntu/argocd-admin-password.txt
chmod 600 /home/ubuntu/argocd-admin-password.txt

log "=== Khởi tạo thành công! Toàn bộ cluster, Ingress, ArgoCD đã sẵn sàng ==="
touch /var/log/bootstrap-completed.flag
