# OpenVPN Client TLS Handshake and Certificate Errors

## Symptoms
- OpenVPN client icon stays yellow or disconnects with red icon.
- Log error: 'TLS Error: TLS key negotiation failed to occur within 60 seconds (check your network connectivity)'.
- Log error: 'VERIFY ERROR: depth=0, error=certificate has expired'.

## Checks
1. View OpenVPN connection log window for exact error lines starting with `TLS Error` or `AUTH_FAILED`.
2. Verify local computer system date, time, and timezone match current real time. Incorrect time breaks TLS certificates.
3. Verify the `.ovpn` configuration file and accompanying client certificates/keys (`.crt`, `.key`) are present in `C:\Program Files\OpenVPN\config`.
4. Check if UDP port 1194 or TCP port 443 is blocked by the local ISP/home Wi-Fi router.

## Resolution
- Correct Windows system clock via Settings > Time & language > Date & time > 'Sync now'.
- Import the latest `.ovpn` profile provided by corporate IT Helpdesk.
- If corporate certificate is expired, request a renewed user certificate bundle from IT Security.
- Temporarily switch connection protocol from UDP to TCP port 443 in the client profile if connecting from restrictive hotel/public Wi-Fi.

## Escalation
Escalate to IT Security team if OpenVPN CA root certificate requires renewal across all corporate profiles.

## Hướng dẫn nhanh (Tiếng Việt)
1. Nhấp chuột phải vào biểu tượng OpenVPN chọn View Log để đọc chi tiết mã lỗi kết nối.
2. Vào Cài đặt ngày giờ của Windows bấm 'Sync now' để đồng bộ lại thời gian (chênh lệch giờ sẽ làm hỏng xác thực chứng chỉ TLS).
3. Nếu log báo 'certificate has expired', gửi yêu cầu cho IT cấp lại file cấu hình `.ovpn` và chứng chỉ mới.
4. Thử phát Wi-Fi từ điện thoại 4G để kiểm tra xem mạng gia đình/quán cafe có chặn cổng OpenVPN không.

## Source and scope
- OpenVPN Community Documentation, [Troubleshooting OpenVPN Client Connections](https://openvpn.net/community-resources/how-to/#troubleshooting), accessed 2026-10-06.
