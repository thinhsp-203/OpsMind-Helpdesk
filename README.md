# OpsMind Helpdesk — Hệ thống Helpdesk RAG Hỗ trợ Xử lý Sự cố CNTT

Hệ thống Service Desk CNTT nội bộ tích hợp RAG (Retrieval-Augmented Generation) với giao diện song ngữ Việt / Anh: quản lý vòng đời ticket, SLA thông minh, phân loại sự cố tự động, tra cứu tri thức nội bộ có đối chiếu nguồn và quản trị runbook chuẩn quy trình.

---

## 1. Hướng dẫn chạy nhanh

### Chạy local trên Windows (SQLite)

```powershell
# 1. Tạo và kích hoạt môi trường ảo
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Cài đặt thư viện
py -m pip install -r requirements.txt

# 3. Thiết lập biến môi trường (hoặc copy từ .env.example)
$env:SECRET_KEY = "thay-bang-khoa-bi-mat-dai-ngau-nhien-it-nhat-32-ky-tu"
$env:DEMO_MODE = "true"  # Bật nếu muốn hiển thị tài khoản demo trên màn hình đăng nhập

# 4. Khởi chạy server
py -m uvicorn app.main:app --reload
```

Mở trình duyệt tại `http://127.0.0.1:8000`. Tài liệu API Swagger tại `http://127.0.0.1:8000/docs`.

### Tài khoản mẫu (khi bật `DEMO_MODE=true`)

| Vai trò | Tên đăng nhập | Mật khẩu mặc định | Quyền hạn chính |
|---|---|---|---|
| **Nhân viên (User)** | `user` | `user` | Tra cứu RAG, gửi ticket, theo dõi tiến độ, trao đổi, đánh giá hài lòng |
| **IT Support (Agent)** | `agent` | `agent` | Tiếp nhận hàng đợi, phân loại SLA, phản hồi ticket, soạn thảo Runbook tri thức, gửi duyệt bài viết |
| **Quản trị IT (Admin)** | `admin` | `admin` | Phê duyệt & xuất bản Runbook, khôi phục phiên bản, quản lý người dùng, đặt lại mật khẩu, xuất báo cáo |

### Nạp dữ liệu mô phỏng thực tế phục vụ Demo / Bảo vệ đồ án

Hệ thống cung cấp script nạp tự động 20 sự cố thực tế đa dạng trạng thái, mức ưu tiên, đính kèm tệp và lịch sử tra cứu:

```powershell
# Nạp 20 ticket mẫu, 6 tài khoản phòng ban và lịch sử RAG:
py scripts/seed_demo_data.py --reset
```

| Tài khoản | Mật khẩu mẫu | Vai trò & Phòng ban | Mục đích trong kịch bản demo |
|---|---|---|---|
| `admin` | `OpsMindAdmin2026!` | Quản trị viên IT (IT Operations) | Duyệt xuất bản Runbook, quản lý phân quyền, xem Analytics |
| `agent_nam` | `AgentPass2026!` | Kỹ thuật viên (Hạ tầng & Mạng) | Tiếp nhận hàng đợi, xử lý sự cố LAN/Wi-Fi/VPN, tạo Runbook |
| `agent_hoa` | `AgentPass2026!` | Kỹ thuật viên (Hệ thống & Phần mềm) | Xử lý sự cố Outlook/Active Directory/Phần mềm kế toán |
| `user_linh` | `UserPass2026!` | Nhân viên (Phòng Kế toán) | Hỏi RAG máy in/hóa đơn, tạo ticket sự cố, đánh giá 5 sao |
| `user_tuan` | `UserPass2026!` | Nhân viên (Phòng Kinh doanh) | Tra cứu VPN, phản hồi ticket đang xử lý |
| `user_mai` | `UserPass2026!` | Nhân viên (Phòng Nhân sự) | Gặp lỗi Outlook đầy hòm thư, gửi phản hồi |

---

### Chạy bằng Docker Compose (PostgreSQL cục bộ)

```powershell
docker compose up --build
```

Docker Compose sẽ tự động khởi tạo:
- Dịch vụ **PostgreSQL 16** với cơ chế bảo toàn dữ liệu qua volume `postgres_data`.
- Ứng dụng **OpsMind Helpdesk** tại cổng `8000`.
- Tách biệt thư mục lưu trữ tài liệu người dùng tải lên (`/app/data/storage`) với bộ tri thức gốc của hệ thống (`/app/data/knowledge`), đảm bảo dữ liệu không bị ghi đè khi mount volume.

---

### Tích hợp CSDL Đám mây Neon Serverless Postgres (Khuyên dùng cho Render / Cloud)

