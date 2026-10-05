# Helpdesk RAG

Prototype Helpdesk nội bộ với giao diện tiếng Việt/Anh: quản lý ticket, SLA, trao đổi và truy xuất hướng dẫn CNTT có dẫn nguồn.

## Chạy local trên Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
$env:SECRET_KEY = "thay-bang-gia-tri-ngau-nhien-dai-cho-may-local"
py -m uvicorn app.main:app --reload
```

Mở `http://127.0.0.1:8000`. Tài liệu API tại `/docs`.

### Tài khoản demo

| Vai trò | Tên đăng nhập | Mật khẩu |
|---|---|---|
| Nhân viên | `user` | `user` |
| IT Support | `agent` | `agent` |
| Quản trị IT | `admin` | `admin` |

Tài khoản mẫu chỉ dùng trình diễn local; thay secret và thay cơ chế nạp tài khoản trước khi đưa hệ thống ra môi trường có người dùng thật.

## Chạy bằng Docker

```powershell
docker compose up --build
```

Compose khởi chạy PostgreSQL 16 cùng ứng dụng, bind web/API vào `127.0.0.1:8000` và lưu database, tệp runtime, Knowledge Base trong các named volume riêng. Mật khẩu database mặc định chỉ dành cho demo local; đặt `POSTGRES_PASSWORD` và `SECRET_KEY` riêng trước khi dùng môi trường chia sẻ. Có thể trỏ `DATABASE_URL` tới PostgreSQL đã quản lý bên ngoài. Không mở cổng này ra Internet.

## Chức năng hiện có

- Đăng nhập JWT; mật khẩu demo băm PBKDF2; vai trò End-user, Agent, Admin.
- PostgreSQL được dùng trong Docker Compose; local development và test mặc định dùng SQLite. Cấu hình `DATABASE_URL` để chọn PostgreSQL; cả hai backend lưu ticket, bình luận, audit, attachment metadata, tài khoản và lịch sử chat.
- End-user chỉ xem ticket của mình; IT có hàng đợi, tìm kiếm/lọc theo trạng thái, danh mục, từ khóa và ngày, phân công và analytics.
- End-user sửa ticket khi còn mới; IT sửa ticket chưa đóng; Admin lưu trữ mềm và audit được giữ lại.
- Admin tạo tài khoản với mật khẩu băm và nạp runbook Markdown UTF-8 (tối đa 256 KiB, cần H1); tài liệu được đưa vào retrieval sau khi cache làm mới.
- Admin cập nhật hồ sơ cơ bản/vai trò, khóa/mở tài khoản (không thể khóa Admin cuối), xóa hoặc re-index runbook, xem báo cáo Agent và tải CSV.
- Luồng nhân viên: tra runbook → xem một nguồn rõ ràng (các nguồn phụ thu gọn) → nếu chưa xử lý được thì chuyển câu hỏi sang ticket (không gõ lại) → theo dõi mã, người IT và hạn SLA. Nút tra cứu tự cuộn tới kết quả; Agent/Admin chỉ thấy hàng đợi và thao tác phù hợp vai trò.
- Khi chuyển tiếp, hệ thống gợi ý category theo runbook đứng đầu và priority theo rule tác động; luôn hiện lý do, không tự gửi và cho người gửi xác nhận/chỉnh. Đây là heuristic demo, không phải mô hình AI phân loại đã nghiệm thu.
- Agent/Admin có thể tra cứu runbook trực tiếp từ ticket; trích đoạn và tên nguồn được chèn vào ô phản hồi dưới dạng bản nháp để IT rà soát/chỉnh sửa rồi tự gửi.
- FSM trạng thái có kiểm tra chuyển tiếp; SLA theo ưu tiên (giờ lịch): thấp 48h, thường 24h, cao 8h, khẩn cấp 2h.
- Ticket hỗ trợ trao đổi; trạng thái chờ bổ sung thông tin/chuyển cấp; nhân viên xác nhận hoặc yêu cầu xử lý lại; đánh giá 1–5 sao khi đã giải quyết.
- Tệp ticket giới hạn PNG/JPG/TXT/LOG đến 10 MiB, được phục vụ qua API có kiểm tra quyền; prototype chưa quét virus.
- RAG baseline bằng BM25 trên Markdown, có truy vấn tiếng Việt cơ bản, trích tên tài liệu và từ chối khi không tìm thấy đoạn phù hợp.
- Lịch sử RAG theo tài khoản, nguồn trích dẫn và feedback 👍/👎 được lưu cục bộ; không có streaming hay LLM-generated answer.
- Giao diện responsive song ngữ Việt/Anh với lựa chọn ngôn ngữ được lưu trong trình duyệt; nội dung ticket/runbook giữ nguyên ngôn ngữ nhập.
- 9+ runbook demo về VPN, Wi-Fi, máy in, Windows Update, Outlook, chứng thư số, quyền thư mục, ERP và MFA.

## Kiểm thử và đánh giá retrieval

```powershell
py -m pytest -q
py -m pytest --cov=app --cov-report=term-missing --cov-report=xml
py -m scripts.evaluate_rag
```

