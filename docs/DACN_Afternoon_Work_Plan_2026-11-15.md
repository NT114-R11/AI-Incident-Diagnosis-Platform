# Kế hoạch làm việc buổi chiều -- DACN

**Dự án:** AI-Incident-Diagnosis-Platform\
**Ngày:** 15/11/2026

## 1. Mục tiêu buổi chiều

Tập trung rà soát AI Diagnosis Service và hoàn thiện CI trước khi dựng
lại Kind cluster để kiểm thử E2E.

-   Kiểm tra cấu trúc, Dockerfile, dependencies và cách khởi động
    service.
-   Xác minh cách chạy pytest và các biến môi trường cần thiết.
-   Kiểm tra Alembic, database URL và schema thực tế.
-   Xác minh Telegram polling chạy độc lập hay cùng ứng dụng.
-   Triển khai CI cho AI Diagnosis Service theo convention hiện tại của
    repository.

**Nguyên tắc:** Không refactor phần đang hoạt động; không sửa workflow
Vote/Result/Worker nếu chưa có lỗi; không viết Kubernetes manifests dựa
trên giả định.

## 2. Bắt đầu: rà soát repository

Tại thư mục gốc repository, chạy:

``` bash
tree -L 3 ai-diagnosis-service
```

Chuẩn bị nội dung các file sau (nếu có):

``` text
ai-diagnosis-service/Dockerfile
ai-diagnosis-service/requirements.txt
ai-diagnosis-service/alembic.ini
ai-diagnosis-service/alembic/env.py
ai-diagnosis-service/app/core/config.py
ai-diagnosis-service/app/main.py
scripts/telegram_polling.py
```

Nếu cần, xem nội dung bằng:

``` bash
sed -n '1,240p' ai-diagnosis-service/Dockerfile
sed -n '1,260p' ai-diagnosis-service/requirements.txt
sed -n '1,260p' ai-diagnosis-service/alembic.ini
sed -n '1,300p' ai-diagnosis-service/alembic/env.py
sed -n '1,280p' ai-diagnosis-service/app/core/config.py
sed -n '1,260p' ai-diagnosis-service/app/main.py
sed -n '1,260p' scripts/telegram_polling.py
```

## 3. Những điểm cần xác minh

Không suy đoán; kiểm tra trực tiếp source code:

-   Docker build context và vị trí Dockerfile.
-   Phiên bản Python, cách cài dependencies và lệnh khởi động.
-   Container port và health endpoint.
-   Cách chạy pytest; test nào cần PostgreSQL hoặc environment
    variables.
-   Alembic lấy database URL từ đâu, quản lý schema nào và đặt
    `alembic_version` ở đâu.
-   Telegram polling là process riêng hay chạy cùng FastAPI.
-   Các biến môi trường bắt buộc và những integration cần mock/tắt khi
    test.

## 4. Triển khai CI cho AI Diagnosis Service

Sau khi rà soát:

1.  Tạo workflow riêng cho AI Diagnosis Service.
2.  Checkout source và thiết lập đúng phiên bản Python.
3.  Cài dependencies.
4.  Thiết lập environment variables cần cho test.
5.  Chạy pytest.
6.  Chỉ build Docker image khi test pass.
7.  Push image lên Docker Hub và GHCR theo convention hiện tại của
    repository.

### Tiêu chí hoàn thành

-   [ ] Workflow chạy được trên GitHub Actions.
-   [ ] Test được thực thi và kết quả hiển thị rõ ràng.
-   [ ] Docker image build thành công.
-   [ ] Image push thành công lên registry dự kiến.
-   [ ] Không ảnh hưởng workflow Vote/Result/Worker hiện có.

Không đưa Gemini API key, Telegram bot token, database password hoặc
credentials thật vào repository/log CI. Dùng GitHub Secrets khi cần; ưu
tiên mock hoặc tắt external integrations trong test nếu không cần gọi
dịch vụ thật.

## 5. Chuẩn bị cho lần dựng Kind tiếp theo

Chưa viết Deployment/Service YAML cho đến khi xác minh:

-   [ ] Image name và tag của AI Diagnosis Service.
-   [ ] Container port và health endpoint.
-   [ ] Tên biến môi trường ứng dụng thực sự đọc.
-   [ ] PostgreSQL Service name, database và schema theo
    manifests/migrations.
-   [ ] Prometheus Service DNS và port.
-   [ ] Loki Service DNS và port.
-   [ ] Cách chạy Alembic migration một lần.
-   [ ] Cách triển khai Telegram polling.
-   [ ] Alertmanager webhook URL tới AI Diagnosis Service.

Định hướng hiện tại: ưu tiên đơn giản, có thể dùng chung PostgreSQL
instance/database với Voting App nhưng tách schema cho AI Diagnosis
Service nếu migration hiện tại hỗ trợ. Phải kiểm tra `alembic/env.py` và
`alembic.ini` trước khi chốt.

## 6. Roadmap sau khi CI hoàn tất

1.  Dựng lại Kind cluster.
2.  Deploy Voting App và monitoring stack.
3.  Deploy PostgreSQL và AI Diagnosis Service.
4.  Kiểm tra kết nối Prometheus, Loki, PostgreSQL và Alertmanager
    webhook.
5.  E2E: Alert → Incident → Evidence → Rule-based diagnosis → Gemini →
    Telegram.
6.  Xây dựng và kiểm thử các kịch bản sự cố demo.
7.  Ghi hình demo local làm phương án dự phòng.
8.  Deploy Cloud trên EC2/K3s.
9.  Hoàn thiện CD và ghi hình demo Cloud cuối cùng.

**Argo CD đang nằm trong Future Work**, không phải hạng mục bắt buộc để
hoàn thành DACN.

## 7. Lưu ý bảo mật

-   Không chia sẻ Telegram bot token, Gemini API key, database password
    hoặc `.env` chứa secrets.
-   Nếu Telegram token từng bị lộ, revoke token cũ qua @BotFather bằng
    `/revoke`, sau đó cập nhật token mới trong `.env` và GitHub Secrets.
-   Kiểm tra, che credentials trước khi gửi log.

## 8. Checklist kết thúc buổi chiều

-   [ ] Rà soát Dockerfile, dependencies và entrypoint.
-   [ ] Xác minh cách chạy test.
-   [ ] Xác minh Alembic và cấu hình database.
-   [ ] Xác minh Telegram polling.
-   [ ] CI AI Diagnosis Service chạy thành công.
-   [ ] Docker image build/push thành công (nếu workflow đã bật push).
-   [ ] Ghi lại thông tin còn thiếu trước khi dựng Kind.

**Điểm bắt đầu khi quay lại:** Gửi cấu trúc thư mục và các file ở mục 2.
Chúng ta sẽ đọc source trước, chỉnh từng phần, chạy kiểm tra và xác nhận
kết quả rồi mới chuyển bước.
