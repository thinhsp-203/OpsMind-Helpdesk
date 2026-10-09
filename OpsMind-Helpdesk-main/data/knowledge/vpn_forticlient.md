# VPN FortiClient Remote Access Troubleshooting

**Từ khóa:** VPN, kết nối VPN, làm việc tại nhà, remote access, FortiClient, VPN gateway, gateway down, mất kết nối VPN.

## Symptoms
- User cannot connect to VPN after upgrade.
- Error: connection failed, certificate not trusted, or authentication timeout.

## Checks
1. Ensure the user is connected to the corporate network or has internet access.
2. Record the exact FortiClient version and error message; compare the version with the company-supported package.
3. Confirm the user selected the approved company profile. Do not delete, recreate, or edit managed profiles.
4. If an error mentions a certificate, token, or authentication, stop and ask IT Security to verify it. Do not send passwords, OTPs, or private keys.

## Resolution
- Users should retry only after confirming general internet access and the approved profile.
- IT can repair or reinstall FortiClient from the organization-approved package after checking the error and profile.
- IT Security must verify and renew certificates or credentials through the approved process.
- If the issue persists, open a ticket with the exact error, client version, and time of failure; redact usernames, addresses, and other sensitive log data.

## Escalation
Escalate to IT Security or network support if the problem affects multiple users or the VPN gateway is unavailable.

## Hướng dẫn nhanh (Tiếng Việt)
1. Kiểm tra Internet và kết nối vào đúng hồ sơ VPN do công ty cấp.
2. Kiểm tra ngày giờ máy và phiên bản FortiClient theo tiêu chuẩn IT.
3. Nếu chứng thư hết hạn hoặc lỗi xác thực, không gửi mật khẩu/OTP; liên hệ IT Security để gia hạn hoặc cấp lại.
4. Nếu nhiều người cùng lỗi hoặc VPN Gateway không truy cập được, tạo ticket ưu tiên cao và chuyển nhóm mạng.

## Source and scope
- Fortinet Document Library, [FortiClient 8.0.0 Administration Guide](https://docs.fortinet.com/document/forticlient/8.0.0/administration-guide/725845/introduction), accessed 2026-10-05. This vendor source identifies the product and administrative guide; it does not define this organization's VPN profile, certificate lifecycle, or support policy. This runbook therefore limits user actions to basic checks and routes managed-client changes to IT.
