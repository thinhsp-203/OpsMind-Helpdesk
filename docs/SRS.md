# Đặc tả yêu cầu phần mềm (SRS)

**Sản phẩm:** Helpdesk RAG — prototype học thuật\
**Phiên bản:** 1.0\
**Trạng thái:** Đặc tả khởi đầu; nhóm/GVHD cần xác nhận phạm vi và chỉ tiêu trước mốc G1.

## 1. Mục đích và Phạm vi thực hiện đề tài

### 1.1. Mục đích đề tài
Đề tài **OpsMind Helpdesk** nghiên cứu và xây dựng giải pháp Service Desk nội bộ tích hợp kỹ thuật RAG (Retrieval-Augmented Generation) nhằm:
1. **Tự phục vụ sự cố CNTT cấp 1 (Tier-1 Self-service):** Giúp nhân viên nội bộ nhanh chóng tra cứu giải pháp xử lý sự cố máy tính, mạng, tài khoản và phần mềm dựa trên kho tri thức chuẩn hóa, giảm tải khối lượng công việc lặp lại cho bộ phận IT.
2. **Chuẩn hóa vòng đời xử lý yêu cầu (Incident Lifecycle Management):** Xây dựng quy trình tiếp nhận, phân loại mức độ ưu tiên, cam kết chất lượng dịch vụ (SLA) và theo dõi xử lý sự cố minh bạch theo chuẩn ITIL thu nhỏ.
3. **Khép kín vòng đời tri thức (Ticket-to-Knowledge Loop):** Chuyển hóa các giải pháp sự cố thực tế đã xử lý thành tài liệu Runbook mới thông qua quy trình biên tập Markdown và kiểm duyệt 2 lớp.

### 1.2. Phạm vi thực hiện (In-Scope)
Hệ thống tập trung vào môi trường vận hành CNTT doanh nghiệp vừa và nhỏ (SMB), bao gồm các phân hệ chính:
- **Phân hệ Cổng tự phục vụ & Trợ lý Tra cứu RAG:**
  - Tra cứu sự cố song ngữ (Việt - Anh) trên 30 Runbook doanh nghiệp chuẩn hóa (Mạng, Phần cứng, Phần mềm, Bảo mật).
  - Trích dẫn chính xác nguồn tài liệu và cơ chế từ chối an toàn với các câu hỏi ngoài phạm vi nghiệp vụ.
  - Tự động gợi ý Phân loại (Category) và Mức độ ưu tiên (Priority) dựa trên nội dung tra cứu và mức độ ảnh hưởng nghiệp vụ.
  - Chuyển tiếp ngữ cảnh tra cứu sang yêu cầu hỗ trợ (Ticket Handoff) không cần gõ lại.
- **Phân hệ Quản lý Ticket & Vòng đời Sự cố:**
  - Hàng đợi IT thông minh (Smart Queue) hỗ trợ lọc theo SLA, trạng thái, người phụ trách và tìm kiếm từ khóa.
  - Quản lý FSM chuyển 6 trạng thái chuẩn: `Mới (new)` $\rightarrow$ `Đang xử lý (in_progress)` $\rightarrow$ `Chờ phản hồi (pending_waiting_user)` $\rightarrow$ `Đã giải quyết (resolved)` $\rightarrow$ `Đã đóng (closed)` / `Chuyển cấp (escalated)`.
  - Tính toán hạn xử lý cam kết (SLA Deadline) theo 4 mức ưu tiên: Khẩn cấp (2h), Cao (8h), Trung bình (24h), Thấp (48h).
  - Trao đổi bình luận 2 chiều giữa nhân viên và kỹ thuật viên; đính kèm tệp tin chẩn đoán/ảnh chụp màn hình (PNG, JPG, TXT, LOG $\le$ 10 MiB).
  - Khảo sát mức độ hài lòng khách hàng nội bộ (CSAT 1–5 sao) sau khi giải quyết ticket.
- **Phân hệ Quản trị Kho Tri thức (Knowledge Base Management):**
  - Trình soạn thảo Markdown trực quan với khung xem trước thời gian thực (Live Preview chia đôi màn hình).
  - Quy trình kiểm duyệt 2 lớp: Kỹ thuật viên (Agent) soạn thảo bản nháp (`draft`) và gửi duyệt (`pending_review`); Quản trị viên (Admin) thẩm định và xuất bản (`published`).
  - Quản lý lịch sử phiên bản (v1, v2...), so sánh và khôi phục (Restore) phiên bản cũ.
  - Tính năng trích xuất ticket đã giải quyết thành bản nháp Runbook mới (Ticket-to-Knowledge).
- **Phân hệ Quản trị An toàn thông tin & Định danh:**
  - Xác thực phiên làm việc qua JWT Token có kiểm tra thời điểm đổi mật khẩu (`pwd_at`).
  - Chính sách mật khẩu mạnh (tối thiểu 12 ký tự, không trùng tên đăng nhập).
  - Cơ chế chống tấn công Brute-force đăng nhập (Rate Limiting: khóa tạm sau 5 lần sai trong 15 phút, trả mã HTTP 429).
  - Chống Timing Attack thông qua Dummy Password Hash.
  - Tính năng Đổi mật khẩu chủ động và Admin đặt lại mật khẩu kèm cờ bắt buộc đổi ở lần đăng nhập kế tiếp (`force_password_change`).
  - Khôi phục mật khẩu thông qua liên kết bảo mật gửi qua Email (Reset Token băm một lần, có thời hạn).
