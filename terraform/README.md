# 🚀 Hướng Dẫn Tự Động Hóa Hạ Tầng Bằng Terraform & GitOps ArgoCD

Tài liệu này hướng dẫn cách sử dụng **Terraform** để tự động khởi tạo hạ tầng Cloud trên **AWS**, cài đặt cụm **Kubernetes (k3s)**, và cấu hình **ArgoCD** để triển khai liên tục (Continuous Delivery) cho toàn bộ nền tảng `AI-Incident-Diagnosis-Platform`.

---

## 🌟 Kiến trúc hạ tầng

* **Infrastructure as Code (IaC):** Terraform tự động tạo:
  * Security Group mở đầy đủ cổng: SSH (22), HTTP (80/30080), HTTPS (443/30443), ArgoCD (30088), Grafana (3000).
  * SSH Key Pair (tự tạo và tải file `.pem` về máy).
  * Máy chủ EC2 `t3.large` (2 vCPU, 8GB RAM, 40GB SSD).
  * Elastic IP tĩnh cho máy chủ.
* **Tự động hóa cấu hình (User Data):**
  * Tự cài đặt cụm `k3s` (Kubernetes chuẩn CNCF).
  * Tự cài đặt `Helm 3`.
  * Tự cài đặt `NGINX Ingress Controller`.
  * Tự cài đặt và cấu hình `ArgoCD`.
  * Tự clone mã nguồn repository về máy chủ.
* **Continuous Delivery (GitOps):**
  * ArgoCD theo dõi nhánh `main` tại đường dẫn `k8s/overlays/production`.
  * Tự động kéo Docker image và đồng bộ khi có phiên bản mới.

---

## 📋 Bước 1: Chuẩn bị thông tin AWS Academy

1. Mở phòng Lab trên **AWS Academy**, bấm nút **AWS Details**.
2. Bấm vào **Show** cạnh dòng **AWS CLI credentials**.
3. Copy toàn bộ đoạn text có dạng:

```bash
export AWS_ACCESS_KEY_ID="ASIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_SESSION_TOKEN="..."
export AWS_DEFAULT_REGION="us-east-1"
```

> ⚠️ **LƯU Ý QUAN TRỌNG:** AWS Academy Learner Lab có chính sách bảo mật (SCP) **chỉ cho phép region `us-east-1` (N. Virginia)**. Nếu dùng bất kỳ region nào khác (như `ap-southeast-1`), AWS sẽ báo lỗi `UnauthorizedOperation ... with an explicit deny in a service control policy`.

4. Dán đoạn trên vào terminal của bạn (trên WSL hoặc macOS/Linux) để nạp quyền cho Terraform.

---

## 📋 Bước 2: Chạy Terraform để dựng hạ tầng (1 lệnh duy nhất)

Di chuyển vào thư mục `terraform`:

```bash
cd terraform

# 1. Khởi tạo các provider của Terraform
terraform init

# 2. Xem trước kế hoạch dựng hạ tầng
terraform plan

# 3. Tiến hành khởi tạo máy chủ trên AWS (gõ yes khi được hỏi)
terraform apply -auto-approve
```

Sau khi hoàn thành (khoảng 1 - 2 phút), màn hình sẽ in ra các thông số kết nối:

```text
Outputs:
ec2_public_ip                 = "13.250.xx.xx"
ssh_command                   = "ssh -i ai-diagnosis-key.pem ubuntu@13.250.xx.xx"
argocd_web_url                = "http://13.250.xx.xx:30088"
argocd_admin_password_command = "ssh -i ai-diagnosis-key.pem ubuntu@13.250.xx.xx 'cat ~/argocd-admin-password.txt'"
voting_app_url                = "http://13.250.xx.xx:30080"
```

*(Lưu ý: Sau khi Terraform chạy xong, hãy chờ thêm khoảng **2 - 3 phút** để máy chủ EC2 hoàn tất quá trình cài đặt k3s và ArgoCD ngầm bên dưới).*

---

## 📋 Bước 3: Lấy mật khẩu và đăng nhập ArgoCD

