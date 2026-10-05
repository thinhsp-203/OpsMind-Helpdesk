# Hướng dẫn sử dụng prototype

Ứng dụng trình diễn ba vai trò với giao diện tiếng Việt và tiếng Anh. Dùng nút ngôn ngữ ở thanh trên cùng để đổi; lựa chọn được lưu trong trình duyệt. Nội dung ticket, bình luận và runbook giữ nguyên ngôn ngữ do người dùng/tác giả nhập. Tài khoản và dữ liệu demo chỉ dùng local, không nhập dữ liệu thật.

## Đăng nhập và điều hướng

Mở `http://127.0.0.1:8000`, đăng nhập bằng tài khoản được Admin cấp. Khi demo mode bật, trang đăng nhập hiển thị tài khoản mẫu: `user/user`, `agent/agent`, `admin/admin`. Không dùng chúng trên môi trường có người dùng thật. Nút **Đăng xuất** kết thúc phiên ở trình duyệt.

Điều hướng thay đổi theo vai trò:

| Vai trò | Khu vực |
|---|---|
| Nhân viên | Tổng quan, Trợ lý IT, Ticket của tôi, Tạo yêu cầu |
| IT Support | Tổng quan, Hàng đợi, Thống kê của tôi, Tra cứu tri thức |
| Quản trị IT | Tổng quan, Hàng đợi, Tra cứu tri thức, Knowledge Base, Người dùng, Báo cáo |

## Nhân viên

1. Từ **Trợ lý IT**, nhập vấn đề hoặc chọn câu hỏi gợi ý rồi chọn **Tra cứu hướng dẫn**. Kết quả có thể gồm trích đoạn và tên runbook nguồn; xem nguồn trước khi làm theo. Công cụ truy xuất BM25, không sinh chẩn đoán hay hướng dẫn mới bằng LLM.
2. Nếu cần IT can thiệp, chọn **Chuyển thành yêu cầu IT** (hoặc gửi yêu cầu khi không có kết quả). Kiểm tra tiêu đề, mô tả, danh mục và mức ưu tiên được điền sẵn, chỉnh nếu cần, rồi chủ động gửi.
3. Trong **Ticket của tôi**, tìm/lọc theo từ khóa, trạng thái, danh mục hoặc khoảng ngày. Mở ticket để xem trao đổi, người xử lý, hạn SLA, audit và attachment.
4. Có thể sửa ticket khi trạng thái còn `new`. Có thể bình luận (trừ ticket đã `closed`) và đính kèm PNG/JPG/TXT/LOG tối đa 10 MiB trên ticket của mình. Không tải lên tệp nhạy cảm; prototype chưa quét malware.
5. Khi IT chuyển ticket sang chờ thông tin, bình luận bổ sung sẽ đưa ticket về xử lý. Với ticket `resolved`, người gửi có thể xác nhận đóng hoặc yêu cầu mở lại; có thể gửi đánh giá 1–5 sao sau khi giải quyết.

## IT Support (Agent)

1. **Hàng đợi** hiển thị ticket trong phạm vi IT. Dùng bộ lọc để tìm ticket; kiểm tra nội dung, SLA và lịch sử trước khi cập nhật.
2. Chọn Agent/Admin phụ trách trong danh sách và bấm **Giao cho IT**. Chỉ tài khoản IT đang hoạt động có thể được phân công.
3. Chọn trạng thái hợp lệ rồi bấm **Cập nhật trạng thái**. FSM ngăn chuyển trạng thái không hợp lệ; bình luận và thao tác được ghi audit.
4. Dùng **Tra cứu runbook cho ticket** để tìm theo tiêu đề/mô tả. Nếu có đoạn phù hợp, chèn đoạn trích và tên nguồn vào bản nháp phản hồi của đúng ticket. Xác minh/chỉnh nội dung rồi tự bấm gửi; hệ thống không gửi thay Agent.
5. **Thống kê của tôi** tính theo ticket hiện được gán cho tài khoản này; các chỉ số prototype chưa chuẩn hóa ca trực, giờ làm việc hay ngày nghỉ.

## Quản trị IT (Admin)

- **Người dùng:** tạo tài khoản với username hợp lệ, vai trò và mật khẩu tạm tối thiểu 12 ký tự; cập nhật hồ sơ/vai trò hoặc khóa/mở tài khoản. Mật khẩu không được hiển thị lại. Không thể tự khóa hoặc vô hiệu hóa Admin hoạt động cuối cùng.
- **Knowledge Base:** xem danh mục, nạp Markdown UTF-8 có H1 (tối đa 256 KiB), re-index hoặc xóa tài liệu. Chỉ nạp runbook đã rà soát, không chứa bí mật/dữ liệu thật.
- **Báo cáo:** xem xu hướng ticket, danh mục, hoạt động Agent và tải CSV. Đây là thống kê từ dữ liệu prototype, không phải KPI vận hành đã được xác nhận.
- **Lưu trữ ticket:** thao tác lưu trữ mềm chỉ ẩn ticket khỏi hàng đợi/báo cáo; audit được giữ lại.

## Lưu ý chung

- SLA là giờ lịch theo ưu tiên: low 48h, medium 24h, high 8h, urgent 2h; chưa có lịch làm việc hoặc ngày nghỉ.
- Runbook là tài liệu tham khảo; khi vấn đề ảnh hưởng an toàn/bảo mật hoặc có dấu hiệu diện rộng, thực hiện quy trình/hotline của đơn vị và liên hệ IT.
- Hướng dẫn API/OpenAPI tự sinh ở `/docs`; đây là API prototype, không phải lời hứa tương thích ổn định.
