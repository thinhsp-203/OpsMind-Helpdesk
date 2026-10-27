# Hướng dẫn xác thực đa yếu tố (MFA) trên Microsoft Teams và Microsoft 365

**Từ khóa:** đăng nhập, MFA, OTP, Authenticator, Microsoft Teams, Microsoft 365, khóa tài khoản, không nhận được mã, login approval, xác thực 2 bước, bảo mật, device time, recovery through IT.

## Triệu chứng / Dấu hiệu nhận biết
- Đăng nhập vào Microsoft Teams, Outlook hoặc cổng dịch vụ công ty xuất hiện yêu cầu phê duyệt đăng nhập (login approval) nhưng điện thoại không nhận được thông báo đẩy.
- Mã số 6 chữ số sinh ra từ ứng dụng Microsoft Authenticator bị báo không hợp lệ hoặc đã hết hạn.
- Nhận được thông báo phê duyệt đăng nhập lạ trên điện thoại trong khi bản thân không hề thực hiện đăng nhập (dấu hiệu tài khoản bị lộ mật khẩu).

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra kết nối mạng trên điện thoại:** Đảm bảo điện thoại thông minh cài ứng dụng Microsoft Authenticator đang có kết nối mạng Wi-Fi hoặc 4G/5G ổn định để nhận thông báo đẩy.
2. **Mở trực tiếp ứng dụng Authenticator:** Đôi khi hệ điều hành điện thoại tắt thông báo ngầm, hãy mở trực tiếp app *Microsoft Authenticator* lên để xem thông báo phê duyệt hoặc lấy mã OTP 6 chữ số theo thời gian.
3. **Đồng bộ thời gian trên điện thoại (Device time):** Nếu mã OTP bị sai, hãy vào cài đặt ngày giờ của điện thoại, bật chế độ "Tự động đặt ngày & giờ theo mạng" (Automatic date and time) để đồng bộ giờ chuẩn xác.
4. **Cảnh báo an toàn (Security Alert):** Nếu nhận được yêu cầu phê duyệt đăng nhập bất ngờ mà bản thân không thao tác, bấm ngay nút **Từ chối (Deny)**, tuyệt đối không phê duyệt và không chia sẻ mã OTP cho bất kỳ ai.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Nhân viên bị mất điện thoại, hỏng điện thoại hoặc đổi máy mới và không thể tự đăng nhập để chuyển Authenticator (Recovery through IT).
- Cần quản trị viên IT đăng nhập cổng Microsoft 365 Admin Center để đặt lại (reset) phương thức xác thực đa yếu tố MFA cho tài khoản.
- Tài khoản nghi ngờ bị tấn công dò quét mật khẩu từ bên ngoài, cần đội an toàn thông tin khóa tài khoản khẩn cấp để rà soát.
