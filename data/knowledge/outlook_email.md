# Khắc phục sự cố Microsoft Outlook không đồng bộ email và kẹt thư trong Outbox

**Từ khóa:** Outlook, email, Outlook keeps asking for my password and MFA, asking for password, không gửi password, liên hệ IT kiểm tra phiên đăng nhập, mail, hộp thư, không đồng bộ, kẹt Outbox, thư đi không gửi được, cập nhật email, Work Offline, Cached Exchange Mode, dung lượng mailbox, kích thước tệp, kiểm tra web, update client, Office 365.

## Triệu chứng / Dấu hiệu nhận biết
- Outlook keeps asking for my password and MFA: Ứng dụng Outlook liên tục bật cửa sổ yêu cầu nhập lại mật khẩu và mã xác thực 2 bước MFA lặp đi lặp lại.
- Gửi email nhưng thư không chuyển sang mục *Sent Items* (Thư đã gửi) mà nằm mãi trong mục *Outbox* với dòng chữ in nghiêng.
- Người khác đã gửi email nhưng hộp thư Outlook của bạn không hiển thị thư mới, trong khi trên điện thoại hoặc Webmail đã nhận được.
- Góc dưới màn hình Outlook hiển thị trạng thái "All folders are up to date" nhưng thực tế dữ liệu không trùng khớp với máy chủ.

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra trạng thái kết nối mạng và Work Offline:** Trong thẻ *Send / Receive*, kiểm tra xem nút *Work Offline* có đang bị bật hay không. Đảm bảo trạng thái hiển thị "Connected to: Microsoft Exchange".
2. **Kiểm tra kích thước tệp đính kèm và thư mục Outbox:** Mở thư mục *Outbox*, kiểm tra xem có thư nào chứa tệp đính kèm quá lớn bị nghẽn mạng hay không. Nếu có, hãy nhấp chọn và xóa thư đó, hoặc kéo thư đó ra thư mục nháp (Drafts) để giảm dung lượng file đính kèm trước khi gửi lại.
3. **Cập nhật lại hộp thư thủ công (Update client):** Nhấn phím `F9` hoặc vào thẻ *Send / Receive* -> bấm *Update Folder* để buộc Outlook đồng bộ lại ngay lập tức.
4. **Kiểm tra dung lượng mailbox trên Webmail:** Mở trình duyệt web đăng nhập Webmail để xác nhận dung lượng hộp thư vẫn còn chỗ trống và thư mới đã đến máy chủ.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Tuyệt đối không gửi password cá nhân qua email hoặc tin nhắn. Nếu Outlook keeps asking for my password and MFA, liên hệ IT kiểm tra phiên đăng nhập và xóa cache Modern Authentication.
- Toàn bộ hộp thư ngừng đồng bộ nhiều giờ liên tục và hiển thị lỗi kết nối máy chủ Exchange.
- Chế độ lưu đệm Cached Exchange Mode bị lỗi chỉ mục nặng, cần IT tạo lại profile hoặc cấu hình lại tệp dữ liệu OST.
- Cần hỗ trợ cập nhật phiên bản Microsoft Office / Outlook lên bản vá mới nhất từ bộ cài chuẩn của công ty.
