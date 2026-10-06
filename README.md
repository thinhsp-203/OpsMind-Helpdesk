# OpsMind Helpdesk

**OpsMind Helpdesk** là prototype học thuật cho bài toán hỗ trợ CNTT nội bộ. Ứng dụng kết hợp quản lý ticket theo vai trò, SLA và lịch sử xử lý với chức năng tìm hướng dẫn trong Knowledge Base Markdown. README này tóm tắt những gì đã có trong mã nguồn và cách chạy demo; đây chưa phải sản phẩm sẵn sàng cho vận hành production.

## Trạng thái dự án

- Các luồng chính có thể trình diễn gồm tra cứu runbook, tạo/theo dõi ticket, xử lý ticket theo vai trò và quản trị tài khoản/tri thức.
- GitHub Actions có workflow kiểm tra lint, giao diện, test, PostgreSQL, baseline truy xuất và build Docker. **Lần chạy CI mới nhất trên `main` mà nhóm kiểm tra (06/10/2026) thất bại ở PostgreSQL integration test** `test_postgres_schema_is_idempotent_and_ticket_lifecycle_works`: test không thể chuyển ticket từ `new` sang `pending_waiting_user`. Vì vậy không xem CI hiện tại là đạt; kết quả của lần chạy khác có thể thay đổi theo thời gian.
- Tài liệu yêu cầu, thiết kế và kế hoạch đánh giá là đầu vào/đặc tả của đồ án, không phải bằng chứng rằng các mục tiêu production hay usability đã được nghiệm thu.

## Chạy thử nhanh trên Windows

Yêu cầu Python 3.11 trở lên. Từ thư mục repository, chạy:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload
```

Mở `http://127.0.0.1:8000`; API docs tại `/docs`, health check tại `/health`. Chế độ demo mặc định bật và tạo tài khoản mẫu trên database mới:

| Vai trò | Tên đăng nhập | Mật khẩu |
|---|---|---|
| Nhân viên | `user` | `user` |
| IT Support (Agent) | `agent` | `agent` |
| Quản trị IT (Admin) | `admin` | `admin` |

Chỉ dùng tài khoản và dữ liệu giả trên máy local. Không tái sử dụng mật khẩu mẫu hoặc mở ứng dụng ra Internet. Hướng dẫn cấu hình non-demo và lưu ý dữ liệu có trong [hướng dẫn triển khai demo](docs/DEPLOYMENT.md).

## Chạy với Docker Compose

Yêu cầu Docker Engine/Desktop và Docker Compose:

```powershell
docker compose up --build -d
docker compose logs -f helpdesk
```

Compose khởi chạy ứng dụng cùng PostgreSQL 16; web/API chỉ bind vào `127.0.0.1:8000`. Database, tệp runtime và Knowledge Base dùng các named volume riêng. Mặc định Compose vẫn ở demo mode và có mật khẩu PostgreSQL chỉ dành cho demo local; thay `POSTGRES_PASSWORD` và `SECRET_KEY` trước khi chạy trên máy dùng chung. Không mở cổng dịch vụ ra Internet. `docker compose down` giữ dữ liệu; tránh `docker compose down -v` nếu cần giữ volume.

Local development/test mặc định dùng SQLite (`HELPDESK_DB_PATH`); Compose cấu hình `DATABASE_URL` để dùng PostgreSQL. Có thể đặt `DATABASE_URL` để kết nối PostgreSQL khác, nhưng Compose vẫn khởi chạy service PostgreSQL cục bộ. Chưa có quy trình chuyển dữ liệu SQLite cũ sang PostgreSQL hay migration production tổng quát.

## Phạm vi prototype

- **Vai trò và luồng:** Nhân viên chỉ xem ticket của mình, tra cứu hướng dẫn và gửi ticket; Agent xem hàng đợi, lọc/phân công ticket, trao đổi và cập nhật trạng thái; Admin có quyền Agent cùng quản trị tài khoản, runbook và báo cáo.
- **Ticket:** trạng thái có kiểm tra chuyển tiếp, bình luận, audit, attachment, xác nhận/mở lại và đánh giá sau giải quyết. SLA demo tính theo giờ lịch: low 48 giờ, medium 24 giờ, high 8 giờ, urgent 2 giờ; chưa tính lịch làm việc/ngày nghỉ.
- **Triage:** category được gợi ý từ runbook đứng đầu; priority được gợi ý bằng luật từ khóa. Giao diện nêu lý do, cho phép chỉnh sửa và yêu cầu người dùng chủ động xác nhận/gửi. Đây là heuristic, không phải mô hình phân loại đã được đánh giá nghiệp vụ.
- **Knowledge Base:** Admin có thể quản lý runbook Markdown UTF-8 (tối đa 256 KiB, cần H1). Prototype có 9 runbook demo về VPN, Wi-Fi, máy in, Windows Update, Outlook, chứng thư số, quyền thư mục, ERP và MFA.
- **Tra cứu:** truy xuất từ khóa BM25 trên đoạn Markdown, có chuẩn hóa tiếng Việt/synonym cơ bản, trích nguồn và từ chối khi không tìm thấy đoạn đủ liên quan. Điểm relevance không phải xác suất câu trả lời đúng. Agent/Admin có thể chèn đoạn trích và nguồn vào bản nháp phản hồi để tự kiểm tra, chỉnh sửa và gửi.
- **LLM bên ngoài (tùy chọn):** tắt mặc định (`ENABLE_LLM_GENERATION=false`). Chỉ khi bật và cấu hình API key, hệ thống mới gửi câu hỏi của người dùng cùng tối đa ba đoạn runbook được truy xuất tới endpoint tương thích Chat Completions đã cấu hình (`LLM_BASE_URL`, mặc định URL OpenAI). Hãy bảo đảm dữ liệu được phép chia sẻ với nhà cung cấp đó trước khi bật. Nếu thiếu cấu hình, không có kết quả phù hợp hoặc lời gọi lỗi, ứng dụng dùng phản hồi tĩnh; prompt hướng dẫn mô hình bám nguồn không bảo đảm loại bỏ hoàn toàn câu trả lời sai.
- **Giao diện và lưu trữ:** giao diện Việt/Anh, lựa chọn ngôn ngữ lưu trong trình duyệt; nội dung ticket/runbook không tự dịch. Lịch sử hỏi đáp và feedback được lưu theo tài khoản trong database ứng dụng.