1. Lấy mật khẩu tài khoản `admin` của ArgoCD:
   ```bash
   ssh -i ai-diagnosis-key.pem ubuntu@<EC2_PUBLIC_IP> "cat ~/argocd-admin-password.txt"
   ```
2. Mở trình duyệt truy cập: **`http://<EC2_PUBLIC_IP>:30088`**
   * **Username:** `admin`
   * **Password:** *(Mật khẩu vừa lấy ở trên)*

Bạn sẽ thấy giao diện quản lý GitOps trực quan của **ArgoCD** hiện lên!

---

## 📋 Bước 4: Tạo Secret và Kích hoạt Đồng bộ bằng ArgoCD

Để AI Service chạy được trên Cloud, ta cần nạp các API key (Gemini, Telegram) trực tiếp vào Kubernetes:

1. **SSH vào máy chủ EC2:**
   ```bash
   ssh -i ai-diagnosis-key.pem ubuntu@<EC2_PUBLIC_IP>
   ```

2. **Tạo namespace và nạp Secret:**
   ```bash
   kubectl create namespace voting-app

   # Điền thông tin thật của bạn vào lệnh dưới:
   kubectl create secret generic ai-diagnosis-secret \
     --namespace voting-app \
     --from-literal=GEMINI_API_KEY="AIzaSy..." \
     --from-literal=TELEGRAM_BOT_TOKEN="..." \
     --from-literal=TELEGRAM_CHAT_ID="..." \
     --from-literal=TELEGRAM_ADMIN_IDS="..."
   ```

3. **Cài đặt Monitoring Stack (Prometheus, Loki, Alertmanager):**
   ```bash
   cd ~/AI-Incident-Diagnosis-Platform

   # Cài Prometheus Stack
   helm upgrade --install prometheus-stack \
     prometheus-community/kube-prometheus-stack \
     --version 92.20.0 \
     --namespace monitoring \
     --create-namespace \
     -f k8s/monitoring/prometheus-stack/values-production.yaml \
     --wait --timeout 10m

   # Cài Loki
   helm upgrade --install loki \
     grafana-community/loki \
     --version 21.0.0 \
     --namespace monitoring \
     -f k8s/monitoring/loki/values-production.yaml \
     --wait --timeout 10m

   # Cài Alloy
   helm upgrade --install alloy \
     grafana/alloy \
     --version 1.15.0 \
     --namespace monitoring \
     -f k8s/monitoring/alloy/values-local.yaml \
     --wait --timeout 10m
   ```

4. **Kích hoạt ArgoCD Application (Bắt đầu GitOps CD):**
   ```bash
   kubectl apply -f k8s/argocd/app-platform.yaml
   ```

5. **Xem kết quả trên ArgoCD Dashboard:**
   * Mở lại trang web `http://<EC2_PUBLIC_IP>:30088`.
   * Bạn sẽ thấy ứng dụng `ai-incident-platform` chuyển sang trạng thái **Synced & Healthy**!
   * Toàn bộ Voting App, AI Diagnosis Service, Database sẽ được tự động vẽ sơ đồ trực quan ngay trên trình duyệt.

---

## 📋 Bước 5: Truy cập ứng dụng & Kiểm thử GitOps

1. **Truy cập Voting App:**
   * Thêm dòng sau vào file `hosts` của máy bạn:
     `<EC2_PUBLIC_IP> voting.local result.voting.local`
   * Mở trình duyệt: `http://voting.local:30080` để bình chọn.
2. **Kiểm thử CD (Continuous Delivery):**
   * Mỗi khi nhóm bạn push code lên GitHub `main`, GitHub Actions tự động build Docker image mới.
   * ArgoCD sẽ tự động phát hiện và cập nhật Pods trên AWS mà không cần ai gõ lệnh deploy thủ công!

---

## 🧹 Dọn dẹp tài nguyên (RẤT QUAN TRỌNG ĐỂ KHÔNG TỐN TIỀN LAB)

Sau khi demo hoặc bảo vệ xong đồ án, hãy giải phóng tài nguyên để không bị trừ hết tiền AWS Academy:

```bash
cd terraform
terraform destroy -auto-approve
```
Toàn bộ máy chủ, IP tĩnh, ổ cứng và Security Group sẽ được xóa sạch trong 1 phút.
