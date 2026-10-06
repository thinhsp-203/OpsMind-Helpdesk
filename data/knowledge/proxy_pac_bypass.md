# Corporate Web Proxy and PAC Script Configuration

## Symptoms
- Browser displays 'The proxy server is not responding' or HTTP 407 Proxy Authentication Required.
- Internal intranet portals load, but external websites or cloud SaaS tools fail to connect.
- Microsoft Teams or Outlook reports offline while web browser works.

## Checks
1. In Windows Settings, navigate to Network & internet > Proxy.
2. Check if 'Automatically detect settings' or 'Use setup script (PAC URL)' is enabled.
3. Verify if manual proxy server is enabled with incorrect IP/Port (e.g., 10.0.0.1:8080).
4. Test intranet URL reachability via command prompt: curl -v http://proxy.company.internal:8080.

## Resolution
- Toggle 'Automatically detect settings' to ON and verify corporate PAC URL:
  http://pac.company.internal/wpad.dat
- Clear cached proxy credentials in Windows Credential Manager:
  Control Panel > Credential Manager > Windows Credentials > Remove outdated corporate proxy entries.
- In Command Prompt, reset WinHTTP proxy configuration:
  `cmd
  netsh winhttp reset proxy
  `
- Restart browsers (Edge/Chrome) after updating proxy settings.

## Escalation
Contact IT Infrastructure/Firewall team if proxy authentication fails for AD domain accounts or corporate PAC server returns 502 Bad Gateway.

## Hướng dẫn nhanh (Tiếng Việt)
1. Vào Windows Settings > Network & internet > Proxy.
2. Bật 'Automatically detect settings' và kiểm tra đúng đường dẫn file PAC nội bộ.
3. Nếu trình duyệt hỏi mật khẩu Proxy liên tục, vào Credential Manager xóa mật khẩu cũ và đăng nhập lại.
4. Mở cmd chạy lệnh 
etsh winhttp reset proxy để đưa cấu hình mạng về mặc định.

## Source and scope
- Microsoft Learn, [Troubleshoot Web Proxy Auto-Discovery (WPAD)](https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/troubleshoot-wpad), accessed 2026-10-06.
