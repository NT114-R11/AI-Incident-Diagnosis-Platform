# Quy tắc thiết kế DACN --- AI Incident Diagnosis Platform

Đọc tài liệu này trước khi tiếp tục công việc ở cuộc trò chuyện mới. Đây
là các nguyên tắc ràng buộc để tránh over-engineering và đi chệch mục
tiêu đồ án.

## 1. Mục tiêu sản phẩm

Xây dựng hệ thống hỗ trợ chẩn đoán sự cố container/Kubernetes dựa
trên: - Metrics từ Prometheus. - Logs từ Loki. - Trạng thái/sự kiện
Kubernetes. - Rule-based diagnosis. - Gemini AI để phân tích và đề xuất
điều tra. - Telegram để Manager nhận kết quả và tương tác.

`voting-app` là workload mẫu được giám sát/demo. `AI Diagnosis Platform`
là sản phẩm chính.

## 2. Thứ tự ưu tiên

1.  Hoàn thiện nghiệp vụ AI trên local.
2.  Kiểm thử local end-to-end: alert giả lập → Incident → Evidence →
    Rules → Gemini → Telegram.
3.  Xác nhận duplicate, resolved và Gemini unavailable.
4.  Sau khi local pass mới dọn dẹp cluster hiện tại.
5.  Chọn môi trường triển khai.
6.  Build image và kiểm thử Kubernetes một lượt có mục tiêu.
7.  Kubernetes pass thì chuyển Cloud deployment.

Không triển khai Kubernetes/Cloud trong lúc đang hoàn thiện logic AI
local.

## 3. Chống over-engineering

-   Chọn giải pháp đơn giản nhất đáp ứng yêu cầu.
-   Tái sử dụng module, service, schema và database hiện có.
-   Không refactor phần đang chạy nếu không có lỗi hoặc nhu cầu cụ thể.
-   Không tự ý thêm layer, abstraction, repository, service, model hoặc
    bảng database chỉ để "đẹp kiến trúc".
-   Không tạo bảng `incident_diagnoses` trong MVP nếu chưa chứng minh
    cần persistence riêng; trước mắt có thể truyền `DiagnosisAnalysis`
    trực tiếp sang Telegram.
-   Không thêm API Gateway, Redis, Kafka, service mesh, LangChain hoặc
    LangGraph trong phạm vi hiện tại.
-   Không thêm PostgreSQL container nếu database hiện tại đáp ứng.
-   Không mở rộng cluster/monitoring chỉ để kiểm tra một thay đổi nhỏ.

## 4. Incident lifecycle --- phải giữ nguyên

`IncidentService` hiện tại: - `firing` với fingerprint mới: tạo
Incident, action `created`. - `firing` với fingerprint đang active: cập
nhật `last_seen`, action `updated`. - `resolved` với Incident active:
cập nhật trạng thái, action `resolved`. - `resolved` không có Incident
active hoặc trạng thái không hỗ trợ: action `ignored`.

Giữ nguyên advisory transaction lock theo fingerprint, unique partial
index `uq_incident_active_fingerprint`, transaction và xử lý duplicate
firing. Không sửa lifecycle nếu chưa xác định lỗi cụ thể.

## 5. Quy tắc kích hoạt diagnosis

  Action       Hành vi
  ------------ -------------------------
  `created`    Chạy diagnosis
  `updated`    Không diagnosis lại
  `resolved`   Chỉ cập nhật trạng thái
  `ignored`    Không diagnosis

Mục tiêu là tránh thu thập evidence và gọi Gemini nhiều lần do
Alertmanager gửi update cho cùng fingerprint. Không tự thêm retry tự
động hoặc diagnosis định kỳ.

## 6. AI Diagnosis Pipeline

Luồng mục tiêu:

`Alertmanager payload → AlertProcessor → IncidentService → DiagnosisService → Evidence Collection → Evidence Validation → Rule-based Diagnosis → Gemini → DiagnosisAnalysis → Telegram`.

-   Thu thập evidence một lần cho mỗi lượt diagnosis.
-   Rule-based diagnosis là nền tảng; Gemini bổ sung phân tích và đề
    xuất.
-   Gemini dùng cùng evidence snapshot, không tự thu thập dữ liệu riêng.
-   Gemini lỗi, timeout, quota hoặc không khả dụng thì vẫn giữ kết quả
    rule-based và trả `ai_diagnosis.status = unavailable`.
