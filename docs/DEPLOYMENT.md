# Cài đặt và chạy prototype

Tài liệu này hướng dẫn chạy demo trên máy cá nhân. Cấu hình trong repository chưa phải hướng dẫn triển khai production; không mở trực tiếp dịch vụ ra Internet.

## Chạy local trên Windows

Yêu cầu Python 3.11 trở lên. Từ thư mục gốc repository:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload
```

Mở `http://127.0.0.1:8000`; health check tại `/health` và OpenAPI UI tại `/docs`. `DEMO_MODE` mặc định là `true`. Trên DB mới ứng dụng tạo ba tài khoản demo `user/user`, `agent/agent`, `admin/admin`. Chỉ dùng dữ liệu giả.

Nếu muốn đặt secret cố định trong phiên PowerShell local:

```powershell
$env:SECRET_KEY = (py -c "import secrets; print(secrets.token_urlsafe(48))")
```

Secret demo ngẫu nhiên mới được tạo khi mỗi lần khởi động nếu biến này không đặt; phiên JWT cũ có thể mất hiệu lực sau restart.

## Chạy bằng Docker Compose

Yêu cầu Docker Engine/Desktop và Docker Compose:

```powershell
docker compose up --build -d
docker compose logs -f helpdesk
```

Mở `http://127.0.0.1:8000`. Compose chạy PostgreSQL 16 cho ứng dụng và chỉ bind web/API vào loopback. Ba named volume tách biệt lưu PostgreSQL (`postgres-data`), tệp runtime/attachment (`helpdesk-runtime`) và runbook (`helpdesk-knowledge`). `docker compose down` giữ dữ liệu; không chạy `docker compose down -v` nếu muốn giữ các volume.

Compose mặc định bật demo mode và dùng mật khẩu PostgreSQL chỉ dành cho demo local. Đặt `POSTGRES_PASSWORD` mạnh và `SECRET_KEY` riêng trong môi trường trước khi chạy trên máy chia sẻ. Có thể đặt `DATABASE_URL` để ứng dụng kết nối PostgreSQL bên ngoài; giá trị URI cần URL-encode thông tin đăng nhập có ký tự đặc biệt. Compose vẫn khởi động service PostgreSQL cục bộ.

Đối với **database mới** ở chế độ non-demo, đặt `DEMO_MODE=false`, secret riêng, username Admin bootstrap và mật khẩu duy nhất ít nhất 12 ký tự:

```powershell
$env:DEMO_MODE = "false"
$env:SECRET_KEY = (py -c "import secrets; print(secrets.token_urlsafe(48))")
$env:INITIAL_ADMIN_USERNAME = "itadmin"
$securePassword = Read-Host "Initial Admin password (12+ characters)" -AsSecureString
$env:INITIAL_ADMIN_PASSWORD = [System.Net.NetworkCredential]::new("", $securePassword).Password
docker compose up --build -d
```

Nhập mật khẩu riêng tại prompt; không lưu secret vào Git hoặc gõ mật khẩu rõ vào lệnh trong shell dùng chung. Ứng dụng từ chối khởi động non-demo nếu DB còn hash mật khẩu demo mặc định; không đổi mode trên DB demo rồi kỳ vọng tự chuyển đổi. Prototype chưa có luồng đổi/reset mật khẩu.

## Cấu hình

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `DEMO_MODE` | `true` | DB mới nhận tài khoản demo; chỉ dùng local. |
| `SECRET_KEY` | Sinh ngẫu nhiên khi demo; bắt buộc non-demo | Đặt secret mạnh, ổn định và quản lý ngoài source control nếu muốn phiên JWT còn hiệu lực qua restart. |
| `DATABASE_URL` | Rỗng | PostgreSQL connection URI; khi rỗng, ứng dụng dùng SQLite tại `HELPDESK_DB_PATH`. Compose mặc định trỏ tới service PostgreSQL `postgres`. |
| `POSTGRES_PASSWORD` | Mật khẩu demo trong Compose | Mật khẩu service PostgreSQL của Compose; bắt buộc thay trước khi dùng ngoài máy demo. |
| `HELPDESK_DB_PATH` | `data/helpdesk.sqlite3` | Đường dẫn SQLite khi không cấu hình `DATABASE_URL`. |
| `HELPDESK_STORAGE_PATH` | `data` | Thư mục lưu attachment; Compose đặt trong named volume runtime. |
| `INITIAL_ADMIN_USERNAME` | Rỗng | Dùng bootstrap Admin khi tạo DB non-demo rỗng. |
| `INITIAL_ADMIN_PASSWORD` | Rỗng | Bootstrap password tối thiểu 12 ký tự và không trùng username. |
| `TOKEN_EXPIRE_MINUTES` | `60` | Thời hạn JWT; phải là số nguyên dương. |

PostgreSQL được khởi tạo lặp lại an toàn cho schema của prototype. Không có công cụ chuyển dữ liệu SQLite cũ sang PostgreSQL hoặc migration tổng quát cho cơ sở dữ liệu PostgreSQL production sẵn có; sao lưu/export và lên kế hoạch migration riêng trước khi chuyển backend. PostgreSQL volume, attachment và Knowledge Base là ba đơn vị persistence riêng, nên cần sao lưu nhất quán cả database **và** hai file volume. Repository chưa có chức năng backup/restore.

## Kiểm tra và chẩn đoán

```powershell
py -m ruff check app tests scripts
node --check app/static/app.js
node --check app/static/i18n.js
node tests/test_i18n.js
py -m compileall -q app tests scripts
py -m pytest --cov=app --cov-report=term-missing
py -m scripts.evaluate_rag
```

- `GET /health` trả lỗi khi database backend không sẵn sàng; xem log server/container và xác minh `DATABASE_URL`, kết nối PostgreSQL hoặc quyền ghi SQLite.
- Nếu thiếu module, xác nhận virtual environment đang hoạt động rồi cài `requirements.txt`.
- Nếu user bootstrap không xuất hiện, kiểm tra DB path thực tế, trạng thái `DEMO_MODE` và log khởi động; seed chỉ tạo tài khoản khi bảng user rỗng.
- Nếu retrieval không thấy tài liệu vừa nạp, xác nhận tệp Markdown hợp lệ; thử thao tác re-index của Admin.

## Giới hạn vận hành

SQLite và file storage cục bộ chỉ dành cho development/demo đơn máy. Compose cung cấp PostgreSQL persistent, nhưng cấu hình hiện tại vẫn là demo: chưa cấu hình HTTPS/reverse proxy, rate limiting, email/WebSocket notifications, task queue, object storage, malware scan, backup tự động, monitoring, HA, thử tải hoặc quy trình nâng cấp production. Không đưa dữ liệu ticket/người dùng thật vào môi trường này.