CI cấu hình Ruff với rule bảo mật, pytest/coverage, Node syntax/i18n test, PostgreSQL integration test, tập baseline RAG và build Docker image; coverage được lưu thành artifact. Coverage là tín hiệu kiểm thử, không chứng minh hệ thống đạt yêu cầu chất lượng khác.

## Tài liệu đồ án

- [Báo cáo bối cảnh đề tài](docs/BAO_CAO_BOI_CANH.md): bài toán, stakeholder, giải pháp, tham chiếu Jira/GLPI/ServiceNow và khảo sát nhu cầu.
- [Đối chiếu plan và tính thực tiễn](docs/DOI_CHIEU_PLAN_THUC_TIEN.md): bằng chứng hiện có, phần chưa đạt/chưa đo, so sánh có giới hạn và kế hoạch pilot.
- [SRS](docs/SRS.md): yêu cầu, user stories/acceptance criteria, NFR và giới hạn.
- [Đối chiếu đặc tả chức năng & UI](docs/DOI_CHIEU_FEATURES_AND_UI.md): phân biệt phần đặc tả đã có, phần prototype hỗ trợ một phần và các hạng mục cần thêm hạ tầng/kiểm chứng.
- [SDD](docs/SDD.md): kiến trúc, context, sequence, FSM, deployment, ERD và API.
- [Ma trận truy vết kiểm thử](docs/TEST_TRACEABILITY.md): liên kết yêu cầu/AC với test tự động và bằng chứng còn thiếu.
- [Hướng dẫn sử dụng](docs/USER_GUIDE.md): thao tác theo vai trò Nhân viên, Agent và Admin.
- [Hướng dẫn triển khai demo](docs/DEPLOYMENT.md): cài local/Docker, cấu hình, dữ liệu và giới hạn vận hành.
- [Hướng dẫn đóng góp](CONTRIBUTING.md): thiết lập môi trường, kiểm tra trước PR và quy tắc dữ liệu.
- [Rà soát tài liệu bổ sung](docs/DOI_CHIEU_SUPPLEMENT_GUIDE.md): đề xuất nào phù hợp, phần nào cần bằng chứng hoặc không khớp prototype.
- [Sổ lỗi và nợ kỹ thuật](docs/DEFECT_TECH_DEBT_LOG.md): lỗi đã sửa trong nhánh hoàn thiện và giới hạn còn mở.
- [Kế hoạch thực nghiệm](docs/KE_HOACH_THUC_NGHIEM.md): bộ câu hỏi RAG, định nghĩa metric, kịch bản usability và SUS.
- [Metric charter G1](docs/G1_METRIC_CHARTER_TEMPLATE.md): mẫu dự thảo để nhóm/GVHD chốt và ký; hiện chưa được phê duyệt.
- [Baseline RAG](docs/RAG_BASELINE.md): kết quả truy xuất lần chạy local mới nhất trên bộ 30 câu nháp cùng giới hạn diễn giải.
- [AI usage log](docs/AI_USAGE_LOG.md): hỗ trợ AI, kết quả rà soát và lỗi thiết kế đã sửa.

## Giới hạn cần nêu khi bảo vệ

Đây là prototype học thuật, không phải hệ thống production. Chỉ có lexical retrieval BM25 trên runbook Markdown, chưa có bước LLM generation; điểm BM25 không phải xác suất độ đúng. Baseline trên 30 câu là dữ liệu tự soạn, chưa được IT độc lập duyệt. PostgreSQL trong Compose cải thiện độ phù hợp cho môi trường nhiều tiến trình so với SQLite local, nhưng không đồng nghĩa đã có HA, backup/restore, hardening hoặc được kiểm thử production. Dữ liệu demo, SLA giờ lịch và bộ runbook nhỏ không phù hợp triển khai Internet. Chế độ non-demo yêu cầu secret và bootstrap Admin; ứng dụng từ chối khởi động nếu phát hiện mật khẩu demo mặc định trong DB. Vẫn cần hardening, backup/restore, staging, tải 50 RPS, uptime đo thực tế, SUS với người tham gia và benchmark RAG được chuyên gia xác nhận; không báo cáo các mục tiêu này như kết quả đã đạt.

So với nhắn Zalo, tiện ích kỳ vọng là ticket có mã/trạng thái/người nhận/SLA/lịch sử, nội dung không trôi trong chat và hướng dẫn có nguồn có thể chuyển thành ticket. Hệ thống chưa thay thế kênh khẩn cấp hoặc Zalo/Teams mà doanh nghiệp đang dùng; chưa có push/email notification hay tích hợp ITSM/nhân sự. Muốn kết luận có giảm thời gian/bỏ sót, cần so sánh cùng tác vụ trên kênh chat hiện tại với người dùng thật.

Chạy kiểm tra RAG baseline bằng `py -m scripts.evaluate_rag`. Trước demo, chạy test, đặt `SECRET_KEY` riêng và dùng dữ liệu giả. Trước bảo vệ, nhóm cần chốt metric với GVHD, thu khảo survey/experiment thật, lưu minh chứng và rà lại nội dung SRS/SDD theo mã nguồn thực tế.
