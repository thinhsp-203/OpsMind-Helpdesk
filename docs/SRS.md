# Đặc tả yêu cầu phần mềm (SRS)

**Sản phẩm:** Helpdesk RAG — prototype học thuật\
**Phiên bản:** 1.0\
**Trạng thái:** Đặc tả khởi đầu; nhóm/GVHD cần xác nhận phạm vi và chỉ tiêu trước mốc G1.

## 1. Mục đích và phạm vi

Hệ thống hỗ trợ nhân viên tra cứu hướng dẫn CNTT và gửi yêu cầu; IT Support quản lý, phân công, trao đổi, cập nhật ticket; Admin/Agent theo dõi thống kê. Ứng dụng là prototype trình diễn, chưa thay thế nền tảng ITSM hoặc quy trình bảo mật của doanh nghiệp.

## 2. Tác nhân và quyền

| Tác nhân | Quyền |
|---|---|
| End-user | Đăng nhập; chỉ xem ticket của mình; tạo ticket; hỏi Knowledge Base; trao đổi trên ticket của mình |
| Agent | Xem hàng đợi; phân công cho Agent/Admin; chuyển trạng thái; trao đổi; xem analytics |
| Admin | Quyền Agent; nạp runbook Markdown; tạo và xem danh sách tài khoản; lưu trữ ticket |

## 3. Yêu cầu chức năng

