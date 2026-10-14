# Thiết kế phần mềm (SDD)

**Phiên bản:** 1.0 — khớp prototype hiện tại\
**Stack:** FastAPI, PostgreSQL cho Docker Compose hoặc SQLite cho local development/test, HTML/CSS/JavaScript tĩnh, bộ truy xuất BM25 tối giản.

## 1. Kiến trúc thành phần

```mermaid
flowchart LR
  Browser[Web UI: HTML/CSS/JS] -->|HTTP(S) / JSON API| API[FastAPI]
  API --> Auth[Auth + RBAC + Rate Limit]
  API --> Tickets[Ticket / SLA / Audit]
  API --> RAG[RAG Retrieval: BM25 + Synonyms]
  API --> KBMod[Knowledge Base: 2-stage Review & Versions]
  API --> Notify[Notification Hub: Telegram / Discord]
  API --> Email[Email Sender / Password Reset]
  Tickets --> DB[(PostgreSQL / SQLite)]
  Auth --> DB
  KBMod --> DB
  KBMod --> Markdown[Markdown Runbook Storage]
  Files[Local Attachment Storage] --> API
  RAG --> Markdown
  RAG -->|Trích đoạn + File nguồn| API
  Notify -->|HTTPS Allowlist / Anti-SSRF| ExtChannels[Telegram Bot & Discord Webhook]
```

Trong hệ thống, ứng dụng web và API chạy cùng FastAPI. `DATABASE_URL` chọn PostgreSQL (cho Docker Compose và Cloud Deployment Neon) hoặc SQLite (cho local test). Cơ sở dữ liệu lưu trữ người dùng, ticket, bình luận, audit log, attachment metadata, lịch sử hỏi đáp RAG, token đặt lại mật khẩu và lịch sử phiên bản Runbook. Phân hệ Notification Hub tích hợp Telegram Bot và Discord Webhook với lớp phòng thủ chống SSRF nghiêm ngặt. Phân hệ Email Sender hỗ trợ gửi link khôi phục mật khẩu tự phục vụ một lần. UI hỗ trợ song ngữ Việt - Anh lưu trong browser LocalStorage.

## 2. Sơ đồ ngữ cảnh

```mermaid
flowchart LR
  Employee[Nhân viên] -->|Câu hỏi / ticket / bình luận| System[Helpdesk RAG]
  System -->|Hướng dẫn có trích dẫn / trạng thái ticket| Employee
  Agent[IT Support Agent] -->|Nhận việc / phân công / cập nhật / phản hồi| System
  System -->|Hàng đợi / SLA / lịch sử| Agent
  Admin[IT Admin] -->|Theo dõi vận hành| System
  KB[Runbook Markdown] -->|Tri thức nội bộ| System
```

## 3. Sequence — gợi ý RAG và tạo ticket

```mermaid
sequenceDiagram
  actor U as Người dùng
  participant W as Web UI
  participant A as FastAPI
  participant R as Retriever
  participant K as Knowledge Base
  U->>W: Nhập câu hỏi
  W->>A: POST /rag/ask
  A->>A: Xác thực người dùng
  A->>R: Chuẩn hóa truy vấn và tìm đoạn
  R->>K: Đọc các đoạn Markdown đã index
  K-->>R: Đoạn nội dung + tên file
  R-->>A: BM25, nguồn không trùng, gợi ý category/priority có lý do
  A->>DB: Lưu session, truy vấn, nguồn, câu trả lời
  alt Có đoạn đủ liên quan
    A-->>W: Hướng dẫn + nguồn + relevance
  else Không đủ bằng chứng
    A-->>W: Từ chối suy đoán, đề nghị tạo ticket
  end
  opt Người dùng cần IT can thiệp
    U->>W: Gửi ticket
    W->>A: POST /tickets
    A->>A: Tính SLA + ghi audit
    A-->>W: Ticket mới + hạn xử lý
  end
  opt IT cần xử lý ticket
    Agent->>W: Tra cứu từ tiêu đề/mô tả ticket
    W->>A: POST /rag/ask
    A-->>W: Trích đoạn + nguồn
    Agent->>W: Chèn trích đoạn vào bản nháp bình luận
    Agent->>W: Xác minh/chỉnh sửa rồi chủ động gửi
  end
```

