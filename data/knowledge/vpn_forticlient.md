# FortiClient VPN Troubleshooting

## Symptoms
- User cannot connect to VPN after upgrade.
- Error: connection failed, certificate not trusted, or authentication timeout.

## Checks
1. Ensure the user is connected to the corporate network or has internet access.
2. Confirm the VPN client version is supported by the company standard.
3. Verify that the certificate or token is not expired.
4. Check whether the laptop is using the latest Windows update.

## Resolution
- Reinstall the FortiClient package using the standard installer.
- Remove the stale VPN profile and reconnect using the corporate profile.
- If the certificate is invalid, contact the IT security team to renew the certificate.
- When the issue persists, open a high-priority ticket and attach error logs.

## Escalation
Escalate to IT Security or network support if the problem affects multiple users or the VPN gateway is unavailable.

## Hướng dẫn nhanh (Tiếng Việt)
1. Kiểm tra Internet và kết nối vào đúng hồ sơ VPN do công ty cấp.
2. Kiểm tra ngày giờ máy và phiên bản FortiClient theo tiêu chuẩn IT.
3. Nếu chứng thư hết hạn hoặc lỗi xác thực, không gửi mật khẩu/OTP; liên hệ IT Security để gia hạn hoặc cấp lại.
4. Nếu nhiều người cùng lỗi hoặc VPN Gateway không truy cập được, tạo ticket ưu tiên cao và chuyển nhóm mạng.
