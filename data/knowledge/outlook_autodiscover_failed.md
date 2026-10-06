# Exchange Autodiscover and New Profile Setup Failure

## Symptoms
- Setting up a new corporate email account stops at: 'Searching for your mail server settings...' and fails.
- Error popup: 'An encrypted connection to your mail server is not available' or 'We couldn\'t connect to the incoming server'.
- Repeated authentication prompts popping up asking for password despite entering correct credentials.

## Checks
1. Ensure the workstation is joined to corporate domain or connected to corporate VPN during initial profile setup.
2. In browser, verify Autodiscover XML endpoint is reachable: `https://autodiscover.company.com/autodiscover/autodiscover.xml`.
3. Check Windows Credential Manager for obsolete saved Microsoft Office / Exchange credentials.
4. Verify user has the required Microsoft 365 Exchange Online license assigned in admin portal.

## Resolution
- Remove outdated cached credentials:
  1. Open Control Panel > Credential Manager > Windows Credentials.
  2. Remove all entries starting with `MicrosoftOffice16_Data` and `ADAL/MSAL`.
- Reset Modern Authentication registry keys if using Office 2016/2019:
  Ensure `EnableADAL` is set to `1` under `HKCU\Software\Microsoft\Office\16.0\Common\Identity`.
- Re-create the Outlook Profile:
  1. Control Panel > Mail (Microsoft Outlook) > Show Profiles > click 'Add...'.
  2. Enter a new profile name (e.g., `Work_New`), input corporate email and password, and allow Autodiscover to complete.

## Escalation
If Autodiscover fails company-wide, escalate to Exchange Messaging Administrator to inspect public/internal DNS CNAME records for `autodiscover.company.com`.

## Hướng dẫn nhanh (Tiếng Việt)
1. Đảm bảo máy tính đang kết nối vào mạng công ty hoặc đã bật VPN khi thiết lập tài khoản email lần đầu.
2. Mở Control Panel > Credential Manager > Windows Credentials, xóa các thông tin đăng nhập Outlook/Office cũ đã lưu.
3. Vào Control Panel > Mail > Show Profiles > Bấm 'Add' để tạo hẳn một Profile cấu hình mới thay thế cho profile cũ bị lỗi.
4. Nếu liên tục bị hỏi mật khẩu, kiểm tra lại xem tài khoản có đang bật xác thực 2 bước (MFA) hay không.

## Source and scope
- Microsoft Learn, [Outlook cannot set up a new profile by using Exchange Autodiscover](https://learn.microsoft.com/en-us/exchange/troubleshoot/client-connectivity/outlook-cannot-set-up-profile-autodiscover), accessed 2026-10-06.