| ID | Yêu cầu |
|---|---|
| FR-01 | Người dùng đăng nhập bằng tài khoản hợp lệ; token có thời hạn; thông tin lỗi đăng nhập không tiết lộ tài khoản tồn tại. Trang đăng nhập chỉ hiển thị tài khoản mẫu khi cấu hình demo bật. |
| FR-02 | End-user tạo ticket với tiêu đề, mô tả, loại sự cố và ưu tiên; hệ thống gán mã, thời gian, hạn SLA và audit event. |
| FR-03 | End-user chỉ xem danh sách/chi tiết ticket do mình tạo; Agent/Admin xem hàng đợi và lọc theo trạng thái, loại, từ khóa. |
| FR-04 | Ticket hỗ trợ `new → in_progress → pending_waiting_user / resolved / escalated`; phản hồi người gửi đưa ticket đang chờ về `in_progress`; từ `resolved` người gửi xác nhận `closed` hoặc yêu cầu xử lý lại; cấm chuyển trạng thái không hợp lệ và không mở lại ticket đã đóng. |
| FR-05 | Agent/Admin gán ticket cho tài khoản Agent/Admin; thao tác được ghi audit. |
| FR-06 | Người dùng có quyền trên ticket thêm bình luận; nội dung và thời điểm được lưu. |
| FR-07 | Hệ thống tính hạn SLA theo ưu tiên; hiển thị/đếm ticket còn mở đã quá hạn. Bản demo tính giờ lịch, không xử lý ngày nghỉ. |
| FR-08 | Người dùng đặt câu hỏi bằng tiếng Việt/Anh; hệ thống truy xuất các đoạn Markdown liên quan và trả nguồn. Khi không đủ liên quan phải từ chối khẳng định và hướng dẫn tạo ticket. |
| FR-09 | Agent/Admin xem tổng số ticket, phân bố trạng thái/loại sự cố, số ticket quá SLA và hoạt động gần đây. |
| FR-10 | Thay đổi trạng thái, giao việc, tạo ticket và bình luận được ghi audit log với tác nhân và thời gian. |
| FR-11 | Chủ ticket được sửa nội dung khi ticket còn `new`; Agent/Admin được sửa ticket chưa `closed`. Thay đổi được audit; sửa ưu tiên tính lại SLA từ thời điểm sửa. |
| FR-12 | Admin lưu trữ mềm ticket; ticket lưu trữ bị ẩn khỏi danh sách/analytics nhưng dữ liệu và audit không bị xóa. |
| FR-13 | Admin tạo tài khoản với username duy nhất, vai trò hợp lệ và mật khẩu tối thiểu 12 ký tự; API không trả password/hash. |
| FR-14 | Admin nạp runbook Markdown UTF-8 tối đa 256 KiB, có H1; từ chối file không hỗ trợ, nội dung lỗi và tên tệp xung đột. Index truy xuất được làm mới sau khi nạp. |
| FR-15 | Sau khi tra cứu, hệ thống gợi ý danh mục từ runbook phù hợp nhất và gợi ý ưu tiên bằng luật từ khóa minh bạch; không tự gửi ticket, không tự đổi lựa chọn sau khi người dùng đã chỉnh. Người gửi phải xác nhận/chỉnh trước khi gửi. |
| FR-16 | Agent/Admin có thể tra cứu Knowledge Base từ tiêu đề và mô tả ticket đang xử lý; khi có nguồn phù hợp, có thể chèn trích đoạn kèm nguồn vào ô phản hồi để xem xét/chỉnh sửa. Hệ thống không tự gửi bình luận hoặc ticket. |
| FR-17 | Hệ thống lưu lịch sử phiên hỏi đáp của từng tài khoản, nguồn đi cùng câu trả lời và feedback hữu ích/không hữu ích; chỉ chủ phiên xem được nội dung, Agent/Admin không tự động thấy hội thoại riêng. |
| FR-18 | Người có quyền trên ticket có thể tải lên ảnh PNG/JPG hoặc TXT/LOG không quá 10 MiB; tệp được phục vụ qua API có xác thực và kiểm tra quyền ticket. Người tạo ticket đánh giá 1–5 sao sau khi ticket được giải quyết/đóng. |
| FR-19 | Admin tạo tài khoản có hồ sơ cơ bản, đổi vai trò và khóa/mở tài khoản; tài khoản bị khóa không đăng nhập hoặc nhận phân công; hệ thống không cho khóa/hạ quyền Admin cuối cùng hoặc tự khóa Admin đang đăng nhập. |
| FR-20 | Admin tìm, nạp, xóa và làm mới chỉ mục tài liệu Markdown; hệ thống không nhận PDF/DOCX trong prototype. |
| FR-21 | Agent xem thống kê theo ticket được giao; Admin xem tổng quan, xu hướng/danh mục, thống kê Agent, rating và xuất báo cáo CSV. Chưa có tỷ lệ tự giải quyết nếu không ghi nhận người dùng xác nhận outcome. |
| FR-22 | Người dùng đổi giao diện giữa tiếng Việt và tiếng Anh; lựa chọn lưu trong trình duyệt. Nội dung ticket, bình luận và runbook giữ nguyên ngôn ngữ nhập. |
| FR-23 | Ứng dụng dùng PostgreSQL khi có `DATABASE_URL`; khi không cấu hình URL, local development/test dùng SQLite. Docker Compose cung cấp PostgreSQL có persistence. |

## 4. Acceptance Criteria (Given / When / Then)

### US-01 — Tạo và tra cứu yêu cầu

**Given** nhân viên đã đăng nhập\
**When** nhập tiêu đề, mô tả, loại và ưu tiên hợp lệ rồi gửi\
**Then** hệ thống tạo ticket trạng thái `new`, hiển thị mã ticket, hạn SLA và chỉ cho người tạo cùng IT xem ticket.

### US-02 — Tra cứu hướng dẫn

**Given** người dùng đã đăng nhập và có câu hỏi về VPN, Wi-Fi, máy in hoặc phần mềm được tài liệu hóa\
**When** gửi câu hỏi cho trợ lý tri thức\
**Then** hệ thống tự cuộn tới kết quả, trả các trích đoạn liên quan cùng tên tệp nguồn; nếu truy vấn không khớp tài liệu, hệ thống thông báo chưa tìm thấy và vẫn cho chuyển câu hỏi thành nội dung ticket.

### US-03 — Xử lý ticket

