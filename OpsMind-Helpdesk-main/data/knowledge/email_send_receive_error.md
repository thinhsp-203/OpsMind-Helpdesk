# Outlook Send and Receive Errors 0x800CCC0E and 0x80042108

## Symptoms
- Outlook Send/Receive Progress dialog reports errors: `Task 'user@company.com - Sending' reported error (0x800CCC0E): 'Cannot connect to the network server'`.
- Error `0x80042108`: 'The operation timed out waiting for a response from the sending (SMTP) server'.
- Bottom status bar alternates between 'Disconnected', 'Trying to connect...', and 'Need Password'.

## Checks
1. Check internet connectivity by loading corporate intranet portals in browser.
2. Verify Outlook bottom status bar does not say 'Working Offline'. Go to Send / Receive tab > ensure 'Work Offline' is not highlighted.
3. Test webmail access via browser (`https://mail.company.com` or `https://outlook.office.com`).
4. Check if outbound SMTP port (port 587 or 465) or incoming IMAP/POP3 port (port 993/995) is blocked by antivirus or local firewall.

## Resolution
- Disconnect and reconnect Outlook:
  Go to Send / Receive tab > click 'Work Offline' to disconnect, wait 5 seconds, then click 'Work Offline' again to re-establish connection.
- Verify account credentials and Modern Authentication:
  Click File > Info > Account Settings > Update credentials if recent company password change occurred.
- Temporarily disable third-party antivirus email scanning plugins that intercept SSL/TLS email traffic.
- Start Outlook without add-ins: `outlook.exe /safe` to isolate conflicting third-party security plugins.

## Escalation
If webmail works normally but Outlook desktop client persistently fails with port 0x800CCC0E, escalate to IT Security to inspect corporate proxy/firewall packet inspection rules.

## Hướng dẫn nhanh (Tiếng Việt)
1. Kiểm tra góc dưới bên phải Outlook: nếu đang hiện 'Working Offline' hoặc 'Disconnected', vào thẻ 'Send / Receive' bấm bỏ chọn nút 'Work Offline'.
2. Đăng nhập thử vào Webmail (trang web đọc mail) để chắc chắn tài khoản và mật khẩu của bạn không bị khóa.
3. Khởi động lại Outlook bằng cách bấm Win+R gõ `outlook.exe /safe` để kiểm tra xem có bị xung đột plugin diệt virus không.
4. Nếu vừa đổi mật khẩu Windows, vào File > Account Settings để nhập mật khẩu mới cho hòm thư.

## Source and scope
- Microsoft Support, [Error 0x800CCC0E or 0x80042108 when sending and receiving in Outlook](https://support.microsoft.com/en-us/office/i-get-a-connection-error-in-outlook-0x800ccc0e-or-0x80042108-c8751567-d867-4ef6-92b4-539050d53c23), accessed 2026-10-06.