- **Phân hệ Thông báo Đa kênh (Notification Hub):**
  - Gửi thông báo tự động khi có ticket mới hoặc chuyển cấp khẩn cấp qua Telegram Bot và Discord Webhook.
- **Phân hệ Báo cáo Quản trị & Giám sát:**
  - Thống kê tỷ lệ tuân thủ SLA theo từng Kỹ thuật viên, phân bố danh mục sự cố và điểm CSAT.
  - Nhật ký Audit Log minh bạch, bất biến cho từng thao tác trên ticket; hỗ trợ xuất báo cáo CSV.
- **Môi trường & Kiến trúc triển khai:**
  - Hỗ trợ triển khai linh hoạt: Docker Compose (PostgreSQL 16) chạy offline cục bộ trên máy tính bảo vệ và triển khai Cloud Web Service (Render) kết hợp CSDL Serverless (Neon Postgres).

### 1.3. Giới hạn đề tài & Phạm vi không thực hiện (Out-of-Scope)
Để tập trung hoàn thiện sâu các nghiệp vụ cốt lõi theo đúng thời lượng đồ án tốt nghiệp, các nội dung sau không nằm trong phạm vi thực hiện:
- Không tích hợp hệ thống xác thực tập trung doanh nghiệp SSO/SAML/LDAP (Active Directory, Azure AD, Okta) mà sử dụng hệ thống tài khoản nội bộ có mã hóa mật khẩu PBKDF2-SHA256.
- Không tích hợp module quét mã độc (Antivirus engine) thời gian thực trên tệp đính kèm; hệ thống áp dụng cơ chế phòng vệ bằng danh sách trắng định dạng (Allow-list: PNG, JPG, TXT, LOG) và giới hạn kích thước tối đa 10 MiB.
- Không tính toán SLA theo lịch làm việc phức tạp (Business Hours / Ngày lễ / Ca trực), chỉ áp dụng giờ lịch liên tục (Calendar Hours) phục vụ mô phỏng thực nghiệm.
- Không mở cổng kết nối kênh thoại VoIP Call Center hoặc tích hợp WhatsApp/Viber doanh nghiệp trả phí.
- Không sử dụng giải pháp cơ sở dữ liệu véc-tơ độc lập bên ngoài (như Milvus, Pinecone); RAG sử dụng giải thuật BM25 kết hợp từ điển thuật ngữ CNTT song ngữ và tiền xử lý tiếng Việt chuyên sâu, kèm tùy chọn LLM Synthesis cục bộ/API.

---

## 2. Đối tượng sử dụng và Phân quyền (Personas & Permissions)

### 2.1. Chân dung tác nhân và Bối cảnh sử dụng

| Tác nhân (Actor) | Chân dung & Bối cảnh sử dụng | Mục tiêu cốt lõi | Trách nhiệm chính |
|---|---|---|---|
| **Nhân viên nội bộ (End-user / Employee)** | Cán bộ nhân viên thuộc các phòng ban nghiệp vụ (Kế toán, Kinh doanh, Nhân sự, Vận hành...). Không có chuyên môn sâu về CNTT. Thường gặp gián đoạn công việc do sự cố máy trạm, máy in, mạng Wi-Fi/VPN, cấp quyền phần mềm hoặc quên mật khẩu. Cần kênh tự phục vụ 24/7 trực quan, đơn giản, giải quyết ngay hoặc tạo yêu cầu mà không phải gọi điện/nhắn tin riêng cho IT. | - Tự khắc phục nhanh sự cố máy tính văn phòng trong < 3 phút.<br>- Tạo ticket có phân loại chuẩn xác mà không cần hiểu sâu kỹ thuật.<br>- Nắm bắt minh bạch tiến độ và thời hạn cam kết SLA. | - Cung cấp mô tả triệu chứng và ảnh chụp lỗi/log trung thực.<br>- Phối hợp phản hồi khi Kỹ thuật viên yêu cầu bổ sung thông tin.<br>- Đánh giá khách quan chất lượng hỗ trợ qua khảo sát CSAT sau khi sự cố hoàn tất. |
| **Kỹ thuật viên IT (IT Support / Agent)** | Cán bộ hỗ trợ kỹ thuật CNTT (L1/L2) thuộc Trung tâm Hỗ trợ Kỹ thuật / Phòng Vận hành CNTT. Chịu áp lực xử lý lượng lớn ticket mỗi ngày, nguy cơ trễ hạn SLA, thường xuyên phải trả lời lặp đi lặp lại các câu hỏi phổ biến. Cần công cụ quản lý hàng đợi tập trung, nhận biết vé khẩn cấp và tra cứu nhanh tri thức để giải quyết vé chuẩn xác. | - Giảm thời gian giải quyết trung bình (MTTR).<br>- Không để sót vé khẩn cấp hoặc quá hạn cam kết SLA.<br>- Tái sử dụng runbook chuẩn hóa để nâng cao chất lượng phản hồi. | - Tiếp nhận, phân loại và cập nhật tiến độ xử lý trung thực trên hệ thống.<br>- Chuyển đổi các sự cố mới đã xử lý thành tài liệu Runbook mới (Ticket-to-Knowledge).<br>- Soạn thảo bản nháp tri thức gửi Quản trị viên thẩm định. |
| **Quản trị viên IT (IT Administrator / Lead)** | Trưởng phòng CNTT, Trưởng nhóm Hỗ trợ Kỹ thuật hoặc Kỹ sư An toàn thông tin. Chịu trách nhiệm bảo đảm tính sẵn sàng của hạ tầng dịch vụ, chuẩn hóa quy trình vận hành theo ITIL, kiểm soát an toàn bảo mật và giám sát KPI của đội ngũ hỗ trợ. | - Giám sát toàn diện tỷ lệ tuân thủ SLA và chỉ số hài lòng CSAT.<br>- Chuẩn hóa và kiểm soát chất lượng kho tri thức Runbook trước khi xuất bản.<br>- Đảm bảo an toàn thông tin, kiểm soát định danh và kênh thông báo khẩn. | - Phê duyệt xuất bản hoặc yêu cầu hiệu chỉnh các bản nháp Runbook.<br>- Quản lý định danh người dùng, cấp quyền và xử lý sự cố tài khoản.<br>- Cấu hình và giám sát các kênh cảnh báo tức thì (Telegram/Discord).<br>- Định kỳ xuất báo cáo phân tích hiệu suất và kiểm toán vết thao tác (Audit Log). |