**Given** Agent đã đăng nhập và có ticket trong hàng đợi\
**When** giao ticket hoặc thực hiện chuyển trạng thái hợp lệ\
**Then** người phụ trách/trạng thái được cập nhật và audit log có tác nhân, thời gian, trạng thái trước/sau.

### US-04 — Phân quyền

**Given** End-user A đã đăng nhập\
**When** xem ticket của End-user B hoặc gọi API chỉ dành cho Agent\
**Then** hệ thống không tiết lộ ticket của B và từ chối thao tác điều phối.

### US-05 — Trao đổi

**Given** người dùng có quyền xem ticket\
**When** thêm bình luận không rỗng\
**Then** bình luận xuất hiện theo thời gian và lưu tên người gửi.

### US-06 — Sửa và lưu trữ ticket

**Given** ticket còn mới (End-user) hoặc chưa đóng (Agent/Admin)\
**When** người có quyền sửa các trường được hỗ trợ hoặc Admin lưu trữ ticket\
**Then** hệ thống cập nhật/audit thay đổi, tính lại SLA nếu ưu tiên đổi; ticket lưu trữ không xuất hiện trong hàng đợi và analytics nhưng vẫn giữ lịch sử.

### US-07 — Quản trị tài khoản và tri thức

**Given** Admin đã đăng nhập\
**When** tạo tài khoản hợp lệ hoặc nạp runbook Markdown đạt giới hạn\
**Then** tài khoản xuất hiện trong danh sách có username/vai trò (không có mật khẩu), hoặc tài liệu được lưu và khả dụng cho truy xuất; vai trò khác bị từ chối.

### US-08 — Phân loại và bàn giao có xác nhận

**Given** nhân viên mô tả sự cố và tra cứu runbook\
**When** có kết quả phù hợp và chọn chuyển thành yêu cầu IT\
**Then** form được điền sẵn nội dung, danh mục gợi ý theo runbook và ưu tiên gợi ý theo luật tác động; nhân viên thấy lý do, được sửa lựa chọn và chủ động bấm gửi. Gợi ý không được xem là chẩn đoán hay SLA doanh nghiệp đã cam kết.

### US-09 — Phản hồi và xác nhận kết quả ticket

**Given** người gửi có ticket đang chờ thông tin hoặc đã được IT giải quyết\
**When** người gửi bổ sung bình luận, xác nhận giải quyết, hoặc yêu cầu xử lý lại\
**Then** ticket chờ được đưa lại vào xử lý; ticket đã giải quyết chỉ được đóng/xác nhận hoặc mở lại bởi người gửi; đánh giá sao chỉ lưu cho ticket đã giải quyết.

### US-10 — Lịch sử trợ lý và tài liệu đính kèm

**Given** người dùng đã đăng nhập\
**When** tra cứu tri thức hoặc tải tệp hợp lệ lên ticket mình có quyền\
**Then** lịch sử hỏi đáp chỉ hiển thị cho đúng chủ sở hữu; tệp được lưu với tên nội bộ ngẫu nhiên và tải về qua route xác thực; định dạng/kích thước không hợp lệ bị từ chối.

## 5. Yêu cầu phi chức năng và cách kiểm chứng

Các con số sau là **mục tiêu dự kiến trong kế hoạch**, không phải cam kết đã được nghiệm thu. Cần chốt phần cứng, môi trường, dữ liệu và cách đo cùng GVHD.