Hệ thống hỗ trợ hoàn hảo **Neon Serverless Postgres** ([neon.tech](https://neon.tech)) với cơ chế tự động tương thích PgBouncer Connection Pooling (`prepare_threshold=None`) và SSL Mode:

1. **Lấy chuỗi kết nối từ Neon:**
   - Đăng nhập vào [console.neon.tech](https://console.neon.tech), chọn Project của bạn.
   - Tại mục **Connection Details**, chọn **Pooled connection** (URL chứa `-pooler` và `sslmode=require`).
   - Copy chuỗi kết nối dạng: `postgresql://user:password@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require`

2. **Kiểm tra kết nối và khởi tạo CSDL tự động:**
   ```powershell
   py scripts/verify_neon.py "chuoi-ket-noi-neon-cua-ban"
   ```
   Script sẽ tự động kiểm tra SSL, đồng bộ Schema, nạp sẵn 30 Runbook doanh nghiệp vào bảng `knowledge_documents` và chạy thử nghiệm ghi/đọc.

3. **Cấu hình trên Render Cloud:**
   - Vào Render Dashboard → Chọn Web Service `opsmind-helpdesk` → Tab **Environment**.
   - Thêm biến môi trường:
     - `DATABASE_URL`: Dán chuỗi kết nối Neon Pooled của bạn.
     - `DEMO_MODE`: `false` (để bảo vệ dữ liệu sản phẩm) hoặc `true` (nếu cần tài khoản demo).
     - `INITIAL_ADMIN_PASSWORD`: Mật khẩu quản trị viên ban đầu (ít nhất 12 ký tự).
   - Render sẽ tự động redeploy và kết nối trực tiếp với CSDL Neon!

4. **Chạy Local kết nối Neon:**
   - Thêm vào file `.env`:
     ```env
     DATABASE_URL=postgresql://user:password@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```
   - Chạy `py -m uvicorn app.main:app --reload`

---

## 2. Các chức năng chính của hệ thống

### 2.1. Quản trị Kho tri thức (Knowledge Base) & Quy trình duyệt Runbook
- **Lưu trữ CSDL & Tự động Seed:** Kho tri thức được lưu trữ trong CSDL (`knowledge_documents` và `knowledge_versions`), tự động nạp sẵn 30 runbook sự cố doanh nghiệp chuẩn hóa. Loại bỏ hoàn toàn sự phụ thuộc vào các dictionary viết cứng trong mã nguồn.
- **Trình soạn thảo Markdown trực quan (Live Preview):**
  - Hỗ trợ đầy đủ cú pháp Markdown: Heading, In đậm, Danh sách, Code snippet, Bảng biểu.
  - Khung xem trước thời gian thực (Split-view Live Preview) song song với ô soạn thảo.
  - Phân loại danh mục động (`network`, `hardware`, `software`, `security`, `general`) cùng hệ thống thẻ từ khóa (`tags`).
- **Quy trình kiểm duyệt 2 lớp (Review Workflow):**
  - Kỹ thuật viên (Agent) soạn thảo bản nháp (`draft`) và gửi yêu cầu phê duyệt (`pending_review`).
  - Quản trị viên (Admin) xem xét, phê duyệt xuất bản (`published`) hoặc trả về bản nháp kèm ghi chú phản hồi.
  - Người dùng cuối chỉ tra cứu các tài liệu đã được chính thức xuất bản.
- **Quản lý phiên bản & Khôi phục (Version Control):**
  - Tự động ghi lại lịch sử chỉnh sửa chi tiết: mã phiên bản (v1, v2...), người sửa, thời điểm và tóm tắt thay đổi.
  - Admin có thể so sánh và khôi phục (Restore) về bất kỳ phiên bản nào trong quá khứ chỉ với 1 cú click.
- **Đóng vòng sự cố (Ticket-to-Knowledge Loop):**
  - Kỹ thuật viên có thể chuyển đổi trực tiếp một ticket sự cố đã giải quyết thành bản nháp Runbook mới với nội dung trích xuất tự động từ quá trình xử lý thực tế.

### 2.2. Động cơ RAG & Trợ lý Tra cứu Sự cố CNTT
- **Tìm kiếm ngữ cảnh BM25:** Chỉ mục toàn văn trên tài liệu Markdown có hỗ trợ tiếng Việt, chuẩn hóa từ khóa và trích dẫn nguồn tham chiếu minh bạch.
- **Gợi ý phân loại tự động (Auto-Triage):**
  - Tự động đề xuất Danh mục (Category) và Mức độ ưu tiên (Priority) dựa trên tài liệu liên quan nhất và mức độ ảnh hưởng nghiệp vụ.
  - IT Support có thể chèn trích đoạn hướng dẫn từ RAG trực tiếp vào ô phản hồi của ticket chỉ với một nút bấm.
- **Chuyển tiếp thành Ticket không cần gõ lại:** Khi hướng dẫn tự phục vụ chưa giải quyết được vấn đề, người dùng có thể bấm chuyển trực tiếp câu hỏi và ngữ cảnh đã tra cứu thành yêu cầu IT.
- **Lịch sử tra cứu & Đánh giá chất lượng:** Lưu vết lịch sử theo từng tài khoản, hỗ trợ phản hồi độ hữu ích 👍 / 👎 để phát hiện khoảng trống tri thức.

### 2.3. Quản lý Ticket & Vòng đời Xử lý Sự cố
- **Hàng đợi IT thông minh:** Bộ lọc đa chiều theo mức độ khẩn cấp, quá hạn SLA, trạng thái chưa phân công hoặc ticket được giao cho tôi.
- **Cam kết chất lượng dịch vụ (SLA):** Thời hạn xử lý tính toán tự động theo mức ưu tiên: Khẩn cấp (2h), Cao (8h), Thông thường (24h), Thấp (48h), kèm đồng hồ đếm ngược trực quan.
- **Trao đổi & Đính kèm tệp:** Hỗ trợ bình luận 2 chiều giữa nhân viên và IT Support; đính kèm ảnh chụp màn hình/log lỗi (PNG, JPG, TXT, LOG) tối đa 10 MiB có kiểm soát quyền truy cập.
- **Audit Log minh bạch:** Lưu trữ toàn bộ lịch sử thay đổi trạng thái, phân công và thao tác trên ticket.
- **Khảo sát mức độ hài lòng (CSAT):** Đánh giá sao (1–5 sao) và phản hồi sau khi ticket được giải quyết.

### 2.4. An toàn thông tin & Quản trị định danh (Security Hardening)
- **Cơ chế chống dò quét đăng nhập (Rate Limiting):** Tự động khóa tạm thời và trả mã HTTP 429 nếu đăng nhập sai quá 5 lần trong vòng 15 phút.
- **Chống Timing Attack:** Sử dụng dummy password hash khi kiểm tra các tài khoản không tồn tại, ngăn chặn kỹ thuật timing-based user enumeration.
- **Chính sách mật khẩu nghiêm ngặt:** Bắt buộc độ dài tối thiểu 12 ký tự cho mọi tài khoản.
- **Đổi mật khẩu & Thu hồi Token tức thì:** Token JWT tự động bị vô hiệu hóa ngay khi người dùng đổi mật khẩu thông qua cơ chế kiểm tra thời điểm cấp token (`pwd_at`).
- **Buộc đổi mật khẩu (Force Password Change):** Admin có thể đặt lại mật khẩu tạm cho nhân viên kèm cờ bắt buộc đổi mật khẩu ở lần đăng nhập tiếp theo.

---

## 3. Kiểm thử & Đánh giá chất lượng

Hệ thống được kiểm thử tự động toàn diện qua cả tầng Backend API (Python) và Frontend Client (Node.js):

```powershell
# Chạy toàn bộ test suite backend (50+ tests)
py -m pytest

# Kiểm tra độ bao phủ mã nguồn (Coverage)
py -m pytest --cov=app --cov-report=term-missing

# Chạy kiểm thử Client-side UI, Handoff & Song ngữ (Node.js)
node tests/test_queue.js
node tests/test_handoff.js
node tests/test_i18n.js

# Đánh giá độ chính xác của bộ RAG Baseline
py -m scripts.evaluate_rag
```

---

## 4. Tài liệu học thuật & Tham khảo đồ án

- [Báo cáo bối cảnh đề tài](docs/BAO_CAO_BOI_CANH.md): Phân tích bài toán, stakeholder, đối sánh Jira / GLPI / ServiceNow.
- [Đặc tả yêu cầu phần mềm (SRS)](docs/SRS.md): Danh mục Use Cases, Acceptance Criteria và NFR.
- [Thiết kế kiến trúc hệ thống (SDD)](docs/SDD.md): Biểu đồ kiến trúc, CSDL (ERD), FSM chuyển trạng thái và tài liệu API.
- [Ma trận truy vết kiểm thử](docs/TEST_TRACEABILITY.md): Ma trận đối chiếu yêu cầu phần mềm và các ca kiểm thử tự động.
- [Hướng dẫn sử dụng chi tiết](docs/USER_GUIDE.md): Cẩm nang thao tác cho Nhân viên, Kỹ thuật viên IT và Quản trị viên.
- [Hướng dẫn triển khai hệ thống](docs/DEPLOYMENT.md): Thiết lập biến môi trường, Docker, reverse proxy và sao lưu dữ liệu.
- [Kế hoạch thực nghiệm RAG & Khảo sát SUS](docs/KE_HOACH_THUC_NGHIEM.md): Phương pháp đánh giá thực nghiệm và đo lường sự hài lòng.

---

## 5. Giới hạn học thuật cần lưu ý khi báo cáo bảo vệ

1. **Bản chất Prototype:** Hệ thống được thiết kế phục vụ đề tài khóa luận tốt nghiệp, ưu tiên tính minh bạch học thuật, kiểm chứng được nguồn trích dẫn và tối ưu tài nguyên vận hành.
2. **Mô hình truy xuất:** Hệ thống mặc định sử dụng giải thuật BM25 kết hợp tiền xử lý tiếng Việt chuyên sâu cho môi trường nội bộ không phụ thuộc Internet. Khi cấu hình khóa API LLM, hệ thống có khả năng tổng hợp câu trả lời tự động với cơ chế kiểm soát hallucination.
3. **Cơ chế kênh thông báo:** Phiên bản hiện tại tập trung hoàn thiện trải nghiệm web portal tập trung, hỗ trợ tích hợp mở rộng sang Telegram webhook cho các giai đoạn tiếp theo.