## 4. Sequence — Agent tiếp nhận và xử lý

```mermaid
sequenceDiagram
  actor Agent
  participant UI as Web UI
  participant API as FastAPI
  participant DB as PostgreSQL / SQLite
  Agent->>UI: Đăng nhập
  UI->>API: POST /auth/login
  API-->>UI: JWT có hạn
  Agent->>UI: Giao ticket / đổi trạng thái
  UI->>API: PUT assignment hoặc PATCH status
  API->>API: Kiểm tra role + FSM
  API->>DB: Cập nhật ticket trong transaction
  API->>DB: Ghi audit actor, thời gian, thay đổi
  DB-->>API: Thành công
  API-->>UI: Ticket cập nhật
```

## 5. FSM trạng thái

```mermaid
stateDiagram-v2
  [*] --> new
  new --> in_progress: Agent bắt đầu
  in_progress --> pending_waiting_user: Chờ bổ sung
  pending_waiting_user --> in_progress: Người gửi phản hồi
  in_progress --> escalated: Chuyển cấp
  escalated --> in_progress: Tiếp tục xử lý
  in_progress --> resolved: Đã xử lý
  resolved --> in_progress: Mở lại
  resolved --> closed: Người gửi xác nhận
  closed --> [*]
```

## 6. Các quy trình nghiệp vụ chính

### 6.1. Quy trình quản trị tri thức & Kiểm duyệt 2 lớp

```mermaid
sequenceDiagram
  actor Agent as Kỹ thuật viên (Agent)
  actor Admin as Quản trị viên (Admin)
  participant UI as Web UI
  participant API as FastAPI
  participant DB as PostgreSQL / SQLite
  participant KB as Markdown Storage
  participant RAG as RAG Index

  Agent->>UI: Soạn thảo Runbook Markdown & Live Preview
  Agent->>UI: Bấm gửi duyệt (pending_review)
  UI->>API: PUT /knowledge/{id} (status: pending_review)
  API->>DB: Lưu snapshot phiên bản (v1, v2...)
  API->>KB: Ghi tệp Markdown
  API-->>UI: Bản nháp chờ duyệt (chưa nạp vào RAG tìm kiếm của User)

  Admin->>UI: Mở tab Phê duyệt tri thức
  Admin->>UI: Thẩm định nội dung và bấm Phê duyệt
  UI->>API: POST /knowledge/{id}/review (action: approve)
  API->>DB: Cập nhật status = published
  API->>RAG: Làm mới bộ chỉ mục BM25
  API-->>UI: Xuất bản thành công, User bắt đầu tìm kiếm được
```

### 6.2. Quy trình khôi phục mật khẩu tự phục vụ qua Email

```mermaid
sequenceDiagram
  actor U as Người dùng
  participant UI as Web UI
  participant API as FastAPI
  participant RL as Rate Limiter (5 req/15m)
  participant DB as PostgreSQL / SQLite
  participant Mail as Email Sender

  U->>UI: Nhập username hoặc email yêu cầu reset
  UI->>API: POST /auth/forgot-password
  API->>RL: Kiểm tra số lần gọi trong 15 phút
  alt Vượt quá 5 lần/15 phút
    RL-->>UI: HTTP 429 Too Many Requests
  else Hợp lệ
    API->>DB: Tìm tài khoản (nếu không thấy vẫn trả success đồng nhất)
    API->>API: Sinh token ngẫu nhiên 32 bytes, băm SHA256
    API->>DB: Lưu token_hash, expires_at = now + 15m
    API->>Mail: Gửi link reset có chứa raw token
    API-->>UI: HTTP 200 Thông báo tiếp nhận đồng nhất
  end

  U->>UI: Mở link email, nhập mật khẩu mới (≥12 ký tự)
  UI->>API: POST /auth/reset-password (token, new_password)
  API->>DB: Xác thực token_hash chưa dùng và chưa hết hạn
  API->>DB: Cập nhật password_hash (PBKDF2), đánh dấu token used
  API->>DB: Cập nhật password_changed_at = now
  API-->>UI: Thành công! Toàn bộ JWT token cũ bị vô hiệu hóa tức thì
```

### 6.3. Quy trình thông báo sự cố đa kênh (Telegram & Discord)