### 2.2. Không gian làm việc theo vai trò (Role-based Workspace Views)

Hệ thống cung cấp trải nghiệm giao diện người dùng được thiết kế chuyên biệt và tối ưu cho từng vai trò nghiệp vụ:

1. **Cổng Tự phục vụ cho Nhân viên (End-User Self-Service Portal):**
   - **Bố cục chia đôi song song (Side-by-Side Split Console):** Khung bên trái dành cho Danh mục Dịch vụ CNTT & Quản lý Ticket cá nhân; Khung bên phải dành riêng cho **Trợ lý AI Helpdesk trực tuyến** (AI Assistant Console) có gắn nhãn trạng thái kết nối thời gian thực (`Trực tuyến • Trả lời ngay`).
   - **Thanh Kịch bản Sự cố nhanh (Quick Scenario Chips):** 5 thẻ kịch bản phổ biến nhất (`🌐 Lỗi VPN`, `🔑 Quên mật khẩu`, `🖨 Kẹt máy in`, `💻 Cấp phần mềm`, `🛡 Sự cố bảo mật`) giúp kích hoạt tra cứu RAG chỉ với 1 thao tác click, tự động cuộn đến kết quả giải pháp.
   - **Danh mục Dịch vụ CNTT (Service Catalog):** 6 ô dịch vụ chuẩn hóa (Phần mềm văn phòng, Tài khoản & Mật khẩu, Mạng & Kết nối VPN, Thiết bị & Máy in, Sự cố khẩn cấp, Khác) giúp điều hướng người dùng dễ dàng.
   - **Theo dõi Ticket cá nhân & CSAT:** Danh sách vé của tôi với huy hiệu trạng thái màu sắc, bộ đếm ngược hạn SLA, trao đổi bình luận 2 chiều, tải tệp ảnh lỗi và biểu mẫu đánh giá sao CSAT ngay khi vé chuyển sang `resolved`.

2. **Hàng đợi Xử lý Sự cố cho Kỹ thuật viên (IT Support Workspace):**
   - **Hàng đợi Thông minh (Smart Queue):** Bảng quản lý tập trung toàn bộ ticket phòng IT với các bộ lọc nghiệp vụ đa chiều (Tất cả, Cần xử lý, Vé của tôi, Quá hạn SLA, Chờ phản hồi).
   - **Chi tiết Sự cố & RAG Assist:** Xem lịch sử trao đổi, thông tin người yêu cầu, tệp đính kèm. Tích hợp nút tra cứu RAG trực tiếp từ mô tả sự cố và nút **Chèn giải pháp vào bình luận** với 1 click, giúp Agent phản hồi người dùng chuẩn xác mà không cần mở tab mới.
   - **Đóng vòng Tri thức (Ticket-to-Knowledge):** Nút chuyển đổi trực tiếp thông tin ticket đã giải quyết thành bản nháp Runbook Markdown mới kèm danh mục và thẻ phân loại.
   - **Bảng Hiệu suất Cá nhân (Personal KPI):** Bảng số liệu riêng hiển thị tổng số vé được giao, số vé hoàn thành và tỷ lệ tuân thủ SLA cá nhân.

