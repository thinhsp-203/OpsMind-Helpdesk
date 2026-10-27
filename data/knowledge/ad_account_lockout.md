# Mở khóa tài khoản Active Directory và xử lý lỗi đăng nhập Windows / Teams

**Từ khóa:** Active Directory, khóa tài khoản, mở khóa tài khoản, nhập sai mật khẩu, tài khoản bị lock, đăng nhập Windows, đăng nhập Teams, mật khẩu hết hạn, Account Lockout, chính sách mật khẩu.

## Triệu chứng / Dấu hiệu nhận biết
- Đăng nhập vào máy tính Windows hoặc Microsoft Teams xuất hiện thông báo: "The referenced account is currently locked out and may not be logged on to" (Tài khoản hiện đang bị khóa).
- Không thể đăng nhập vào bất kỳ dịch vụ nội bộ nào của công ty (mạng Wi-Fi nội bộ, máy chủ chia sẻ NAS, máy tính bàn).
- Lỗi thường xảy ra sau khi người dùng nhập sai mật khẩu quá 5 lần liên tiếp theo chính sách bảo mật Active Directory.

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra phím Caps Lock và bộ gõ tiếng Việt:** Tắt phím Caps Lock và tạm chuyển bộ gõ Unikey sang tiếng Anh (hoặc bấm biểu tượng con mắt trên ô mật khẩu để xem trước khi Enter) nhằm tránh gõ nhầm ký tự.
2. **Chờ thời gian tự động mở khóa:** Theo chính sách bảo mật tài khoản chuẩn của công ty, tài khoản bị khóa tạm thời có thể tự động mở khóa sau 15 đến 30 phút. Người dùng nên kiên nhẫn chờ đủ thời gian rồi thử lại một lần duy nhất với mật khẩu chính xác.
3. **Kiểm tra các thiết bị khác đang lưu mật khẩu cũ:** Kiểm tra điện thoại, máy tính bảng hoặc laptop khác có đang lưu mật khẩu cũ của bạn hay không (các thiết bị này tự động kết nối Wi-Fi hoặc đồng bộ mail liên tục bằng mật khẩu cũ là nguyên nhân gây khóa tài khoản lặp đi lặp lại).

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Cần mở khóa tài khoản ngay lập tức để kịp tiến độ công việc quan trọng mà không thể chờ thời gian tự động mở khóa.
- Người dùng quên hẳn mật khẩu hoặc mật khẩu tài khoản miền đã hết hạn chu kỳ (Domain Password Expired).
- Cần quản trị viên IT can thiệp trên Active Directory Users and Computers (ADUC) để tích chọn "Unlock account" và cấp lại mật khẩu tạm thời cho người dùng.