```mermaid
sequenceDiagram
  actor U as Người dùng / Hệ thống
  participant API as FastAPI
  participant Hub as Notification Hub
  participant Guard as Anti-SSRF Guard
  participant Ext as Telegram / Discord API

  U->>API: Tạo sự cố mới (POST /tickets) hoặc Chuyển cấp (escalated)
  API->>Hub: dispatch_ticket_notification(ticket)
  Hub->>Guard: Kiểm tra an toàn URL webhook/bot
  alt Phát hiện HTTP, Localhost, IP nội bộ (RFC1918) hoặc AWS metadata
    Guard-->>Hub: Từ chối kết nối (Chặn đứng SSRF)
  else Domain hợp lệ (api.telegram.org / discord.com)
    Guard-->>Hub: Cho phép
    Hub->>Ext: POST JSON thông điệp Markdown (Ticket ID, Priority, Title, SLA)
    Ext-->>Hub: HTTP 200 Delivered
  end
```

## 7. Sơ đồ triển khai demo

```mermaid
flowchart TB
  Browser[Browser] -->|localhost:8000| App[FastAPI container]
  App --> Static[Static UI]
  App -->|DATABASE_URL| DB[(PostgreSQL 16 container or external PostgreSQL)]
  App --> Runtime[Attachment volume]
  App --> KB[Knowledge Base volume]
```

Docker Compose chạy service PostgreSQL 16 và ứng dụng, bind web/API vào loopback `127.0.0.1:8000`; database, attachment và Knowledge Base có named volume riêng. App container chạy bằng UID không đặc quyền; healthcheck gọi `/health`. `DATABASE_URL` có thể trỏ PostgreSQL bên ngoài, nhưng Compose hiện vẫn khởi chạy service PostgreSQL cục bộ. Không có công cụ migration dữ liệu SQLite cũ sang PostgreSQL hoặc migration tổng quát cho PostgreSQL production sẵn có. Chưa có Nginx, worker, vector database, TLS, backup/restore tự động, HA hoặc cấu hình production.

## 8. Mô hình dữ liệu (ERD)

```mermaid
erDiagram
  USERS ||--o{ TICKETS : requests
  USERS o|--o{ TICKETS : assigned_to
  USERS ||--o{ COMMENTS : writes
  TICKETS ||--o{ COMMENTS : contains
  USERS ||--o{ AUDIT_LOGS : acts
  TICKETS ||--o{ AUDIT_LOGS : records
  TICKETS ||--o{ TICKET_ATTACHMENTS : contains
  USERS ||--o{ CHAT_SESSIONS : owns
  CHAT_SESSIONS ||--o{ CHAT_MESSAGES : contains
  USERS ||--o{ PASSWORD_RESET_TOKENS : requests
  USERS ||--o{ KB_VERSIONS : authors

  USERS {
    string username PK
    string password_hash
    string role
    string full_name
    string email
    string department
    string phone
    boolean is_active
    boolean force_password_change
    datetime password_changed_at
  }
  TICKETS {
    int id PK
    string title
    string description
    string category
    string priority
    string requester FK
    string assignee FK
    string status
    datetime sla_deadline
    datetime created_at
    datetime updated_at
    datetime archived_at
    datetime resolved_at
    datetime closed_at
    integer rating
    string rating_comment
  }
  COMMENTS {
    int id PK
    int ticket_id FK
    string author FK
    string comment
    datetime created_at
  }
  AUDIT_LOGS {
    int id PK
    int ticket_id FK
    string actor FK
    string event
    string from_status
    string to_status
    string details
    datetime timestamp
  }
  TICKET_ATTACHMENTS {
    string id PK
    int ticket_id FK
    string original_name
    string stored_name
    string content_type
    int size_bytes
    string uploaded_by FK
  }
  CHAT_SESSIONS {
    string id PK
    string user_id FK
    datetime created_at
    datetime last_message_at
  }
  CHAT_MESSAGES {
    int id PK
    string session_id FK
    string role
    string content
    string sources
    string feedback
  }
  PASSWORD_RESET_TOKENS {
    int id PK
    string user_id FK
    string token_hash
    datetime expires_at
    datetime used_at
    datetime created_at
  }
  KB_VERSIONS {
    int id PK
    string document_identifier
    int version_number
    string content
    string summary
    string created_by FK
    datetime created_at
  }
```

