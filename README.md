# OpsMind Helpdesk

OpsMind Helpdesk là prototype học thuật hỗ trợ quy trình xử lý yêu cầu CNTT nội bộ. Nhân viên có thể tra cứu runbook, chuyển vấn đề thành ticket kèm nội dung đã nhập và theo dõi tiến độ; IT Support tiếp nhận trong hàng đợi có phân công, trạng thái, trao đổi và SLA; Admin quản lý tài khoản, tài liệu tri thức và báo cáo. Các bước này gom thông tin xử lý vào hồ sơ ticket thay vì để yêu cầu và hướng dẫn rời rạc trong các cuộc trò chuyện.

## Trải nghiệm quy trình

1. **Nhân viên tra cứu:** nhập câu hỏi để tìm các đoạn liên quan trong Knowledge Base và xem nguồn runbook.
2. **Chuyển thành ticket:** nếu cần hỗ trợ, chuyển câu hỏi và ngữ cảnh sang biểu mẫu ticket; kiểm tra, chỉnh nội dung cùng danh mục/mức ưu tiên được gợi ý rồi chủ động gửi.
3. **IT Support xử lý:** Agent xem hàng đợi, tìm/lọc và phân công ticket, cập nhật trạng thái, trao đổi với người gửi và theo dõi hạn SLA. Có thể tra cứu runbook từ ticket, chèn đoạn trích có nguồn vào bản nháp phản hồi, rà soát rồi tự gửi.
4. **Admin quản trị:** quản lý người dùng và runbook Markdown, xem báo cáo ticket/Agent và xuất CSV.

Các vai trò có giao diện tiếng Việt/Anh; quyền xem và thao tác được phân theo vai trò và chủ sở hữu ticket. Ticket có lịch sử/audit, bình luận, tệp đính kèm, quy trình chờ thông tin/giải quyết/xác nhận và đánh giá sau giải quyết.

## Chạy thử

### Local trên Windows

Yêu cầu Python 3.11 trở lên. Từ thư mục repository:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload
```

Mở `http://127.0.0.1:8000`; API docs tại `/docs`, health check tại `/health`. Trên database mới, demo mode mặc định tạo các tài khoản mẫu:

| Vai trò | Tên đăng nhập | Mật khẩu |
|---|---|---|
| Nhân viên | `user` | `user` |
| IT Support (Agent) | `agent` | `agent` |
| Quản trị IT (Admin) | `admin` | `admin` |

### Docker Compose

Yêu cầu Docker Engine/Desktop và Docker Compose:

```powershell
docker compose up --build -d
docker compose logs -f helpdesk
```

Compose chạy ứng dụng với PostgreSQL 16; web/API chỉ bind vào `127.0.0.1:8000`. Database PostgreSQL, tệp runtime và Knowledge Base được lưu trong các named volume riêng. `docker compose down` giữ dữ liệu; tránh `docker compose down -v` nếu muốn giữ volume.

Local development/test mặc định dùng SQLite tại `HELPDESK_DB_PATH`. Compose đặt `DATABASE_URL` để chạy PostgreSQL; có thể cấu hình biến này để ứng dụng kết nối PostgreSQL khác, nhưng Compose vẫn khởi chạy PostgreSQL cục bộ.

## Tính năng và cách hoạt động

- **Ticket và SLA:** trạng thái được kiểm tra theo luồng; có phân công, bình luận, audit, attachment, xác nhận/mở lại và đánh giá sau giải quyết. Mục tiêu SLA demo là giờ lịch: low 48 giờ, medium 24 giờ, high 8 giờ, urgent 2 giờ.
- **Knowledge Base:** Admin có thể nạp, xóa và re-index runbook Markdown UTF-8 (tối đa 256 KiB, cần H1). Repository có 9 runbook mẫu về VPN, Wi-Fi, máy in, Windows Update, Outlook, chứng thư số, quyền thư mục, ERP và MFA.
- **Tìm kiếm có dẫn nguồn:** baseline retrieval dùng BM25 trên các đoạn Markdown, kèm chuẩn hóa tiếng Việt/synonym cơ bản, nguồn tài liệu và cơ chế không trả lời khi không tìm thấy đoạn đủ liên quan. Agent/Admin cũng có thể tra cứu từ nội dung ticket và đưa trích đoạn vào bản nháp phản hồi.
- **Gợi ý phân loại:** category dựa trên runbook đứng đầu; priority dùng luật từ khóa. Giao diện giải thích gợi ý và cho phép người gửi chỉnh sửa trước khi xác nhận ticket.
- **LLM tùy chọn:** sinh câu trả lời qua LLM tắt mặc định (`ENABLE_LLM_GENERATION=false`). Khi bật và cấu hình API key, ứng dụng gửi câu hỏi cùng tối đa ba đoạn runbook được truy xuất đến endpoint tương thích Chat Completions cấu hình bằng `LLM_BASE_URL` (mặc định endpoint OpenAI). Chỉ bật nếu được phép chia sẻ nội dung đó với nhà cung cấp. Nếu không bật hoặc lời gọi không thành công, ứng dụng dùng phản hồi tĩnh.
- **Lưu trữ và giao diện:** lịch sử hỏi đáp/feedback được lưu theo tài khoản trong database ứng dụng; lựa chọn ngôn ngữ giao diện lưu ở trình duyệt, không tự dịch nội dung ticket hoặc runbook.

