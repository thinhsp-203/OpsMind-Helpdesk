# Báo Cáo Tiến Độ Tuần — Đề Tài Khóa Luận Tốt Nghiệp

**Đề tài:** Xây dựng Hệ thống Service Desk Nội bộ Tích hợp RAG Hỗ trợ Tự phục vụ Sự cố CNTT (OpsMind Helpdesk)  
**Sinh viên thực hiện:** Nhóm sinh viên thực hiện đồ án  
**Giảng viên hướng dẫn:** Giảng viên hướng dẫn  
**Ngày báo cáo:** 14/10/2026  
**Nội dung phản hồi góp ý của GVHD tuần trước:** *"Trong tuần tới bổ sung lại phạm vi thực hiện của đề tài, cụ thể các yêu cầu, chức năng sẽ làm, đối tượng sử dụng"*

---

## 1. Tiếp thu và Làm rõ Góp ý của Giảng viên Hướng dẫn

Thực hiện ý kiến chỉ đạo của Thầy/Cô, nhóm đã rà soát toàn bộ tài liệu đặc tả [SRS.md](file:///E:/OpsMind-Helpdesk/docs/SRS.md) và [SDD.md](file:///E:/OpsMind-Helpdesk/docs/SDD.md), đồng thời đối chiếu với **Rubric chấm điểm đồ án (Tiêu chí TC1 và TC2.1)** để chuẩn hóa 3 nội dung trọng tâm:

### 1.1. Phạm vi thực hiện đề tài (Scope Definition)
Nhóm phân định rõ ràng giữa **Phần làm (In-scope)** và **Phần không làm (Out-of-scope)** để tránh phân tán tài nguyên và đảm bảo tính khả thi cao nhất:

- **Phần thực hiện (In-Scope):**
  1. *Cổng tự phục vụ & RAG:* Tra cứu sự cố tiếng Việt/Anh có đối chiếu nguồn runbook; gợi ý phân loại (Category) và mức độ ưu tiên (Priority) theo luật nghiệp vụ; cơ chế từ chối an toàn khi ngoài phạm vi; chuyển tiếp ngữ cảnh (Ticket Handoff).
  2. *Vòng đời Sự cố (Incident Lifecycle):* Hàng đợi thông minh; máy trạng thái FSM 6 trạng thái (`new`, `in_progress`, `pending_waiting_user`, `resolved`, `closed`, `escalated`); cam kết thời hạn SLA 4 cấp (2h, 8h, 24h, 48h); trao đổi 2 chiều và đính kèm tệp tin log/ảnh.
  3. *Quản trị Kho Tri thức (Knowledge Base):* Soạn thảo Markdown với Live Preview chia đôi màn hình; quy trình kiểm duyệt 2 lớp (`draft` $\rightarrow$ `pending_review` $\rightarrow$ `published`); quản lý lịch sử phiên bản và khôi phục (Restore); đóng vòng sự cố từ Ticket sang Runbook mới.
  4. *An toàn thông tin & Quản trị định danh:* Chống tấn công dò quét (Rate limiting 5 lần/15 phút); chống Timing Attack; chính sách mật khẩu mạnh $\ge$ 12 ký tự; đổi mật khẩu và vô hiệu token cũ tức thì (`pwd_at`); buộc đổi mật khẩu lần đầu (`force_password_change`); quên mật khẩu qua Email.
  5. *Thông báo Đa kênh:* Tự động gửi cảnh báo sự cố mới và chuyển cấp khẩn cấp qua Telegram Bot và Discord Webhook.
  6. *Báo cáo & Giám sát:* Dashboard SLA compliance theo Agent, đánh giá hài lòng CSAT 1–5 sao và Audit Log bất biến.

- **Phần không thực hiện / Giới hạn đề tài (Out-of-Scope):**
  1. Không tích hợp SSO/SAML/LDAP doanh nghiệp bên ngoài (Azure AD, Okta); sử dụng hệ thống xác thực nội bộ mã hóa PBKDF2-SHA256 chuẩn NIST.
  2. Không tích hợp module quét virus thời gian thực; áp dụng kiểm soát an toàn bằng danh sách trắng định dạng (PNG, JPG, TXT, LOG) và giới hạn dung lượng $\le$ 10 MiB.
  3. Không tính toán SLA theo ca kíp/ngày nghỉ lễ phức tạp; áp dụng SLA giờ lịch (Calendar Hours) phục vụ mô phỏng thực nghiệm.
  4. Không mở cổng thoại tổng đài VoIP hoặc kết nối trả phí với WhatsApp/Viber doanh nghiệp do chi phí và thủ tục cấp phép nhà mạng.

---

### 1.2. Đối tượng sử dụng và Chân dung người dùng (Personas)

| Nhóm đối tượng | Chân dung & Bối cảnh nghiệp vụ | Nhu cầu chính & Quyền hạn |
|---|---|---|
| **1. Nhân viên nội bộ (End-user / Employee)** | Cán bộ, nhân viên văn phòng thuộc các phòng ban (Kế toán, Kinh doanh, Nhân sự...). Trình độ CNTT cơ bản đến trung bình, thường gặp sự cố máy in, Wi-Fi, phần mềm, email hoặc tài khoản khi đang làm việc. | - Tra cứu nhanh cách tự xử lý qua Trợ lý RAG.<br>- Tạo ticket hỗ trợ khi không tự giải quyết được.<br>- Theo dõi trạng thái, trao đổi với IT và đánh giá sao hài lòng (CSAT). |
| **2. Kỹ thuật viên IT (IT Support / Agent)** | Cán bộ kỹ thuật IT Support phụ trách tiếp nhận, phân loại và giải quyết các sự cố máy trạm, mạng nội bộ, ứng dụng. | - Xem hàng đợi tập trung, nhận vé theo chuyên môn.<br>- Dùng RAG Assist chèn nhanh cách giải quyết vào phản hồi.<br>- Chuyển đổi ticket đã xử lý thành bản nháp Runbook tri thức mới. |
| **3. Quản trị viên IT (IT Administrator)** | Trưởng phòng CNTT hoặc Quản trị viên hệ thống. Chịu trách nhiệm bảo đảm chất lượng dịch vụ, phê duyệt tài liệu và bảo mật hệ thống. | - Phê duyệt xuất bản bài viết Runbook mới, kiểm soát phiên bản.<br>- Quản lý tài khoản, phân quyền, đặt lại mật khẩu cưỡng bức.<br>- Cấu hình kênh thông báo Telegram/Discord; theo dõi Dashboard SLA & CSAT. |

---

### 1.3. Cụ thể hóa 26 Yêu cầu chức năng (FR) và 5 KPI định lượng

- **26 Yêu cầu chức năng (FR-01 $\rightarrow$ FR-26):** Đã được chi tiết hóa trong [mục 4 của tài liệu SRS.md](file:///E:/OpsMind-Helpdesk/docs/SRS.md#4-yêu-cầu-chức-năng-chi-tiết), gắn với từng phân hệ cụ thể và có Acceptance Criteria (Given/When/Then) truy vết được.
- **5 KPI nghiệp vụ định lượng (Cam kết trước mốc 50% theo Quy tắc G1 của Rubric):**
  - **KPI-01:** Độ chính xác truy xuất RAG (Context Hit@3) $\ge 90\%$ trên tập kiểm thử độc lập (Holdout set).
  - **KPI-02:** Tỷ lệ tuân thủ cam kết SLA $\ge 85\%$ trên tổng số ticket giải quyết (chuẩn ITIL, bảo lưu deadline khi cập nhật ticket).
  - **KPI-03:** Tỷ lệ từ chối an toàn các câu hỏi ngoài phạm vi $\ge 80\%$ trên tập Holdout, tỷ lệ chặn nhầm $\le 5\%$ (không bịa thông tin và không chặn nhầm câu hỏi IT).
  - **KPI-04:** Thời gian phản hồi truy vấn RAG (Latency p95): Truy xuất BM25 $\le 100\text{ ms}$; toàn trình qua LLM $\le 3000\text{ ms}$.
  - **KPI-05:** Điểm đánh giá mức độ hài lòng người dùng thực tế (CSAT / SUS) $\ge 70/100$ điểm (Mức Khá/Chấp nhận được theo thang chuẩn Brooke 1996).

---

## 2. Tiến độ Triển khai Kỹ thuật Tuần này

2. **Hạ tầng CSDL, Email & Triển khai Đám mây:**
   - Tích hợp thành công CSDL **Neon Serverless Postgres** (Singapore) tương thích connection pooling PgBouncer (`prepare_threshold=None`) và SSL Mode.
   - Triển khai dịch vụ Web thành công lên **Render Cloud** (Live, pass health check tự động).
   - **Xử lý điểm nghẽn gửi email trên Render Free:** Render chặn cổng SMTP đi ra (25/465/587); đã xây dựng kiến trúc gửi email đa nhà cung cấp qua HTTPS API (Brevo API, Resend API, Webhook, Mock/Console) tại cổng 443 và Mailpit trong Docker Compose cho local. Gửi thành công email đặt lại mật khẩu và email tài khoản mới có mật khẩu tạm.
   - Sửa lỗi hiển thị và lọc danh mục tại trang Kho tri thức & Runbook (bổ sung CSS select, `autocomplete="off"`, đồng bộ DOM state).
   - Xử lý lỗi tự động đăng nhập khi đang khôi phục mật khẩu (xóa sạch session cũ khi vào luồng reset, ngăn browser sleep reload gây auto-login).
3. **Kiến trúc & Tái cấu trúc mã nguồn (Refactoring & Modularization):**
   - **Tách nhỏ backend thành APIRouters:** Chuyển đổi tệp monolithic `main.py` (>1.500 dòng) thành các router chuyên biệt theo miền nghiệp vụ trong `app/routers/` (`auth.py`, `tickets.py`, `knowledge.py`, `rag.py`, `admin.py`, `analytics.py`), tách `schemas.py` và `dependencies.py`, giữ `main.py` dưới 180 dòng.
   - **Module hóa frontend:** Tách `app.js` (>2.600 dòng) thành các module JavaScript độc lập trong `app/static/modules/` (`markdown.js`, `notifications.js`, `admin.js`, `knowledge.js`), bảo toàn 100% anchor điểm neo kiểm thử.
   - **Chuyển Rate Limiting sang CSDL:** Chuyển bộ đếm tần suất và lockout từ RAM sang bảng `rate_limit_attempts` (hỗ trợ cả SQLite và PostgreSQL), bảo đảm duy trì lockout khi restart máy chủ.
   - **Bổ sung script đo tải thực nghiệm:** Xây dựng `scripts/benchmark_load.py` kiểm chứng chỉ tiêu NFR-02 (số đo cũ 35 – 597 RPS chưa hợp lệ để xác nhận NFR-02; đính chính 29/10/2026: token benchmark cũ không đáp ứng xác thực hiện tại, cần chạy lại qua HTTP thật).
4. **Chất lượng Phần mềm (Đạt chuẩn Rubric TC2.4, TC2.5, TC2.6):**
   - 100% test case tự động pass (82/82 pytest backend pass, 3/3 bộ test Node.js frontend pass, GitHub Actions CI pass 100%).
   - Chuẩn hóa song ngữ Anh - Việt cho toàn bộ thông báo xác thực và lỗi validation của hệ thống.
   - 0 lỗi lint (Ruff pass 100%), 0 secret bị lộ trong mã nguồn.

---

## 3. Kế hoạch Tuần Tiếp Theo

1. Tổ chức thử nghiệm người dùng nội bộ đợt 1 để thu thập phiếu khảo sát SUS phục vụ minh chứng cho Tiêu chí TC2.7 của Rubric.
2. Hoàn thiện các ca kiểm thử E2E giao diện người dùng (User / Agent / Admin) và chuẩn bị slide báo cáo tiến độ giữa kỳ.