### Từ điển dữ liệu

| Bảng | Trường | Ý nghĩa / ràng buộc |
|---|---|---|
| `users` | `username` | Khóa chính; 3–50 ký tự, chữ/số/`._-`; được chuẩn hóa chữ thường khi tạo qua API |
| `users` | `password_hash` | PBKDF2-HMAC-SHA256 (180.000 vòng lặp), salt ngẫu nhiên; không trả qua API |
| `users` | `role` | Enum: `user` (Nhân viên), `agent` (Kỹ thuật viên) hoặc `admin` (Quản trị viên) |
| `users` | `full_name`, `email`, `department`, `phone`, `is_active` | Hồ sơ người dùng; `is_active=0` khóa tài khoản, chặn đăng nhập và phân công |
| `users` | `force_password_change` | Cờ bắt buộc đổi mật khẩu ở lần đăng nhập tiếp theo do Admin đặt lại |
| `users` | `password_changed_at` | Mốc thời gian đổi mật khẩu UTC; dùng đối soát để vô hiệu hóa JWT cấp trước mốc này (`pwd_at`) |
| `tickets` | `id` | Khóa chính tăng tự động |
| `tickets` | `requester`, `assignee` | Khóa ngoại tới `users`; `assignee` để trống hoặc trỏ tới Kỹ thuật viên/Admin |
| `tickets` | `title`, `description`, `category` | Tiêu đề (5–160), mô tả (10–5000), loại (2–50 ký tự) |
| `tickets` | `priority`, `status` | Enum ràng buộc: Priority (`low`, `medium`, `high`, `urgent`); Status (`new`, `in_progress`, `pending_waiting_user`, `resolved`, `closed`, `escalated`) |
| `tickets` | `resolved_at`, `closed_at`, `rating`, `rating_comment` | Mốc hoàn tất và đánh giá 1–5 sao của người tạo ticket |
| `tickets` | `sla_deadline` | Thời gian UTC; mục tiêu cam kết tính theo giờ lịch: 48h (Low), 24h (Medium), 8h (High), 2h (Urgent) |
| `tickets` | `created_at`, `updated_at`, `archived_at` | Mốc UTC ISO-8601; `archived_at` null khi hoạt động, có giá trị khi lưu trữ mềm |
| `comments` | `ticket_id`, `author` | Khóa ngoại; chuỗi trao đổi 2 chiều giữa nhân viên và IT |
| `audit_logs` | `ticket_id`, `actor`, `event` | Nhật ký bất biến; lưu tác nhân/thời gian/trạng thái cũ/mới; lưu trữ ticket không xóa log |
| `ticket_attachments` | `stored_name`, `content_type`, `size_bytes` | Tệp PNG/JPG/TXT/LOG tối đa 10 MiB; tên lưu trữ UUID ngẫu nhiên; download qua API xác thực |
| `chat_sessions`, `chat_messages` | `user_id`, `session_id`, `sources`, `feedback` | Lịch sử tra cứu giới hạn theo chủ phiên; feedback 👍 / 👎 phục vụ tinh chỉnh tri thức |
| `password_reset_tokens` | `token_hash`, `expires_at`, `used_at` | Token đặt lại mật khẩu ngẫu nhiên băm SHA256; hạn sử dụng 15 phút; dùng một lần |
| `kb_versions` | `document_identifier`, `version_number`, `summary` | Lịch sử phiên bản Runbook (v1, v2...); hỗ trợ đối soát thay đổi và khôi phục (Restore) |

---

## 9. API chính

