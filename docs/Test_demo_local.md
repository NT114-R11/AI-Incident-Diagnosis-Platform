# DACN – LOCAL DEMO & END-TO-END TEST RUNBOOK

**Project:** AI-Incident-Diagnosis-Platform  
**Environment:** Kind – Kubernetes Local  
**Namespace ứng dụng:** `voting-app`  
**Namespace monitoring:** `monitoring`

---

## 1. Mục tiêu demo

Chứng minh hệ thống có khả năng:

1. Giám sát trạng thái Kubernetes và tài nguyên container.
2. Thu thập metrics bằng Prometheus.
3. Thu thập logs bằng Alloy và lưu trữ trên Loki.
4. Phát hiện sự cố bằng Prometheus Rules và Loki Ruler.
5. Chuyển cảnh báo qua Alertmanager.
6. Tiếp nhận cảnh báo qua AI Diagnosis API.
7. Thu thập evidence từ Prometheus, Loki và Kubernetes.
8. Phân tích sự cố bằng AI.
9. Lưu incident vào PostgreSQL.
10. Gửi kết quả chẩn đoán qua Telegram.

**Nguyên tắc:** AI chỉ đưa ra chẩn đoán và khuyến nghị. Không tự động restart Pod, sửa cấu hình hoặc thực hiện remediation.

---

## 2. Kiểm tra trước khi demo

### 2.1. Kiểm tra Kubernetes

```bash
kubectl get nodes
kubectl get pods -n voting-app
kubectl get pods -n monitoring
```

Điều kiện:

- Các node ở trạng thái Ready.
- Voting App hoạt động.
- AI Diagnosis API hoạt động.
- Telegram Polling hoạt động.
- Monitoring Stack không có Pod lỗi.

### 2.2. Kiểm tra các thành phần monitoring

```bash
helm list -n monitoring
kubectl get svc -n monitoring
kubectl get pvc -n monitoring
```

Kiểm tra Prometheus Targets, Loki readiness, Alloy DaemonSet và Alertmanager.

### 2.3. Port-forward

Sử dụng các terminal riêng biệt.

**Terminal 1 – Grafana**

```bash
kubectl port-forward -n monitoring \
  svc/prometheus-stack-grafana 3000:80
```

Truy cập: http://localhost:3000

**Terminal 2 – Prometheus**

```bash
kubectl port-forward -n monitoring \
  svc/prometheus-stack-kube-prometheus-prometheus 9090:9090
```

Truy cập: http://localhost:9090

**Terminal 3 – Alertmanager**

```bash
kubectl port-forward -n monitoring \
  svc/prometheus-stack-kube-prometheus-alertmanager 9093:9093
```

Truy cập: http://localhost:9093

**Terminal 4 – Loki (chỉ khi cần debug)**

```bash
kubectl port-forward -n monitoring \
  svc/loki-gateway 3100:80
```

Truy cập: http://localhost:3100

Lưu ý: Các tên Service trên là tên dự kiến theo Helm release. Phải đối chiếu `kubectl get svc -n monitoring` trước khi sử dụng.

### 2.4. Kiểm tra AI Diagnosis API

```bash
kubectl get pods -n voting-app
kubectl logs deploy/ai-diagnosis-api -n voting-app
kubectl logs deploy/telegram-polling -n voting-app
```

Kiểm tra PostgreSQL:

```bash
kubectl exec deploy/db -n voting-app -- \
  psql -U postgres -d postgres -c \
  "SELECT * FROM public.alembic_version;"
```

Revision mong đợi:

`11a51f2aa2a6`

---

# 3. Demo Scenario 01 – Kubernetes CrashLoopBackOff

**File:** `k8s/test-scenarios/crashloop-liveness.yaml`

**Alert:** `POD_CRASH_LOOP`

**Detection:** Prometheus

### Mục tiêu

Mô phỏng một ứng dụng bị lỗi liveness probe khiến Kubernetes liên tục restart container.

### Thực hiện

1. Kiểm tra trạng thái Pod trước khi tạo sự cố.

```bash
kubectl get pods -n voting-app
```

2. Đọc manifest để xác nhận namespace, tên Pod và cấu hình liveness probe.

```bash
cat k8s/test-scenarios/crashloop-liveness.yaml
```

3. Tạo sự cố.

```bash
kubectl apply -f k8s/test-scenarios/crashloop-liveness.yaml
```