| ID | Mục tiêu dự kiến | Cách kiểm chứng |
|---|---|---|
| NFR-01 | RAG p95 ≤ 3 giây trên bộ tài liệu thử nghiệm đã chốt | Đo từ API trên máy/môi trường ghi rõ, tối thiểu 30 truy vấn |
| NFR-02 | ≥ 50 request/giây | Công cụ load test, ghi cấu hình máy, concurrency, error rate; không suy ra từ test đơn |
| NFR-03 | Uptime ≥ 99% trong giai đoạn quan sát đã xác định | Giám sát uptime liên tục; nêu khoảng thời gian và cách tính |
| NFR-04 | Coverage lõi ≥ 70% | `pytest --cov`; coverage không thay thế kiểm thử chất lượng |
| NFR-05 | Không truy cập chéo ticket giữa End-user | API integration test cho tài khoản A/B |
| NFR-06 | Tài liệu truy xuất có nguồn; không trả lời không có căn cứ | Bộ test câu hỏi có ground truth, kiểm tra nguồn và trường hợp ngoài phạm vi |
| NFR-07 | Giao diện dùng được ở chiều rộng điện thoại và desktop | Kiểm tra thủ công ở viewport 375px và 1280px |
| NFR-08 | Tệp tri thức tối đa 256 KiB; mật khẩu tạo mới tối thiểu 12 ký tự | Kiểm thử API biên kích thước/encoding và validation; không xem đây là hardening đủ cho Internet |
| NFR-09 | Tệp ticket chỉ PNG/JPG/TXT/LOG, tối đa 10 MiB/tệp | Kiểm thử phần mở rộng, dung lượng, quyền upload/download; vẫn cần antivirus scan trước dùng thật |
| NFR-10 | PostgreSQL là backend trong cấu hình Compose; SQLite vẫn dùng được cho local test | PostgreSQL integration test trong CI và smoke test Compose; chưa phải kiểm chứng HA/production |

## 6. Quy tắc nghiệp vụ

- Ưu tiên `low/medium/high/urgent` lần lượt có mục tiêu SLA 48/24/8/2 giờ lịch.
- Ticket đóng không chuyển trạng thái tiếp; ticket đã giải quyết có thể mở lại.
- End-user không được xem hay điều phối ticket của người khác.
- End-user chỉ sửa ticket khi ở trạng thái `new`; Agent/Admin không sửa ticket đã `closed`.
- Lưu trữ ticket là lưu trữ mềm, không xóa audit; chỉ Admin thực hiện.
- Chỉ Admin quản trị tài khoản và nạp Markdown; tệp phải UTF-8, có H1, ≤256 KiB và tên đích chưa tồn tại.
- Chỉ chủ ticket hoặc IT được upload/tải attachment; allow-list hiện tại chỉ gồm PNG/JPG/TXT/LOG ≤10 MiB; chưa quét virus.
- Gợi ý ưu tiên theo rule-based markers chỉ là triage ban đầu: `urgent` khi có dấu hiệu diện rộng/an ninh; `high` khi mô tả mất khả năng làm việc/kết nối/xác thực; trường hợp khác `medium`. Luôn yêu cầu người gửi/IT xác nhận; SLA prototype tính giờ lịch.
- RAG Assist của Agent chỉ chèn các trích đoạn tìm thấy và thông tin nguồn vào bản nháp phản hồi; Agent chịu trách nhiệm xác minh, chỉnh sửa và chủ động gửi.
- RAG chỉ trích xuất nguồn tri thức nội bộ đã nạp; không thay thế xác nhận của IT.
- Attachment prototype giới hạn PNG/JPG/TXT/LOG đến 10 MiB, chưa có malware scanning; chỉ người dùng có quyền với ticket tải được tệp.
- Lựa chọn ngôn ngữ chỉ áp dụng cho giao diện, không dịch nội dung người dùng hoặc runbook.
- PostgreSQL hỗ trợ backend demo Compose; chưa có migration dữ liệu SQLite cũ hoặc quy trình upgrade production.

## 7. Ngoài phạm vi phiên bản demo

Email/SSO, đổi/reset mật khẩu, thông báo push/email, tự đóng ticket sau 72 giờ, lịch làm việc/cấu hình SLA, PDF/DOCX ingestion, pgvector, LLM sinh câu trả lời, antivirus scan, PDF/XLSX report, benchmark quy mô lớn, backup/monitoring production và triển khai cloud thật.
