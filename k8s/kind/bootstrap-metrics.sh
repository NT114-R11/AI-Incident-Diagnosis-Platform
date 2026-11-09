
#!/usr/bin/env bash

set -Eeuo pipefail

# ==========================================================
# Kind Control Plane Metrics Bootstrap
# Cluster: voting-local
#
# Configures:
#   - etcd metrics       : 0.0.0.0:2381
#   - controller-manager: 0.0.0.0:10257
#   - scheduler          : 0.0.0.0:10259
#   - kube-proxy metrics : 0.0.0.0:10249
#
# Safe to run repeatedly.
# ==========================================================

CLUSTER_NAME="voting-local"
CONTROL_PLANE="${CLUSTER_NAME}-control-plane"
NAMESPACE="kube-system"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIND_CONFIG="${SCRIPT_DIR}/kind-config.yaml"

log() {
    printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$*"
}

die() {
    echo "[ERROR] $*" >&2
    exit 1
}

# ==========================================================
# 0. Dependencies
# ==========================================================

for cmd in docker kind kubectl jq grep sed; do
    command -v "$cmd" >/dev/null 2>&1 \
        || die "Missing dependency: $cmd"
done

[[ -f "$KIND_CONFIG" ]] \
    || die "Missing Kind config: $KIND_CONFIG"

# ==========================================================
# 1. Create cluster if necessary
# ==========================================================

if kind get clusters | grep -qx "$CLUSTER_NAME"; then
    log "Cluster $CLUSTER_NAME already exists"
else
    log "Creating Kind cluster: $CLUSTER_NAME"

    kind create cluster \
        --config "$KIND_CONFIG" \
        --wait 5m
fi

kubectl config use-context "kind-${CLUSTER_NAME}"

docker inspect "$CONTROL_PLANE" >/dev/null 2>&1 \
    || die "Control-plane container not found: $CONTROL_PLANE"

# ==========================================================
# 2. Wait for nodes
# ==========================================================

log "Waiting for all Kubernetes nodes"

kubectl wait \
    --for=condition=Ready \
    nodes --all \
    --timeout=240s

# ==========================================================
# 3. Static manifest patch function
# ==========================================================


patch_manifest() {
    local file="$1"
    local search="$2"
    local replacement="$3"
    local backup="$4"

    log "Patching $file"

    docker exec "$CONTROL_PLANE" sh -c '
        set -eu

        file="$1"
        search="$2"
        replacement="$3"
        backup="$4"

        test -f "$file" || {
            echo "Manifest not found: $file" >&2
            exit 1
        }

        # Preserve original manifest only once.
        if [ ! -f "$backup" ]; then
            cp "$file" "$backup"
            echo "Backup created: $backup"
        fi

        # Skip if already configured.
        if grep -Fq -- "$replacement" "$file"; then
            echo "Already configured: $replacement"

        else
            # Verify expected original configuration.
            if ! grep -Fq -- "$search" "$file"; then
                echo "Expected configuration not found: $search" >&2
                exit 1
            fi

            # Apply patch.
            sed -i "s|$search|$replacement|" "$file"

            # Mandatory verification.
            if ! grep -Fq -- "$replacement" "$file"; then
                echo "PATCH FAILED: replacement not found" >&2
                exit 1
            fi

            echo "Patch applied successfully"
        fi

        echo "Verified configuration:"
        grep -F -- "$replacement" "$file"
    ' _ "$file" "$search" "$replacement" "$backup"
}




# ==========================================================
# 4. Wait for etcd directly
# ==========================================================

wait_for_etcd() {
    local timeout=180
    local elapsed=0

    log "Waiting for etcd readiness endpoint"

    while (( elapsed < timeout )); do
        if docker exec "$CONTROL_PLANE" \
            curl -fsS --max-time 3 \
            http://127.0.0.1:2381/readyz 2>/dev/null |
            grep -qx "ok"; then

            log "etcd is Ready"
            return 0
        fi

        sleep 2
        elapsed=$((elapsed + 2))
    done

    echo "[ERROR] etcd did not become Ready" >&2

    docker exec "$CONTROL_PLANE" \
        crictl ps -a --name etcd || true

    die "etcd readiness timeout"
}

log "Configuring etcd metrics endpoint"

patch_manifest \
    "/etc/kubernetes/manifests/etcd.yaml" \
    "--listen-metrics-urls=http://127.0.0.1:2381" \
    "--listen-metrics-urls=http://0.0.0.0:2381" \
    "/tmp/etcd.yaml.bootstrap.bak"

# IMPORTANT:
# Do not use kubectl wait here.
# etcd restart can temporarily interrupt Kubernetes API.

