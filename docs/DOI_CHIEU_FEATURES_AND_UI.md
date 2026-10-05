# Đối chiếu đặc tả chức năng & giao diện

**Nguồn:** đặc tả chức năng/giao diện đầu vào do người dùng cung cấp (05/10/2026), không được lưu trong repository.\
**Đối tượng:** prototype Helpdesk RAG trong repository này.\
**Nguyên tắc:** đặc tả mục tiêu không được xem là bằng chứng tính năng đã triển khai; các số liệu, thông báo và kết nối ngoài chỉ được đưa vào khi có backend và kiểm chứng tương ứng.

## Tóm tắt quyết định

Đặc tả mô tả một sản phẩm ITSM rộng với Next.js, WebSocket, vector database, embedding, email/SSO, file attachments, SLA policy editor và analytics. Prototype hiện dùng FastAPI, HTML/CSS/JavaScript, SQLite và BM25 trên runbook Markdown. Vì vậy, giữ nguyên stack và phạm vi prototype; không đổi frontend/backend chỉ để khớp bảng công nghệ tham khảo, và không giả lập những chức năng cần dịch vụ/hạ tầng chưa có.

Luồng đang được ưu tiên là: nhân viên tra runbook có nguồn → bàn giao nội dung thành ticket có người xử lý/SLA/audit → Agent tra cứu ngay từ ticket và đưa trích đoạn vào bản nháp phản hồi → người có trách nhiệm kiểm tra rồi chủ động gửi. Đây là luồng demo được, chưa phải quy trình đã nghiệm thu tại doanh nghiệp.

## Đối chiếu theo module

| Module đặc tả | Trạng thái trong prototype | Giới hạn/cần làm tiếp |
|---|---|---|
| A — Cổng nhân viên | Đăng nhập; tra runbook; tạo ticket; lọc ticket của mình theo từ khóa/trạng thái/danh mục/ngày; xem trao đổi, hạn SLA, audit và tệp; xác nhận/mở lại ticket; đánh giá sau xử lý. | Chưa có notification badge, comment realtime, PDF/Excel attachment hay hồ sơ self-service. |
| B — Chatbot RAG | BM25 cục bộ trên Markdown; trích đoạn/tệp nguồn; từ chối khi không đủ liên quan; 6 câu hỏi mẫu; lịch sử phiên lưu SQLite; feedback 👍/👎; chuyển câu hỏi thành ticket. | Không streaming, không confidence probability, không sinh hướng dẫn bằng LLM. Chưa ghi nhận nhãn giải quyết self-service nên không tính tỷ lệ deflection. |
| C — Ticket | Tạo, sửa theo quyền, comment, audit, gán IT, FSM gồm chờ nhân viên/chuyển cấp, SLA theo giờ lịch, lưu trữ mềm, tệp PNG/JPG/TXT/LOG tối đa 10 MiB và rating 1–5. | Chưa tự đóng sau 72 giờ, hỗ trợ attachment PDF/DOCX, SLA business-hours hoặc policy editor; tệp chưa được virus scan. |
| D — Agent | Hàng đợi tìm/lọc; phân công; xử lý; RAG Assist lấy nội dung ticket và chèn trích đoạn vào bản nháp; thống kê cá nhân đã gán/đã giải quyết/thời gian/SLA. | Chưa có Kanban drag-and-drop, realtime push, nhắc SLA hay đo hiệu suất theo lịch/ca trực. |
| E — Admin | Nạp Markdown giới hạn; tìm danh mục; xóa/re-index; tạo/sửa hồ sơ, vai trò, khóa/mở tài khoản; dashboard xu hướng/danh mục/agent; xuất CSV. | Chưa có PDF/DOCX extraction, vector indexing, antivirus, SLA editor, PDF/XLSX export hoặc KPI self-service. |
| F — Xác thực/RBAC | JWT, ba vai trò, phân quyền API/UI; tài khoản có hồ sơ cơ bản và trạng thái active. | Chưa có Microsoft SSO, quên/reset mật khẩu, refresh/revocation chủ động, remember-me hay directory sync. Tài khoản demo không dùng cho triển khai thật. |
| API/CSDL | REST endpoint hiện tại, SQLite cho user/ticket/comment/audit/attachment/chat session/message. Có migration cho schema cũ. | Khác cấu trúc URL/ERD đề xuất; chưa có category/SLA policy/vector-chunk tables hoặc hạ tầng production. |

## Phần được bổ sung theo đặc tả

- Agent/Admin có nút **Tra cứu runbook cho ticket**, dùng tiêu đề và mô tả ticket làm truy vấn.
- Khi truy xuất có nguồn phù hợp, Agent/Admin có thể **chèn trích đoạn cùng tên nguồn vào bản nháp bình luận của đúng ticket**. Người dùng phải kiểm tra/chỉnh sửa và nhấn gửi; không có bình luận tự động.
- Không hiển thị phần trăm “độ tin cậy”: điểm BM25 không phải xác suất câu trả lời đúng. Không gọi tính năng này là giải pháp tự động hay câu trả lời AI.
- Nhân viên có lịch sử phiên tra cứu và đánh giá phản hồi. Ticket hỗ trợ attachment loại/kích thước giới hạn, xác nhận giải quyết/mở lại và đánh giá sao; Admin có thể quản lý trạng thái/vai trò tài khoản và xuất dữ liệu ticket CSV.

## Các hạng mục chưa triển khai

Các mục như SSO, email/push, WebSocket, file upload, PDF/DOCX parsing, virus scan, embedding/vector DB, session chat lưu trữ, báo cáo PDF/Excel, lịch SLA và số liệu self-service cần thiết kế, hạ tầng, chính sách dữ liệu và kiểm thử riêng. Chúng không được suy ra từ mockup giao diện. Việc triển khai nên theo ưu tiên/rubric đã được GVHD và nhóm xác nhận, sau khi có người dùng/đơn vị thử nghiệm phù hợp.

## Kiểm chứng bổ sung cần có

1. Browser E2E cho cả ba vai trò, đặc biệt xác nhận Agent dùng đúng ticket, sửa được bản nháp và không gửi tự động; kiểm tra upload/tải tệp và quyền chủ ticket.
2. IT nghiệp vụ duyệt runbook và đánh giá chất lượng nguồn/đoạn trích trên ticket đại diện.
3. Usability pilot với tác vụ tương đương trên kênh hiện tại và prototype; ghi thời gian, số lần nhập lại, hoàn tất tác vụ và phản hồi người tham gia.
4. Chốt riêng yêu cầu pháp lý/bảo mật, retention, giờ SLA và hạ tầng trước khi mở rộng tới dữ liệu hoặc người dùng thật.
