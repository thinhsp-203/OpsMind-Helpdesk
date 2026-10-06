# Rà soát tài liệu bổ sung đầu vào

**Phạm vi:** đối chiếu `SUPPLEMENT_GUIDE.md` được gửi kèm với mã nguồn và tài liệu prototype trong repository. Bản đính kèm là tài liệu tham khảo, không được chép nguyên trạng vào đồ án vì chứa giả định kiến trúc và số liệu thị trường chưa có nguồn kiểm chứng.

## Kết luận

Giữ cách tiếp cận thận trọng: mô tả hệ thống là prototype FastAPI + PostgreSQL trong Compose hoặc SQLite cho local development/test, HTML/CSS/JavaScript có giao diện Việt/Anh, truy xuất BM25 trên Markdown, có citation và heuristic triage có xác nhận. Không tuyên bố sinh đáp án LLM/RAG vector hoặc chất lượng production chỉ để khớp checklist mẫu.

## Đối chiếu các luận điểm chính

| Nội dung trong tài liệu đính kèm | Đối chiếu với repository | Xử lý |
|---|---|---|
| Bảng giá JSM, Freshdesk, ServiceNow; kết luận giải pháp cạnh tranh rẻ hơn hoặc lấp “khoảng trống thị trường” | Chưa có cùng gói, ngày/đơn vị tính, thuế/tỷ giá, self-host cost, chi phí triển khai/bảo trì hoặc benchmark tính năng được xác minh | Không đưa con số/kết luận tiết kiệm vào báo cáo. `BAO_CAO_BOI_CANH.md` chỉ giữ đối chiếu phạm vi có giới hạn và ghi rõ chưa benchmark |
| Các số 42%, 28 phút/ngày, giảm 60%, 67% SME Việt Nam | Tài liệu đính kèm không cung cấp trích dẫn có thể kiểm tra (tên báo cáo đầy đủ, trang/bảng, mẫu, phương pháp); “khảo sát nội bộ” không đi kèm dữ liệu hay biên bản | Không dùng làm kết quả/sự thật. Chỉ bổ sung sau khi truy được nguồn gốc hoặc tự khảo sát có consent, phương pháp, cỡ mẫu và kết quả thật |
| RAG built-in, source citations, tiếng Việt hoàn toàn, PDF/DOCX, tự host production, phản hồi ≤3 giây, cảnh báo SLA realtime | Phần này không khớp implementation: retrieval là BM25 lexical trên Markdown; chưa có LLM/embedding/streaming, PDF/DOCX, push notification hay benchmark API/performance | Không nhận các mô tả này. Tài liệu hiện tại giới hạn rõ tính năng và số đo local |
| Giá license 0 USD và hosting 10–20 USD/tháng | Chưa có quote/estimate hạ tầng, chi phí vận hành, nhân lực hoặc security hardening | Không công bố chi phí tổng sở hữu hoặc tiết kiệm |
| Celery/Redis, PostgreSQL/pgvector, Chroma, MinIO, WebSocket, email và Next.js | Compose nay có PostgreSQL cho dữ liệu quan hệ; chưa có pgvector, Celery/Redis, Chroma, MinIO, WebSocket, email hay Next.js | Chỉ xem các dịch vụ còn thiếu là lựa chọn tương lai nếu có yêu cầu đã xác nhận, thiết kế/migration, tiêu chí vận hành và test |
| AI Usage Log, test plan, deployment/user guide, API docs | AI usage log, kế hoạch thực nghiệm, ma trận truy vết, baseline, SDD và OpenAPI `/docs` đã có. Thiếu hướng dẫn thao tác role-based, triển khai demo end-to-end và quy tắc đóng góp | Bổ sung `USER_GUIDE.md`, `DEPLOYMENT.md` và `CONTRIBUTING.md`; SUS report không được tạo khi chưa có người tham gia |
| Tối thiểu 30 runbook | Hiện repository có 9 runbook và 30 câu hỏi đánh giá nháp; số lượng không phải bằng chứng chất lượng/độ phủ | Ghi đúng 9 runbook; chỉ mở rộng theo tài liệu được phép sử dụng, rà soát và gán ground truth |
| Checklist có streaming, Kanban, WebSocket, staging và CI xanh | Các mục này chưa được triển khai hoặc kiểm chứng trong repo | Không biến checklist thành trạng thái đạt. Kiểm tra workflow trên GitHub và lưu run/artifact trước khi báo cáo CI là đã chạy |
| Lệnh push thẳng `main`, Compose dùng mật khẩu minh họa cố định, `docker compose down -v` | Không an toàn nếu áp dụng cho repo/dữ liệu có giá trị; lệnh cuối xóa volume dữ liệu | Dùng nhánh tính năng/PR; tạo secret riêng; chỉ xóa volume khi đã xác nhận dữ liệu có thể bỏ |

## Bổ sung hữu ích đã đưa vào

- `USER_GUIDE.md`: các thao tác thực tế theo ba vai trò, gồm tra cứu/bàn giao, xử lý ticket, Admin và các giới hạn bảo mật.
- `DEPLOYMENT.md`: chạy local/Compose, biến môi trường thực tế, bootstrap tài khoản non-demo, dữ liệu persistent và lưu ý backup.
- `CONTRIBUTING.md`: setup, lệnh kiểm tra, quy tắc nhánh/PR và ngăn dữ liệu/secrets/generated artifacts vào Git.
- README liên kết tới các tài liệu mới để người chấm và người chạy demo tìm được.

## Thứ tự ưu tiên nếu mở rộng sau này

1. **Trước demo học thuật:** kiểm tra workflow CI thật; diễn tập user guide trên dữ liệu giả; chốt G1 với GVHD; nhờ IT duyệt runbook/ground truth. Hoàn thành test usability chỉ khi có người tham gia và ghi nhận đúng protocol.
2. **Trước pilot có dữ liệu thật:** threat model, TLS/secret handling, rate limiting, audit thay đổi quyền, malware scan/retention cho attachment, backup/restore và quy trình phản ứng sự cố. Đây là yêu cầu an toàn cần thiết; không thể thay thế bằng một thư viện hoặc bảng checklist.
3. **Chỉ khi có nhu cầu/đo đạc:** email/in-app notifications, background queue, object storage, PostgreSQL production migration/HA/backup hoặc search nâng cao. Định nghĩa yêu cầu, chủ sở hữu dữ liệu, migration, chi phí và rollback trước khi chọn công nghệ.
4. **Không thêm vào phạm vi hiện tại nếu không đổi đề tài/đánh giá:** LLM generation, embeddings/vector DB, Ragas-as-answer-evaluation. Muốn chấm faithfulness/answer relevance phải có câu trả lời được sinh, bộ ground truth được chuyên gia duyệt, judge/protocol và disclosure chi phí/model; hit@3 hiện tại không thay thế các phép đo đó.

## Nguồn bằng chứng trong repo

- Khả năng/giới hạn prototype: `README.md`, `docs/DOI_CHIEU_FEATURES_AND_UI.md`, `docs/SDD.md`, `docs/SRS.md`.
- Kết quả retrieval và điều kiện diễn giải: `docs/RAG_BASELINE.md`, `docs/KE_HOACH_THUC_NGHIEM.md`, `data/evaluation/rag_questions.csv`.
- Các rủi ro còn mở: `docs/DEFECT_TECH_DEBT_LOG.md`, đặc biệt staging, user study, rate limiting/hardening, backup, tải và attachment scanning.