3. **Trung tâm Kiểm soát Toàn diện cho Quản trị viên (IT Administrator Control Center):**
   - **Quy trình Phê duyệt Tri thức 2 lớp (Knowledge Approval Workflow):** Tab chuyên biệt quản lý các bản nháp Runbook chờ duyệt (`pending_review`), cho phép phê duyệt xuất bản (`published`) hoặc trả lời từ chối kèm ghi chú.
   - **Quản lý Phiên bản & Khôi phục (Version Control & Restore):** Xem lịch sử các lần sửa đổi Runbook (v1, v2...), so sánh thay đổi và khôi phục về phiên bản cũ an toàn.
   - **Quản lý Định danh & Cưỡng bức đổi mật khẩu:** Danh sách tài khoản nhân viên, đổi vai trò, khóa/mở khóa tài khoản, đặt lại mật khẩu tạm kèm cờ bắt buộc đổi ở lần đăng nhập tiếp theo (`force_password_change`).
   - **Trung tâm Kênh thông báo Đa kênh (Notification Hub):** Giám sát trạng thái kết nối Telegram Bot và Discord Webhook, nút kiểm tra kết nối tức thì (`Test Notification`), bảo vệ chống SSRF và che dấu token bảo mật.
   - **Báo cáo Điều hành & Kiểm toán (Executive Analytics & Audit):** Biểu đồ SLA Compliance, phân bổ danh mục sự cố, xếp hạng đánh giá CSAT, hiệu suất từng Agent, xuất báo cáo CSV và xem nhật ký Audit Log bất biến.

### 2.3. Ma trận Phân quyền Nghiệp vụ (RBAC CRUD Matrix)

| Nhóm chức năng / Tài nguyên | Thao tác chi tiết | Nhân viên (User) | Kỹ thuật viên (Agent) | Quản trị viên (Admin) | Ràng buộc nghiệp vụ & Cơ chế kiểm soát |
|---|---|:---:|:---:|:---:|---|
| **Xác thực & Tài khoản** | Đăng nhập hệ thống | ✔ | ✔ | ✔ | Rate limit 5 lần sai/15 phút; JWT kiểm tra `pwd_at` |
| | Đổi mật khẩu chủ động | ✔ | ✔ | ✔ | Yêu cầu mật khẩu cũ, mật khẩu mới $\ge$ 12 ký tự |
| | Quên mật khẩu qua Email | ✔ | ✔ | ✔ | Token SHA256 một lần (15 phút), phản hồi đồng nhất |
| | Tạo tài khoản mới | ✖ | ✖ | ✔ | Chỉ Admin; không trả mật khẩu thô |
| | Khóa / Mở khóa tài khoản | ✖ | ✖ | ✔ | Không thể tự khóa chính mình hoặc khóa Admin cuối |
| | Đặt lại mật khẩu nhân viên | ✖ | ✖ | ✔ | Admin cấp mật khẩu tạm, cờ `force_password_change` |
| **Cổng tự phục vụ & RAG** | Tra cứu Tri thức RAG | ✔ | ✔ | ✔ | BM25 song ngữ; chỉ truy xuất tài liệu `published` |
| | Thẻ kịch bản nhanh (Chips) | ✔ | ✔ | ✔ | Kích hoạt tra cứu tự động 5 tình huống phổ biến |
| | Xem lịch sử hỏi đáp cá nhân | ✔ (Của mình) | ✔ (Của mình) | ✔ (Của mình) | Giới hạn nghiêm ngặt theo `user_id` của phiên |
| | Gửi phản hồi 👍 / 👎 | ✔ | ✔ | ✔ | Phục vụ cải tiến chất lượng kho tri thức |
| | Chuyển tiếp sang Ticket (Handoff) | ✔ | ✔ | ✔ | Tự động điền câu hỏi, danh mục & ưu tiên gợi ý |
| **Quản lý Ticket & Sự cố** | Tạo ticket mới | ✔ | ✔ | ✔ | Tự động tính toán SLA deadline theo Priority |
| | Xem danh sách ticket | ✔ (Chỉ vé của mình) | ✔ (Toàn bộ hàng đợi) | ✔ (Toàn bộ hàng đợi) | Kiểm tra quyền truy cập ở mức API và CSDL |
| | Sửa nội dung ticket | ✔ (Chỉ khi `new`) | ✔ (Trước `closed`) | ✔ (Trước `closed`) | Tính lại SLA nếu thay đổi Mức độ ưu tiên |
| | Chuyển trạng thái (FSM) | ✖ | ✔ (new $\rightarrow$ in_prog, v.v.) | ✔ (Toàn quyền FSM) | Tuân thủ nghiêm ngặt máy trạng thái hữu hạn |
| | Tự nhận / Phân công ticket | ✖ | ✔ | ✔ | Chỉ gán cho tài khoản có vai trò Agent/Admin |
| | Trao đổi bình luận | ✔ (Vé của mình) | ✔ (Vé được giao/xem) | ✔ (Toàn bộ vé) | Người tạo bình luận tự động mở lại vé chờ |
| | Đính kèm tệp tin | ✔ (Vé của mình) | ✔ (Vé được giao/xem) | ✔ (Toàn bộ vé) | Allow-list PNG/JPG/TXT/LOG $\le$ 10 MiB |
| | Tải về tệp đính kèm | ✔ (Vé của mình) | ✔ (Vé được giao/xem) | ✔ (Toàn bộ vé) | Xác thực JWT trước khi cho phép tải stream |
| | Đóng / Mở lại vé resolved | ✔ (Chủ vé) | ✖ | ✔ | Chỉ người tạo hoặc Admin có quyền chốt vé |
| | Đánh giá sao CSAT | ✔ (Chủ vé) | ✖ | ✖ | Chỉ khả dụng khi ticket đã `resolved` / `closed` |
| | RAG Assist theo ticket | ✖ | ✔ | ✔ | Tra cứu nhanh ngữ cảnh lỗi chèn vào bình luận |
| | Trích xuất Ticket $\rightarrow$ Runbook | ✖ | ✔ | ✔ | Chỉ áp dụng cho ticket đã ở trạng thái `resolved` |
| | Lưu trữ mềm (Soft Archive) | ✖ | ✖ | ✔ | Ẩn khỏi hàng đợi/analytics nhưng giữ Audit Log |
| **Quản trị Kho Tri thức (KB)** | Xem danh sách Runbook | ✔ (Chỉ published) | ✔ (Tất cả trạng thái) | ✔ (Tất cả trạng thái) | Nhân viên không xem được tài liệu nháp |
| | Soạn thảo Runbook mới | ✖ | ✔ (Tạo draft) | ✔ (Tạo published) | Trình soạn thảo Markdown + Live Preview |
| | Gửi duyệt Runbook | ✖ | ✔ (pending_review) | ✔ | Chuyển trạng thái nháp sang chờ thẩm định |
| | Phê duyệt / Từ chối Runbook | ✖ | ✖ | ✔ | Admin thẩm định nội dung trước khi xuất bản |
| | Xem lịch sử phiên bản & Diff | ✖ | ✔ | ✔ | Quản lý lịch sử các lần sửa đổi v1, v2... |
| | Khôi phục phiên bản cũ | ✖ | ✖ | ✔ | Khôi phục nội dung từ phiên bản lịch sử |
| | Xóa Runbook / Đánh chỉ mục | ✖ | ✖ | ✔ | Không cho phép xóa Runbook mặc định hệ thống |
| **Thông báo & Báo cáo** | Cấu hình kênh Telegram/Discord | ✖ | ✖ | ✔ | Kiểm tra an toàn URL chống SSRF |
| | Bắn thông báo test | ✖ | ✖ | ✔ | Kiểm tra kết nối kênh thông báo |
| | Xem Dashboard SLA & Analytics | ✖ | ✔ (Chỉ vé của mình) | ✔ (Toàn hệ thống) | Phân tích tuân thủ SLA, CSAT, phân bổ lỗi |
| | Xuất báo cáo dữ liệu CSV | ✖ | ✖ | ✔ | Chỉ Quản trị viên mới được trích xuất dữ liệu |
| | Xem Nhật ký Audit Log | ✔ (Chỉ vé của mình) | ✔ (Vé trong hàng đợi) | ✔ (Toàn bộ hệ thống) | Nhật ký bất biến ghi nhận mọi thao tác |