-   AI unavailable không đồng nghĩa toàn bộ diagnosis thất bại.
-   Diagnosis lỗi không được làm mất Incident đã tạo.
-   `updated` không được vô tình gọi Gemini lại.

## 7. Telegram và quyền Manager

Telegram MVP: - Gửi Incident và kết quả diagnosis. - Hiển thị probable
cause, severity/confidence, evidence và investigation steps. - Nhận yêu
cầu điều tra khi chức năng đó được triển khai.

An toàn: - Bot Token/Chat ID lấy từ environment/config, không hardcode
hoặc commit. - Giới hạn người được phép tương tác bằng Telegram user ID
allowlist. - AI chỉ đề xuất; không tự thực thi. - Manager phải xác nhận
rõ ràng trước từng hành động. - Chỉ cho phép operation nằm trong
allowlist; không chạy shell/kubectl tùy ý do AI sinh. - Telegram handler
không có Kubernetes credentials. - Gemini/AI không có Kubernetes
credentials. - Nếu có remediation sau này, mỗi hành động cần xác nhận
riêng, hết hạn và có audit.

## 8. Database và persistence

-   Giữ schema `incident_management` và migration Incident hiện tại.
-   Không đổi bảng `incidents` nếu không có yêu cầu cụ thể.
-   Không tạo bảng diagnosis riêng chỉ để lưu output trong MVP; trước
    hết chứng minh pipeline và Telegram.
-   Không lưu raw evidence lớn vào DB khi chưa có nhu cầu.
-   Không chạy migration mới nếu chưa xem xét nội dung và tác động.

## 9. Testing

-   Test nhằm xác minh nghiệp vụ, không phải tăng số lượng.
-   Tái sử dụng test hiện có; không viết lại test suite.
-   Ưu tiên luồng giả lập end-to-end bằng Alertmanager payload.
-   Có thể mock evidence/collectors để kiểm tra orchestration; dùng
    Gemini API và Telegram thật khi kiểm tra tích hợp ngoài.
-   Xác minh tối thiểu: created, duplicate/updated, resolved, Gemini
    unavailable, Telegram delivery.
-   Chỉ thêm test khi bảo vệ hành vi quan trọng chưa được kiểm tra.
-   Chạy test mục tiêu sau thay đổi; regression suite hiện có chạy ở mốc
    hoàn thành, không cần chạy toàn bộ sau mọi chỉnh sửa nhỏ.
-   Không build image/deploy Kubernetes sau mỗi thay đổi code.

## 10. Deployment và tài nguyên

-   Không để cluster chạy/phình to trong lúc phát triển AI nếu không
    cần.
-   Chỉ cleanup cluster sau khi local AI → Telegram pass và đã ghi lại
    thông tin cần giữ.
-   Chỉ build image khi code local đã ổn định.
-   Kubernetes chỉ kiểm thử một lượt có mục tiêu.
-   Kubernetes pass thì triển khai Cloud, tránh lặp vòng thử nghiệm
    không cần thiết.

## 11. Cách cộng tác và sửa code

-   Làm từng bước nhỏ; giải thích mục đích trước khi yêu cầu sửa.
-   Chỉ yêu cầu các file liên quan, không yêu cầu dump cả repository nếu
    không cần.
-   Đọc code thực tế trước khi đề xuất interface; không đoán tên hàm,
    constructor hoặc schema.
-   Đưa thay đổi tối thiểu, chỉ rõ file cần sửa.
-   Không tự ý đổi tên, di chuyển hoặc xóa module đang hoạt động.
-   Không đưa nhiều hướng kiến trúc khi MVP đã có hướng rõ.
-   Không chuyển sang deployment khi người dùng đang yêu cầu hoàn thiện
    AI.
-   Nếu có nguy cơ trễ deadline, chọn phương án đơn giản hơn và nói rõ
    trade-off.

## 12. Tiêu chí hoàn thành AI Service MVP

-   Nhận Alertmanager payload giả lập.
-   Tạo/cập nhật Incident đúng lifecycle.
-   Thu thập và validate evidence.
-   Chạy rule-based diagnosis.
-   Gọi Gemini và parse output đúng schema.
-   Graceful degradation khi Gemini unavailable.
-   Gửi kết quả diagnosis đến Telegram Manager.
-   Không gọi Gemini lặp với duplicate firing.
-   Không diagnosis mới cho resolved.
-   Các test hiện có liên quan vẫn pass.

Chỉ sau khi đạt các tiêu chí trên mới chuyển sang Kubernetes và Cloud.