wait_for_etcd

# ==========================================================
# 5. Wait for Kubernetes API
# ==========================================================

wait_for_api() {
    local timeout=180
    local elapsed=0

    log "Waiting for Kubernetes API readiness"

    while (( elapsed < timeout )); do
        if kubectl get --raw=/readyz \
            --request-timeout=5s >/dev/null 2>&1; then

            log "Kubernetes API is Ready"
            return 0
        fi

        sleep 3
        elapsed=$((elapsed + 3))
    done

    die "Kubernetes API readiness timeout"
}

wait_for_pod() {
    local pod="$1"

    wait_for_api

    log "Waiting for Pod: $pod"

    kubectl wait \
        --for=condition=Ready \
        "pod/${pod}" \
        -n "$NAMESPACE" \
        --timeout=180s
}

# ==========================================================
# 6. Controller Manager
# ==========================================================

log "Configuring Controller Manager metrics endpoint"

patch_manifest \
    "/etc/kubernetes/manifests/kube-controller-manager.yaml" \
    "--bind-address=127.0.0.1" \
    "--bind-address=0.0.0.0" \
    "/tmp/controller-manager.yaml.bootstrap.bak"

wait_for_pod "kube-controller-manager-${CONTROL_PLANE}"

# ==========================================================
# 7. Scheduler
# ==========================================================

log "Configuring Scheduler metrics endpoint"

patch_manifest \
    "/etc/kubernetes/manifests/kube-scheduler.yaml" \
    "--bind-address=127.0.0.1" \
    "--bind-address=0.0.0.0" \
    "/tmp/scheduler.yaml.bootstrap.bak"

wait_for_pod "kube-scheduler-${CONTROL_PLANE}"

# ==========================================================
# 8. Configure kube-proxy metrics
# ==========================================================

log "Checking kube-proxy configuration"

CURRENT_CONFIG="$(
    kubectl get configmap kube-proxy \
        -n "$NAMESPACE" \
        -o jsonpath='{.data.config\.conf}'
)"

[[ -n "$CURRENT_CONFIG" ]] \
    || die "Cannot read kube-proxy config"

FIELD_COUNT="$(
    grep -cE '^[[:space:]]*metricsBindAddress:' \
        <<< "$CURRENT_CONFIG" || true
)"

[[ "$FIELD_COUNT" == "1" ]] \
    || die "Expected exactly one metricsBindAddress field, found: $FIELD_COUNT"

UPDATED_CONFIG="$(
    printf '%s\n' "$CURRENT_CONFIG" |
        sed -E \
        's|^[[:space:]]*metricsBindAddress:.*|metricsBindAddress: 0.0.0.0:10249|'
)"

if [[ "$CURRENT_CONFIG" != "$UPDATED_CONFIG" ]]; then

    log "Updating kube-proxy ConfigMap"

    PATCH="$(
        jq -n \
            --arg config "$UPDATED_CONFIG" \
            '{data: {"config.conf": $config}}'
    )"

    kubectl patch configmap kube-proxy \
        -n "$NAMESPACE" \
        --type merge \
        -p "$PATCH"

    log "Restarting kube-proxy"

    kubectl rollout restart daemonset/kube-proxy \
        -n "$NAMESPACE"

else
    log "kube-proxy metrics already configured"
fi

log "Waiting for kube-proxy rollout"

kubectl rollout status daemonset/kube-proxy \
    -n "$NAMESPACE" \
    --timeout=240s

# ==========================================================
# 9. Final verification
# ==========================================================

log "Checking Kubernetes API"

kubectl get --raw=/readyz

log "Checking nodes"

kubectl get nodes

log "Checking kube-system Pods"

kubectl get pods \
    -n "$NAMESPACE" \
    -o wide

# ==========================================================
# 10. Verify listening addresses
# ==========================================================

log "Checking metrics listeners"

for node in \
    voting-local-control-plane \
    voting-local-worker \
    voting-local-worker2
do
    echo
    echo "===== ${node} ====="

    docker exec "$node" sh -c \
        'ss -lntp | grep -E "2381|10249|10257|10259" || true'
done

# ==========================================================
# 11. Verify node readiness again
# ==========================================================

log "Final node readiness check"

kubectl wait \
    --for=condition=Ready \
    nodes --all \
    --timeout=120s

kubectl get nodes

log "Bootstrap completed successfully!"

echo
echo "Next steps:"
echo "  1. Install monitoring stack"
echo "  2. Check Prometheus Targets"
echo "  3. Verify Alert Rules"
echo "  4. Verify Alerts"
