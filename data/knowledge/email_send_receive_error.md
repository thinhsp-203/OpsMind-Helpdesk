# Outlook Send and Receive Errors 0x800CCC0E and 0x80042108

**Từ khóa:** gửi email, nhận email, lỗi gửi mail, lỗi nhận mail, không gửi được thư, không nhận được thư, SMTP, IMAP, POP3, mailbox.

## Symptoms
- Outlook Send/Receive Progress dialog reports errors: `Task 'user@company.com - Sending' reported error (0x800CCC0E): 'Cannot connect to the network server'`.
- Error `0x80042108`: 'The operation timed out waiting for a response from the sending (SMTP) server'.
- Bottom status bar alternates between 'Disconnected', 'Trying to connect...', and 'Need Password'.

## Checks
1. Check internet connectivity by loading corporate intranet portals in browser.
2. Verify Outlook bottom status bar does not say 'Working Offline'. Go to Send / Receive tab > ensure 'Work Offline' is not highlighted.
3. Test webmail access via browser (`https://mail.company.com` or `https://outlook.office.com`).
4. Check if outbound SMTP port (port 587 or 465) or incoming IMAP/POP3 port (port 993/995) is reachable on the current network.

## Resolution
- Disconnect and reconnect Outlook:
  Go to Send / Receive tab > click 'Work Offline' to disconnect, wait 5 seconds, then click 'Work Offline' again to re-establish connection.
- Verify account credentials and Modern Authentication:
  Click File > Info > Account Settings > Update credentials if recent company password change occurred.
- Isolate conflicting add-ins in Safe Mode:
  Start Outlook without add-ins via `outlook.exe /safe` to determine if a third-party add-in or security plugin is interfering with mail transport.
- Security and Policy Compliance:
  Do NOT disable endpoint antivirus or firewall protection agents. If port inspection or SSL scanning is suspected of dropping packets, escalate to IT Security to review corporate firewall and certificate trust chain policies.

## Escalation
If webmail works normally but Outlook desktop client persistently fails with port 0x800CCC0E, escalate to IT Security to inspect corporate proxy/firewall packet inspection rules.

## Hướng dẫn nhanh (Tiếng Việt)
1. Kiểm tra góc dưới bên phải Outlook: nếu đang hiện 'Working Offline' hoặc 'Disconnected', vào thẻ 'Send / Receive' bấm bỏ chọn nút 'Work Offline'.
2. Đăng nhập thử vào Webmail (trang web đọc mail) để chắc chắn tài khoản và mật khẩu của bạn không bị khóa.
3. Khởi động lại Outlook hoặc mở ở chế độ Safe Mode (`outlook.exe /safe`) để kiểm tra xung đột add-in.
4. Nếu vẫn không gửi nhận được thư, tạo ticket gửi Kỹ thuật viên CNTT kiểm tra kết nối máy chủ và cấu hình tường lửa (tuyệt đối không tự ý tắt phần mềm diệt virus hoặc tường lửa trên máy).

## Source and scope
- Microsoft Learn, [Outlook error 0x800CCC0E when sending or receiving email](https://learn.microsoft.com/en-us/outlook/troubleshoot/performance/error-0x800ccc0e-send-receive-email), accessed 2026-10-06.
