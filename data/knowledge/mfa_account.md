# Tài khoản và xác thực đa yếu tố (MFA)

**Từ khóa:** đăng nhập, MFA, OTP, Authenticator, khóa tài khoản, mật khẩu.

## Hướng dẫn an toàn
1. Kiểm tra đúng trang đăng nhập công ty và kết nối mạng/VPN theo hướng dẫn.
2. Nếu mã MFA không hoạt động, kiểm tra giờ tự động trên thiết bị và chọn đúng tài khoản công việc.
3. Không chia sẻ OTP, mã khôi phục hoặc phê duyệt thông báo đăng nhập mà bạn không chủ động yêu cầu.
4. Không gửi mật khẩu qua email/ticket/chat; IT không cần mật khẩu của bạn để xử lý.

## Khôi phục
- Nếu mất thiết bị hoặc bị khóa, liên hệ IT qua kênh đã xác minh danh tính.
- Nếu nhận yêu cầu MFA bất ngờ, từ chối yêu cầu và báo IT Security ngay.
- Chỉ dùng quy trình reset chính thức; không tắt MFA để né lỗi.

## Sources and scope
- Microsoft Learn, [Manage authentication methods for Microsoft Entra multifactor authentication](https://learn.microsoft.com/en-us/entra/identity/authentication/howto-mfa-userdevicesettings), accessed 2026-10-05. Users manage their own methods through Security info; authorized administrators can manage methods and require re-registration. The article warns against using public profile contact details as MFA methods. Follow the organization's identity verification and recovery process; never share an OTP or approve an unexpected sign-in.