| Method | Endpoint | Quyền hạn | Mục đích & Nghiệp vụ |
|---|---|---|---|
| GET | `/config` | Công khai | Trả cờ `demo_mode` để giao diện hiển thị thông tin mẫu hỗ trợ kiểm thử |
| POST | `/auth/login` | Công khai | Đăng nhập; cấp JWT token; rate limit 5 lần sai/15 phút; dummy hash chống timing attack |
| GET | `/auth/me` | Đã đăng nhập | Lấy đầy đủ hồ sơ người dùng (họ tên, email, phòng ban, điện thoại, ngày đổi MK) và thống kê hoạt động vé cá nhân |
| PATCH | `/auth/profile` | Đã đăng nhập | Người dùng tự cập nhật thông tin liên hệ cá nhân (họ tên, email có kiểm tra cú pháp, phòng ban, số điện thoại) |
| POST | `/auth/change-password` | Đã đăng nhập | Người dùng đổi mật khẩu chủ động; yêu cầu mật khẩu cũ, mật khẩu mới $\ge$ 12 ký tự |
| POST | `/auth/forgot-password` | Công khai | Yêu cầu link reset mật khẩu qua email; rate limit 5 req/15m; phản hồi đồng nhất |
| POST | `/auth/reset-password` | Công khai | Đặt lại mật khẩu bằng token email; hủy token và vô hiệu hóa JWT cũ |
| GET | `/staff` | Agent / Admin | Danh sách nhân sự IT khả dụng để phân công ticket |
| GET | `/admin/users` | Admin | Danh sách toàn bộ người dùng và vai trò; không lộ hash mật khẩu |
| POST | `/admin/users` | Admin | Tạo tài khoản mới; kiểm tra mật khẩu $\ge$ 12 ký tự |
| PATCH | `/admin/users/{username}` | Admin | Chỉnh sửa hồ sơ, vai trò, khóa/mở khóa; chặn tự khóa hoặc khóa Admin duy nhất |
| POST | `/admin/users/{username}/reset-password` | Admin | Đặt lại mật khẩu nhân viên kèm cờ `force_password_change` |
| GET | `/admin/notifications/status` | Admin | Xem trạng thái cấu hình Telegram Bot & Discord Webhook (che mờ token) |
| POST | `/admin/notifications/test` | Admin | Bắn thông báo thử nghiệm tới Telegram hoặc Discord có kiểm tra chống SSRF |
| GET | `/tickets` | Đã đăng nhập | Xem danh sách ticket (User chỉ xem vé của mình; IT xem toàn bộ hàng đợi) |
| POST | `/tickets` | Đã đăng nhập | Tạo ticket mới; tự động tính `sla_deadline` và ghi Audit Log |
| GET | `/tickets/{id}` | Chủ vé / IT | Xem chi tiết sự cố, tiến trình SLA và chuỗi trao đổi |
| PUT | `/tickets/{id}` | Chủ vé (`new`) / IT | Cập nhật thông tin ticket; tự động tính lại SLA nếu thay đổi Mức độ ưu tiên |
| PATCH | `/tickets/{id}` | Agent / Admin / Chủ vé | Chuyển đổi trạng thái FSM hoặc đóng/mở lại ticket đã giải quyết |
| DELETE | `/tickets/{id}` | Admin | Lưu trữ mềm ticket (soft archive); giữ nguyên toàn bộ Audit Log |
| PUT | `/tickets/{id}/assignment` | Agent / Admin | Nhận hoặc chuyển giao ticket cho Kỹ thuật viên phụ trách |
| POST | `/tickets/{id}/comments` | Chủ vé / IT | Thêm bình luận trao đổi; người tạo bình luận tự động đưa vé chờ về `in_progress` |
| POST | `/tickets/{id}/attachments` | Chủ vé / IT | Tải lên tệp chẩn đoán (PNG, JPG, TXT, LOG $\le$ 10 MiB) |
| GET | `/tickets/{id}/attachments/{aid}` | Chủ vé / IT | Tải về tệp đính kèm an toàn qua xác thực quyền truy cập |
| POST | `/tickets/{id}/rate` | Chủ vé | Đánh giá sao CSAT (1–5 sao) và phản hồi sau khi ticket được giải quyết |
| GET | `/tickets/{id}/audit` | Chủ vé / IT | Xem nhật ký kiểm toán bất biến theo thời gian của ticket |
| GET | `/analytics` | Agent / Admin | Bảng điều khiển phân tích tổng quan: SLA compliance, CSAT, phân bố danh mục |
| GET | `/analytics/agents/me` | Agent / Admin | Báo cáo hiệu suất cá nhân của chính Kỹ thuật viên (vé được giao, SLA cá nhân) |
| GET | `/analytics/export` | Admin | Xuất dữ liệu báo cáo sự cố toàn diện dưới định dạng CSV |
| GET | `/knowledge` | Đã đăng nhập | Danh sách tài liệu Runbook (User chỉ xem `published`; IT xem cả bản nháp) |
| POST | `/knowledge` | Admin | Nạp tệp Runbook Markdown mới (kiểm tra UTF-8, tiêu đề H1, dung lượng $\le$ 256 KiB) |
| GET | `/knowledge/{identifier}` | Đã đăng nhập | Xem nội dung chi tiết của một tài liệu Runbook |
| PUT | `/knowledge/{identifier}` | Agent / Admin | Cập nhật nội dung Runbook; Agent gửi duyệt (`pending_review`); Admin lưu trực tiếp |
| POST | `/knowledge/{identifier}/review` | Admin | Phê duyệt (`published`) hoặc trả lời từ chối bản nháp Runbook kèm ghi chú |
| GET | `/knowledge/{identifier}/versions` | Agent / Admin | Xem lịch sử các phiên bản sửa đổi (v1, v2...) của tài liệu Runbook |
| POST | `/knowledge/{identifier}/restore/{version}` | Admin | Khôi phục nội dung tài liệu về một phiên bản lịch sử cụ thể |
| DELETE | `/knowledge/{source}` | Admin | Xóa tài liệu Runbook tự tạo (bảo vệ các Runbook chuẩn mặc định hệ thống) |
| POST | `/knowledge/{source}/reindex` | Admin | Làm mới bộ chỉ mục tìm kiếm BM25 của tài liệu |
| POST | `/rag/ask` | Đã đăng nhập | Tra cứu tri thức tự phục vụ BM25; trích dẫn nguồn; trả thông báo từ chối an toàn |
| GET | `/rag/sessions` | Đã đăng nhập | Xem danh sách các phiên hỏi đáp trợ lý RAG của chính người dùng |
| GET | `/rag/sessions/{session_id}` | Đã đăng nhập | Xem chi tiết chuỗi hội thoại trong một phiên hỏi đáp cụ thể |
| POST | `/rag/feedback` | Đã đăng nhập | Gửi phản hồi đánh giá hữu ích 👍 hoặc không hữu ích 👎 cho câu trả lời |
| GET | `/health` | Công khai | Kiểm tra tình trạng kết nối CSDL và sức khỏe của hệ thống |