4. Theo dõi trạng thái Pod.

```bash
kubectl get pods -n voting-app -w
```

5. Kiểm tra events.

```bash
kubectl get events -n voting-app \
  --sort-by=.lastTimestamp
```

6. Truy cập Prometheus, kiểm tra alert `POD_CRASH_LOOP`.

7. Truy cập Alertmanager, kiểm tra alert được tiếp nhận.

8. Kiểm tra AI Diagnosis API và Telegram để xác minh quá trình xử lý.

### Kết quả mong đợi

- Pod xuất hiện trạng thái CrashLoopBackOff.
- Prometheus phát hiện sự cố.
- Alertmanager nhận cảnh báo.
- AI nhận được alert và thực hiện chẩn đoán.
- Kết quả được gửi đến Telegram nếu luồng notification hoạt động.

### Cleanup

```bash
kubectl delete -f k8s/test-scenarios/crashloop-liveness.yaml
```

Kiểm tra Pod đã được dọn dẹp và hệ thống trở về trạng thái bình thường.

---

# 4. Demo Scenario 02 – Application Error qua Loki

**File:** `k8s/test-scenarios/loki-error.yaml`

**Alert:** `APPLICATION_ERROR`

**Detection:** Loki Ruler

### Mục tiêu

Mô phỏng ứng dụng phát sinh lỗi ở tầng application mà không cần làm Pod chết.

### Thực hiện

1. Kiểm tra Alloy.

```bash
kubectl get pods -n monitoring -o wide
```

2. Kiểm tra nội dung manifest.

```bash
cat k8s/test-scenarios/loki-error.yaml
```

3. Apply test workload.

```bash
kubectl apply -f k8s/test-scenarios/loki-error.yaml
```

4. Kiểm tra log tại namespace ứng dụng.

```bash
kubectl logs -n voting-app \
  -l app=<label-thực-tế-của-test-pod> \
  --all-containers=true
```

5. Truy cập Grafana Explore, chọn Loki datasource.

6. Tìm log với nội dung:

`ERROR simulated application failure: database connection failed`

7. Kiểm tra Loki Ruler phát hiện `APPLICATION_ERROR`.

8. Kiểm tra Alertmanager và AI Diagnosis API.

9. Kiểm tra Telegram notification.

### Kết quả mong đợi

- Alloy thu thập được log.
- Loki lưu trữ được log.
- Loki Ruler phát hiện `APPLICATION_ERROR`.
- Alertmanager chuyển cảnh báo đến AI API.
- AI truy vấn logs làm evidence cho chẩn đoán.

### Cleanup

```bash
kubectl delete -f k8s/test-scenarios/loki-error.yaml
```

---

# 5. Demo Scenario 03 – High CPU

**File:** `k8s/test-scenarios/prometheus-cpu.yaml`

**Alert:** `HIGH_CPU`

**Detection:** Prometheus

**Ngưỡng:** CPU usage vượt 80% CPU limit trong 1 phút.

### Mục tiêu

Mô phỏng một container tiêu thụ CPU cao.

### Thực hiện

1. Kiểm tra cấu hình resource limit trong manifest.

```bash
cat k8s/test-scenarios/prometheus-cpu.yaml
```

2. Apply workload.

```bash
kubectl apply -f k8s/test-scenarios/prometheus-cpu.yaml
```

3. Theo dõi CPU metrics trên Prometheus.

4. Kiểm tra alert `HIGH_CPU`.

5. Kiểm tra Alertmanager.

6. Kiểm tra AI Diagnosis và Telegram.

### Kết quả mong đợi

- CPU usage tăng.
- Prometheus thu thập được metrics.
- Alert `HIGH_CPU` chuyển sang trạng thái Firing.
- Alertmanager gửi cảnh báo.
- AI sử dụng metrics để xác định tình trạng CPU cao.

### Cleanup

```bash
kubectl delete -f k8s/test-scenarios/prometheus-cpu.yaml
```

---

# 6. Demo Scenario 04 – Memory Pressure

**File:** `k8s/test-scenarios/prometheus-memory.yaml`

### Mục tiêu

Kiểm tra khả năng thu thập và quan sát memory usage của container.

### Thực hiện

1. Đọc manifest và xác nhận memory request/limit.

```bash
cat k8s/test-scenarios/prometheus-memory.yaml
```