## Kiểm tra và đánh giá

Các lệnh kiểm tra cục bộ:

```powershell
py -m ruff check app tests scripts
node --check app/static/app.js
node --check app/static/i18n.js
node tests/test_i18n.js
py -m pytest --cov=app --cov-report=term-missing
py -m scripts.evaluate_rag
```

Workflow CI trong `.github/workflows/ci.yml` còn có PostgreSQL integration test và build Docker image. Báo cáo [baseline RAG](docs/RAG_BASELINE.md) ghi nhận lần chạy local trên 30 câu hỏi nháp tự soạn: context hit@3 đạt 28/28 câu in-scope, từ chối 2/2 câu out-of-scope; latency median 0,75 ms và p95 0,80 ms đo trực tiếp hàm retrieval. Đây là kết quả trên tập nhỏ chưa được IT độc lập duyệt, không đo độ faithful của câu trả lời hay hiệu năng toàn ứng dụng.

## Tài liệu đồ án

- [Báo cáo bối cảnh đề tài](docs/BAO_CAO_BOI_CANH.md): bài toán, stakeholder, giải pháp và tham chiếu.
- [SRS](docs/SRS.md): yêu cầu, tác nhân, acceptance criteria và mục tiêu cần kiểm chứng.
- [SDD](docs/SDD.md): kiến trúc, luồng xử lý, FSM, dữ liệu và API.
- [Ma trận truy vết kiểm thử](docs/TEST_TRACEABILITY.md): đối chiếu yêu cầu với test và bằng chứng còn thiếu.
- [Hướng dẫn sử dụng](docs/USER_GUIDE.md): thao tác theo vai trò.
- [Hướng dẫn triển khai demo](docs/DEPLOYMENT.md): cài đặt, cấu hình và vận hành demo.
- [Kế hoạch thực nghiệm](docs/KE_HOACH_THUC_NGHIEM.md) và [metric charter G1](docs/G1_METRIC_CHARTER_TEMPLATE.md): kế hoạch/mẫu để nhóm và GVHD chốt.
- [Baseline RAG](docs/RAG_BASELINE.md): kết quả truy xuất và giới hạn diễn giải.
- [Sổ lỗi và nợ kỹ thuật](docs/DEFECT_TECH_DEBT_LOG.md): vấn đề đã ghi nhận.
- [Hướng dẫn đóng góp](CONTRIBUTING.md) và [tài liệu đối chiếu nội bộ](docs/internal/).

## Phạm vi và bước tiếp theo

Đây là prototype học thuật, chưa được kiểm chứng vận hành production hoặc qua thử nghiệm người dùng đối chứng; lợi ích so với trao đổi chat được thể hiện ở quy trình và dữ liệu tập trung, không phải kết quả định lượng hay tuyên bố vượt trội sản phẩm khác. Triage là heuristic, SLA dùng giờ lịch, và tập đánh giá RAG nhỏ/tự soạn. Chưa có thông báo email/push, tích hợp ITSM/nhân sự, backup/restore, HA hoặc quy trình đầy đủ để nâng cấp production.

Tài khoản mẫu dùng mật khẩu yếu: chỉ dùng dữ liệu giả ở môi trường demo local, thay cấu hình demo/secret trước khi chạy trên máy dùng chung và không mở dịch vụ trực tiếp ra Internet. Attachment chưa được quét virus và prototype chưa có luồng đổi/reset mật khẩu. LLM bên ngoài mặc định tắt; khi bật, câu hỏi và ngữ cảnh truy xuất được gửi đến endpoint đã cấu hình. Trước khi mở rộng thử nghiệm, cần rà soát các giới hạn bảo mật, xác nhận runbook/metric với người có chuyên môn và đánh giá bằng người dùng cùng môi trường đã xác định.