## 10. An toàn, lỗi và giới hạn

- Mật khẩu mẫu được lưu bằng PBKDF2; JWT dùng secret cấu hình qua biến môi trường.
- Demo tự sinh secret ngẫu nhiên khi không cấu hình; chế độ non-demo yêu cầu secret và bootstrap admin. Nếu DB vẫn chứa credential mẫu chưa đổi, startup non-demo chủ động từ chối để không vô tình dùng lại tài khoản demo. Chỉ dùng tài khoản mẫu ở local.
- Trước khi triển khai thật vẫn cần bật HTTPS, quản lý secret an toàn, rate limit, backup/restore, rà soát phụ thuộc và kiểm thử bảo mật theo môi trường.
- Các thao tác ghi cơ sở dữ liệu dùng parameter binding và foreign key.
- Tệp đính kèm có allow-list phần mở rộng, tên lưu trữ ngẫu nhiên, giới hạn dung lượng, quyền download và `X-Content-Type-Options: nosniff`; chưa có antivirus scan, quota tổng hoặc retention automation.
- SQL động cho bộ lọc/cập nhật chỉ ghép tên trường nội bộ từ danh sách cho phép; mọi giá trị truy vấn vẫn bind parameter.
- BM25 và synonym map chỉ là baseline; điểm relevance không phải xác suất độ đúng.
- Response `/rag/ask` kèm `triage`: danh mục theo source đứng đầu và ưu tiên heuristic theo các cụm từ tác động rõ ràng. Web hiển thị lý do và chỉ điền vào form khi người dùng chọn chuyển tiếp; mọi giá trị còn sửa được trước submit. Đây không phải dự đoán ML/chẩn đoán hay SLA được đơn vị nghiệp vụ phê duyệt.
- SQLite phù hợp development/test đơn máy; Docker Compose dùng PostgreSQL persistent. Chưa có kết quả thử tải/HA hoặc bằng chứng vận hành production.