2. Kiểm tra tài nguyên còn trống trên cluster.

3. Apply workload.

```bash
kubectl apply -f k8s/test-scenarios/prometheus-memory.yaml
```

4. Theo dõi resource usage.

```bash
kubectl top pods -n voting-app
```

5. Kiểm tra metrics memory trên Prometheus và Grafana.

6. Theo dõi trạng thái Pod, kiểm tra có xảy ra OOMKilled hay không.

### Kết quả mong đợi

- Prometheus quan sát được memory usage.
- Grafana hiển thị được biến động memory.
- Có thể xác định trạng thái OOMKilled nếu container vượt giới hạn.

**Lưu ý:** Hiện tại chưa xác nhận có alert rule riêng cho memory. Không được kết luận hệ thống đã phát hiện và gửi cảnh báo memory nếu chưa bổ sung rule tương ứng.

### Cleanup

```bash
kubectl delete -f k8s/test-scenarios/prometheus-memory.yaml
```

---

# 7. Kiểm tra Incident trong PostgreSQL

Sau mỗi kịch bản, kiểm tra dữ liệu được lưu trong hệ thống.

```bash
kubectl exec deploy/db -n voting-app -- \
  psql -U postgres -d postgres -c \
  "SELECT
      id,
      fingerprint,
      alert_name,
      namespace,
      pod,
      severity,
      status,
      first_seen_at,
      last_seen_at,
      resolved_at
   FROM incident_management.incidents
   ORDER BY created_at DESC
   LIMIT 10;"
```

Kiểm tra:

- Incident có được tạo không?
- Alert name có chính xác không?
- Namespace và Pod có đúng không?
- Fingerprint có ổn định không?
- Incident status có được cập nhật không?
- Resolved alert có cập nhật `resolved_at` không?

Không mặc định các trường đã được cập nhật đúng chỉ vì Telegram nhận được tin nhắn.

---

# 8. Kiểm tra Alert Lifecycle

Đối với mỗi alert, kiểm tra ba trạng thái:

1. Inactive: Không có sự cố.
2. Firing: Sự cố đang xảy ra.
3. Resolved: Sự cố đã được xử lý.

Kiểm tra:

- Alertmanager nhận được firing alert.
- AI tạo hoặc cập nhật incident.
- Alertmanager gửi resolved notification.
- AI cập nhật incident tương ứng.
- Không tạo incident trùng lặp khi cùng fingerprint vẫn đang active.

Đây là phần đặc biệt quan trọng để chứng minh cơ chế quản lý incident của hệ thống.

---

# 9. Checklist nghiệm thu demo

| Hạng mục | Tiêu chí |
|---|---|
| Kubernetes | Quan sát được trạng thái Pod |
| Prometheus | Thu thập được metrics |
| Loki | Lưu được application logs |
| Alloy | Đẩy được logs vào Loki |
| Prometheus Rules | Phát hiện CrashLoop và High CPU |
| Loki Ruler | Phát hiện Application Error |
| Alertmanager | Nhận và gửi alert |
| AI API | Tiếp nhận webhook |
| Evidence | Thu thập được metrics/logs/status |
| Gemini | Sinh chẩn đoán |
| PostgreSQL | Lưu incident |
| Telegram | Nhận notification |
| Resolution | Xử lý được resolved alert |

---

# 10. Nguyên tắc vận hành khi demo

- Chỉ chạy một fault injection tại một thời điểm.
- Chụp lại trạng thái hệ thống trước và sau khi tạo sự cố.
- Ghi nhận thời điểm alert chuyển sang Firing.
- Lưu lại kết quả AI diagnosis.
- Kiểm tra bản ghi PostgreSQL.
- Kiểm tra Telegram notification.
- Cleanup workload trước khi chạy kịch bản tiếp theo.
- Đợi hệ thống trở về trạng thái bình thường trước khi chuyển kịch bản.
- Không tạo memory pressure lớn nếu cluster đang thiếu tài nguyên.
- Không thực hiện fault injection trên PostgreSQL production.

**Tiêu chí thành công cuối cùng:** Chứng minh được hệ thống chuyển từ trạng thái quan sát hạ tầng sang phát hiện sự cố, thu thập evidence và hỗ trợ chẩn đoán bằng AI, đồng thời lưu lại incident để phục vụ theo dõi.