---

## 3. Mục tiêu Nghiệp vụ Định lượng (KPI)

Nhóm cam kết 5 chỉ số định lượng xuyên suốt quá trình thực hiện và nghiệm thu đề tài:

| Mã KPI | Tên chỉ số | Mục tiêu định lượng | Phương pháp đo lường & Minh chứng |
|---|---|---|---|
| **KPI-01** | Độ chính xác truy xuất RAG (Context Hit@3) | $\ge 90\%$ (Kỳ vọng đạt $100\%$ trên bộ test chuẩn) | Đo bằng script tự động [`scripts.evaluate_rag`](file:///E:/OpsMind-Helpdesk/scripts/evaluate_rag.py) trên bộ câu hỏi đánh giá độc lập (chứa ca có dấu, không dấu, viết tắt CNTT, câu ngoài phạm vi). |
| **KPI-02** | Tỷ lệ tuân thủ cam kết SLA (SLA Compliance Rate) | $\ge 85\%$ | Tính toán tự động trên Dashboard Analytics: tỷ lệ ticket được giải quyết trước thời hạn `sla_deadline` trên tổng số ticket hoàn thành. |
| **KPI-03** | Tỷ lệ từ chối an toàn thông tin ngoài phạm vi | $100\%$ | Hệ thống phát hiện và từ chối các câu hỏi không liên quan đến tài liệu kỹ thuật đã nạp, hướng dẫn người dùng tạo ticket; không sinh ảo giác (Hallucination). |
| **KPI-04** | Thời gian phản hồi truy vấn RAG (Latency p95) | $\le 3000\text{ ms}$ (3 giây) | Đo lường độ trễ từ thời điểm gửi câu hỏi đến khi nhận kết quả truy xuất trên môi trường thử nghiệm tiêu chuẩn. |
| **KPI-05** | Mức độ hài lòng của người dùng thực tế (CSAT / SUS) | $\ge 80/100$ điểm (Mức Tốt – Xuất sắc) | Khảo sát thực nghiệm tối thiểu 10 người dùng thật thực hiện kịch bản tác vụ và thu thập phiếu đánh giá System Usability Scale (SUS). |

---

## 4. Yêu cầu chức năng chi tiết

| ID | Tên chức năng | Phân hệ | Mô tả nghiệp vụ chi tiết |
|---|---|---|---|
| **FR-01** | Xác thực & Quản trị phiên | Bảo mật | Đăng nhập bằng username/mật khẩu; cấp phát JWT token có hạn; mã hóa PBKDF2-SHA256 (180.000 vòng lặp). Kiểm tra cờ `force_password_change` và vô hiệu token khi đổi mật khẩu (`pwd_at`). |
| **FR-02** | Chống dò quét & Timing Attack | Bảo mật | Khóa tạm thời và trả mã HTTP 429 sau 5 lần đăng nhập thất bại trong 15 phút. Sử dụng dummy password hash ngăn chặn user enumeration qua sai lệch thời gian xử lý. |
| **FR-03** | Đổi & Đặt lại mật khẩu | Bảo mật | Cho phép người dùng tự đổi mật khẩu (bắt buộc nhập mật khẩu cũ, mật khẩu mới $\ge$ 12 ký tự). Admin có quyền đặt lại mật khẩu tạm cho nhân viên kèm cờ `force_password_change`. Hỗ trợ gửi link đặt lại mật khẩu một lần qua Email (token SHA256, hạn 15 phút, rate limit 5 req/15 phút). |
| **FR-04** | Tra cứu sự cố RAG | Cổng tự phục vụ | Tìm kiếm ngữ cảnh BM25 trên 30 Runbook sự cố song ngữ; trích xuất đoạn văn phù hợp nhất kèm tên tệp nguồn tham chiếu minh bạch. |
| **FR-05** | Cổng từ chối thông minh | Cổng tự phục vụ | Phát hiện câu hỏi ngoài phạm vi tri thức hoặc điểm tương đồng thấp; trả thông báo từ chối lịch sự và cung cấp nút bấm chuyển thành Ticket hỗ trợ. |
| **FR-06** | Phân loại & Đề xuất ưu tiên | Cổng tự phục vụ | Phân tích nội dung sự cố để gợi ý Danh mục (Category) và Mức độ ưu tiên (Priority) theo luật tác động nghiệp vụ (diện rộng $\rightarrow$ Urgent; mất kết nối/lỗi công việc $\rightarrow$ High; lỗi thông thường $\rightarrow$ Medium/Low). Người dùng toàn quyền xác nhận hoặc điều chỉnh. |
| **FR-07** | Chuyển tiếp ngữ cảnh (Handoff) | Cổng tự phục vụ | Điền sẵn tiêu đề và câu hỏi từ giao diện tra cứu RAG sang form tạo ticket, đính kèm nguồn tham khảo giúp nhân viên không phải gõ lại. |
| **FR-08** | Quản lý phiên hỏi đáp RAG | Cổng tự phục vụ | Lưu trữ lịch sử hỏi đáp theo từng tài khoản cá nhân; hỗ trợ đánh giá hữu ích 👍 / 👎 để phát hiện khoảng trống tài liệu. |
| **FR-09** | Tạo yêu cầu hỗ trợ (Ticket) | Xử lý sự cố | Nhân viên tạo ticket với tiêu đề, mô tả, danh mục, mức ưu tiên; hệ thống tự động gán mã ID tăng dần, thời điểm tạo và tính toán `sla_deadline`. |
| **FR-10** | Hàng đợi sự cố thông minh | Xử lý sự cố | IT Support xem danh sách sự cố; bộ lọc đa chiều: mức độ khẩn cấp, quá hạn SLA, trạng thái chưa phân công hoặc ticket được giao cho tôi. |
| **FR-11** | Quản lý vòng đời FSM | Xử lý sự cố | Kiểm soát chuyển đổi trạng thái: `new` $\rightarrow$ `in_progress` $\rightarrow$ `pending_waiting_user` / `resolved` / `escalated`. Phản hồi của người gửi tự động đưa ticket chờ về `in_progress`. Cấm chuyển đổi trái phép. |
| **FR-12** | Phân công & Chuyển giao | Xử lý sự cố | Gán ticket cho Kỹ thuật viên phụ trách; ghi nhận người gán và thời điểm trong lịch sử xử lý. |
| **FR-13** | Trao đổi bình luận 2 chiều | Xử lý sự cố | Nhân viên và IT trao đổi thông tin trực tiếp trên ticket; hiển thị theo trình tự thời gian kèm định danh người gửi. |
| **FR-14** | Đính kèm tệp tin chẩn đoán | Xử lý sự cố | Cho phép tải lên tệp tin ảnh (PNG, JPG) hoặc log (TXT, LOG) $\le$ 10 MiB; lưu trữ tên ngẫu nhiên an toàn; kiểm tra quyền truy cập trước khi cho phép tải về. |
| **FR-15** | Đóng & Mở lại ticket | Xử lý sự cố | Khi ticket được `resolved`, người tạo có quyền xác nhận `closed` hoặc mở lại nếu sự cố tái diễn. Không cho phép mở lại ticket đã ở trạng thái `closed`. |
| **FR-16** | Đánh giá hài lòng CSAT | Xử lý sự cố | Cho phép người tạo đánh giá từ 1 đến 5 sao kèm bình luận sau khi sự cố được giải quyết; dữ liệu cập nhật tức thì vào điểm hài lòng chung. |
| **FR-17** | RAG Assist cho Kỹ thuật viên | Hỗ trợ IT | Hỗ trợ IT tra cứu nhanh kho tri thức trực tiếp từ tiêu đề/mô tả sự cố và chèn trích dẫn vào ô bình luận với 1 cú click để phản hồi cho người dùng. |
| **FR-18** | Soạn thảo Runbook Markdown | Quản trị tri thức | Trình soạn thảo Markdown chuyên nghiệp có khung xem trước Live Preview thời gian thực; phân loại danh mục và hệ thống thẻ từ khóa (tags). |
| **FR-19** | Quy trình kiểm duyệt 2 lớp | Quản trị tri thức | Kỹ thuật viên soạn thảo bản nháp (`draft`) $\rightarrow$ Gửi yêu cầu phê duyệt (`pending_review`) $\rightarrow$ Admin thẩm định và xuất bản (`published`) hoặc trả về bản nháp kèm ghi chú phản hồi. Người dùng cuối chỉ tra cứu các bài đã `published`. |
| **FR-20** | Lịch sử phiên bản & Khôi phục | Quản trị tri thức | Tự động lưu trữ lịch sử chỉnh sửa (v1, v2...) kèm tác nhân và tóm tắt thay đổi; cho phép Quản trị viên khôi phục về bất kỳ phiên bản nào trong quá khứ. |
| **FR-21** | Đóng vòng Ticket $\rightarrow$ Runbook | Quản trị tri thức | Trích xuất trực tiếp thông tin từ ticket đã giải quyết (mô tả lỗi, các bước xử lý trong comment) thành bản nháp Runbook mới, giúp làm giàu kho tri thức từ thực tế. |
| **FR-22** | Thông báo Telegram & Discord | Tích hợp | Tự động gửi tin nhắn thông báo về kênh Telegram hoặc Discord webhook khi có sự cố mới hoặc sự cố khẩn cấp chuyển cấp; có kiểm tra chặn SSRF và nút gửi thử nghiệm. |
| **FR-23** | Quản lý người dùng & phân quyền | Quản trị hệ thống | Admin tạo tài khoản, đổi vai trò, khóa/mở khóa tài khoản; bảo vệ tài khoản Admin cuối cùng không bị khóa hoặc hạ quyền. |
| **FR-24** | Báo cáo SLA & Thống kê | Quản trị hệ thống | Dashboard thống kê tổng số sự cố, phân bố trạng thái, tỷ lệ tuân thủ SLA theo Kỹ thuật viên, điểm CSAT trung bình; hỗ trợ xuất báo cáo định dạng CSV. |
| **FR-25** | Nhật ký Audit Log bất biến | Quản trị hệ thống | Ghi nhận chi tiết mọi thay đổi trạng thái, phân công, chỉnh sửa ticket kèm định danh tác nhân và dấu thời gian; không thể xóa sửa. |
| **FR-26** | Giao diện song ngữ (Việt - Anh) | Trải nghiệm | Hỗ trợ chuyển đổi ngôn ngữ tức thì trên toàn bộ giao diện; ghi nhớ tùy chọn trong LocalStorage của trình duyệt. |
| **FR-27** | Cổng dịch vụ CNTT & Thẻ kịch bản nhanh | Cổng tự phục vụ | Cung cấp danh mục dịch vụ CNTT trực quan phân loại theo nhóm sự cố (Phần mềm, Tài khoản, Mạng/VPN, Thiết bị, Khẩn cấp) và thanh thẻ kịch bản xử lý nhanh (Lỗi VPN, Quên mật khẩu, Kẹt máy in, Cấp phần mềm, Sự cố bảo mật) kích hoạt tra cứu RAG chỉ với 1 thao tác click. |

---

## 5. Kịch bản chấp nhận (Acceptance Criteria - Given / When / Then)

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

### US-11 — Khôi phục mật khẩu tự phục vụ qua Email

**Given** người dùng quên mật khẩu và truy cập tính năng Quên mật khẩu\
**When** nhập tên đăng nhập hoặc email hợp lệ và gửi yêu cầu\
**Then** hệ thống luôn trả thông báo tiếp nhận đồng nhất (tránh lộ thông tin tồn tại tài khoản); gửi email chứa liên kết với token băm ngẫu nhiên có hiệu lực 15 phút; giới hạn 5 yêu cầu/15 phút (trả HTTP 429 nếu vượt quá); khi đặt lại mật khẩu thành công, token bị hủy và toàn bộ phiên JWT cũ bị vô hiệu hóa tức thì.

### US-12 — Kênh thông báo sự cố Telegram & Discord có bảo vệ SSRF

**Given** Quản trị viên cấu hình kênh thông báo qua biến môi trường hoặc giao diện quản trị\
**When** có ticket mới được tạo, ticket khẩn cấp được chuyển cấp, hoặc bấm nút gửi thử nghiệm\
**Then** hệ thống kiểm tra an toàn URL (chặn triệt để giao thức HTTP không mã hóa, chặn địa chỉ localhost, IP mạng nội bộ RFC 1918 và AWS metadata); nếu hợp lệ thì định dạng thông điệp Markdown và gửi tới Telegram/Discord; trạng thái hiển thị che mờ token nhạy cảm.

### US-13 — Quy trình kiểm duyệt Runbook 2 lớp và Khôi phục phiên bản

**Given** Kỹ thuật viên (Agent) hoặc Quản trị viên (Admin) biên soạn tài liệu Runbook Markdown\
**When** Agent gửi bản nháp với trạng thái `pending_review`\
**Then** tài liệu chưa xuất hiện trong kết quả tra cứu RAG của người dùng cuối; Quản trị viên xem xét và duyệt chuyển sang `published` (lúc này mới nạp vào RAG retriever) hoặc trả lời từ chối kèm lý do; mỗi lần lưu giữ một snapshot phiên bản và Admin có thể xem lịch sử, so sánh diff hoặc khôi phục về phiên bản cũ bất kỳ lúc nào.

### US-14 — Đóng vòng sự cố thành tài liệu tri thức (Ticket-to-Knowledge)

**Given** sự cố đã được Kỹ thuật viên xử lý thành công ở trạng thái `resolved`\
**When** Kỹ thuật viên bấm nút trích xuất tri thức từ ticket\
**Then** hệ thống tự động tổng hợp tiêu đề, mô tả lỗi và các bước giải pháp từ chuỗi bình luận thành bản nháp Runbook Markdown chuẩn hóa, điền sẵn danh mục và thẻ tag để Kỹ thuật viên hoàn thiện và gửi kiểm duyệt.

### US-15 — Thẻ kịch bản sự cố nhanh và Danh mục dịch vụ CNTT

**Given** Nhân viên truy cập Cổng tự phục vụ (Self-Service Portal)\
**When** bấm chọn một Thẻ kịch bản sự cố nhanh (như `🌐 Lỗi VPN`, `🔑 Quên mật khẩu`...) hoặc một danh mục dịch vụ\
**Then** hệ thống tự động điền câu hỏi mẫu tương ứng vào ô tra cứu RAG, kích hoạt tìm kiếm ngay lập tức và cuộn mượt xuống khung kết quả giải pháp, giúp người dùng tiếp cận hướng dẫn mà không cần suy nghĩ từ khóa tìm kiếm.

### US-16 — Bảng điều khiển hiệu suất cá nhân của Kỹ thuật viên

**Given** Kỹ thuật viên IT đã đăng nhập vào hệ thống\
**When** truy cập bảng điều khiển cá nhân (`/analytics/agents/me`)\
**Then** hệ thống chỉ hiển thị các chỉ số liên quan đến các ticket được phân công cho chính kỹ thuật viên đó (số vé đang xử lý, số vé đã giải quyết, tỷ lệ tuân thủ cam kết SLA cá nhân) và không bị lẫn với dữ liệu tổng thể của toàn đội ngũ.

---

## 6. Yêu cầu phi chức năng và cách kiểm chứng

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

## 7. Quy tắc nghiệp vụ

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

## 8. Giới hạn học thuật và Ngoài phạm vi đề tài

Để tập trung sâu vào chất lượng giải thuật RAG và vòng đời quản lý sự cố chuẩn ITIL thu nhỏ trong thời gian làm đồ án, các yêu cầu sau được xác định rõ ràng nằm ngoài phạm vi thực hiện:
- **Xác thực doanh nghiệp:** Không tích hợp SSO/SAML/OAuth2 bên ngoài (Azure AD, Google Workspace, Okta) mà sử dụng hệ thống tài khoản nội bộ bảo mật với PBKDF2-SHA256 và JWT token.
- **An toàn tệp tin nâng cao:** Không tích hợp Antivirus engine quét mã độc thời gian thực; kiểm soát an toàn bằng allow-list định dạng (PNG, JPG, TXT, LOG) và giới hạn dung lượng 10 MiB.
- **Tính toán SLA nâng cao:** Chưa xử lý ca làm việc linh hoạt, ngày nghỉ lễ hay múi giờ phức tạp; áp dụng SLA giờ lịch liên tục phục vụ môi trường thực nghiệm.
- **Định dạng tri thức nâng cao:** Tập trung tối ưu Markdown chuẩn hóa cho 30 runbook; chưa hỗ trợ tự động bóc tách PDF/DOCX phức tạp có biểu bảng và hình ảnh lồng ghép.
- **Kênh thoại & Mạng xã hội:** Không mở tổng đài VoIP hoặc tích hợp trả phí với WhatsApp Business / Viber do rào cản chi phí và thủ tục xác minh doanh nghiệp; tập trung vào Web Portal, Telegram Bot và Discord Webhook.
