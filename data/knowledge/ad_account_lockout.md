# Active Directory Account Lockout and Password Reset

## Symptoms
- Windows login screen displays: 'The referenced account is currently locked out and may not be logged on to'.
- User is suddenly locked out after changing corporate password on another device (e.g., mobile phone or tablet).
- Outlook and VPN disconnect simultaneously due to authentication failure.

## Checks
1. In Active Directory Users and Computers (ADUC) or PowerShell, check account status:
   `Get-ADUser -Identity <username> -Properties LockedOut | Select-Object Name, LockedOut`.
2. Check bad password count and lockout time: `net user <username> /domain`.
3. Identify devices storing stale credentials that cause repeated lockout (Event ID 4740 on Domain Controller).
4. Check mobile devices connected to corporate Wi-Fi or corporate ActiveSync email with outdated saved password.

## Resolution
- To unlock account via Domain Controller PowerShell:
  `Unlock-ADAccount -Identity <username>`
- On the user\'s workstation:
  1. Open Control Panel > Credential Manager > Windows Credentials.
  2. Clear all saved entries with old corporate credentials.
- Disconnect mobile phone from corporate Wi-Fi temporarily, update the corporate email account password, then reconnect Wi-Fi with new password.
- If password has expired, user must perform self-service password reset (SSPR) via `https://passwordreset.microsoftonline.com` or contact IT Service Desk.

## Escalation
If account re-locks immediately within 60 seconds after unlock, initiate an IT Security audit to inspect Event ID 4740 Caller Computer Name for rogue credential caching or brute-force scripts.

## Hướng dẫn nhanh (Tiếng Việt)
1. Khi máy báo 'account is currently locked out', nguyên nhân phổ biến nhất là bạn vừa đổi mật khẩu nhưng điện thoại hoặc máy tính bảng vẫn đang lưu mật khẩu cũ và tự động kết nối Wi-Fi/Email liên tục khiến tài khoản bị khóa.
2. Tạm thời tắt Wi-Fi trên điện thoại, cập nhật lại mật khẩu mới cho ứng dụng Outlook trên điện thoại.
3. Vào Credential Manager trên máy tính xóa các thông tin tài khoản cũ đã lưu.
4. Liên hệ IT Helpdesk yêu cầu mở khóa tài khoản (Unlock AD Account). Tài khoản thường sẽ tự động mở lại sau 15-30 phút tùy chính sách công ty.

## Source and scope
- Microsoft Learn, [Account lockout troubleshooting guidance](https://learn.microsoft.com/en-us/troubleshoot/windows-server/identity/account-lockout-troubleshooting), accessed 2026-10-06.