## Kiểm thử và đánh giá

Các lệnh kiểm tra cục bộ theo cấu hình repository:

```powershell
py -m ruff check app tests scripts
node --check app/static/app.js
node --check app/static/i18n.js
node tests/test_i18n.js
py -m pytest --cov=app --cov-report=term-missing
py -m scripts.evaluate_rag
```

Workflow CI còn chạy kiểm thử backend với PostgreSQL và build Docker image. Trạng thái CI nêu ở đầu README là lần chạy mới nhất nhóm kiểm tra, không phải kết quả của các lệnh cục bộ trên.

Baseline retrieval được ghi trong [báo cáo RAG](docs/RAG_BASELINE.md): lần chạy local trên tập 30 câu nháp tự soạn cho kết quả context hit@3 28/28 câu in-scope, từ chối 2/2 câu out-of-scope; latency median 0,75 ms và p95 0,80 ms đo trực tiếp hàm retrieval trong tiến trình. Tập nhỏ chưa được chuyên gia IT duyệt; số đo không bao gồm HTTP/UI, tải lần đầu hay tải đồng thời và không chứng minh độ faithful của câu trả lời. Chưa có bằng chứng load test, uptime, usability/SUS, triển khai staging hay đánh giá độc lập. Coverage và kết quả retrieval không tự thân chứng minh chất lượng hoặc mức sẵn sàng production.

## Giá trị dự kiến và giới hạn so sánh

So với việc chỉ trao đổi yêu cầu trong nhóm chat, prototype hướng tới việc giữ mã ticket, trạng thái, người xử lý, hạn SLA và lịch sử cùng một nơi; hướng dẫn có nguồn cũng có thể chuyển thành ticket mà không nhập lại. Đây là lợi ích thiết kế dự kiến, **chưa có thử nghiệm người dùng đối chứng để kết luận giảm thời gian, giảm bỏ sót hay vượt trội** Jira, GLPI, ServiceNow hoặc quy trình hiện hữu. Ứng dụng chưa thay thế kênh khẩn cấp, chat doanh nghiệp hay nền tảng ITSM; chưa có thông báo email/push hoặc tích hợp nhân sự/ITSM.

Đây là prototype, không phải hệ thống production. Tài khoản demo dùng mật khẩu yếu; cần dữ liệu giả. Chưa có đầy đủ các biện pháp vận hành như HTTPS/reverse proxy, rate limiting, backup/restore, monitoring/HA, kiểm thử tải và quy trình nâng cấp production. Attachment chưa được quét virus; chưa có luồng đổi/reset mật khẩu. Không dùng để lưu dữ liệu nhạy cảm hoặc triển khai Internet.

## Tài liệu đồ án

- [Báo cáo bối cảnh đề tài](docs/BAO_CAO_BOI_CANH.md): bài toán, stakeholder, giải pháp và tham chiếu sản phẩm.
- [SRS](docs/SRS.md): yêu cầu, tác nhân, acceptance criteria và mục tiêu cần kiểm chứng.
- [SDD](docs/SDD.md): kiến trúc, luồng xử lý, FSM, dữ liệu và API.
- [Ma trận truy vết kiểm thử](docs/TEST_TRACEABILITY.md): đối chiếu yêu cầu với test hiện có và bằng chứng còn thiếu.
- [Hướng dẫn sử dụng](docs/USER_GUIDE.md): thao tác theo vai trò.
- [Hướng dẫn triển khai demo](docs/DEPLOYMENT.md): cài đặt, cấu hình và giới hạn vận hành.
- [Kế hoạch thực nghiệm](docs/KE_HOACH_THUC_NGHIEM.md) và [metric charter G1](docs/G1_METRIC_CHARTER_TEMPLATE.md): kế hoạch/mẫu cần được nhóm và GVHD chốt, chưa phải kết quả nghiệm thu.
- [Baseline RAG](docs/RAG_BASELINE.md): kết quả retrieval local và giới hạn diễn giải.
- [Sổ lỗi và nợ kỹ thuật](docs/DEFECT_TECH_DEBT_LOG.md): vấn đề đã ghi nhận và giới hạn còn mở.
- [Hướng dẫn đóng góp](CONTRIBUTING.md) và [tài liệu đối chiếu nội bộ](docs/internal/).
