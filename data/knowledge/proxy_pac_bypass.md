# Corporate Web Proxy and PAC Script Configuration

**Từ khóa:** Proxy, tệp PAC, không tải được trang web nội bộ, bypass proxy, cấu hình proxy, máy chủ proxy, web nội bộ.

## Symptoms
- Browser displays 'The proxy server is not responding' or HTTP 407 Proxy Authentication Required.
- Internal intranet portals load, but external websites or cloud SaaS tools fail to connect.
- Microsoft Teams or Outlook reports offline while web browser works.

## Checks
1. In Windows Settings, navigate to Network & internet > Proxy.
2. Check if 'Automatically detect settings' or 'Use setup script (PAC URL)' is enabled.
3. Verify if manual proxy server is enabled with incorrect IP/Port (e.g., 10.0.0.1:8080).
4. Test intranet URL reachability via command prompt: `curl -v http://proxy.company.internal:8080`.

## Resolution
- User Self-Service Actions:
  1. In Windows Settings > Network & internet > Proxy: Toggle 'Automatically detect settings' to ON and verify the corporate PAC URL (`http://pac.company.internal/wpad.dat`).
  2. Clear cached proxy credentials in Windows Credential Manager:
     Control Panel > Credential Manager > Windows Credentials > Remove outdated corporate proxy entries.
  3. Restart web browsers (Edge/Chrome) after updating proxy settings.
  4. Compliance Warning: Do NOT attempt to disable or bypass corporate proxy scripts; all outbound internet traffic must route through authorized security gateways.
- IT Infrastructure Actions (Requires Administrator Privileges):
  1. In Command Prompt (Run as Administrator), reset WinHTTP proxy configuration if system-level services fail:
     ```cmd
     netsh winhttp reset proxy
     ```
  2. Inspect PAC file syntax and upstream proxy server gateway availability.

## Escalation
Contact IT Infrastructure/Firewall team if proxy authentication fails for AD domain accounts or corporate PAC server returns 502 Bad Gateway.

## Hướng dẫn nhanh (Tiếng Việt)
1. Vào Windows Settings > Network & internet > Proxy.
2. Bật 'Automatically detect settings' và kiểm tra đúng đường dẫn file PAC nội bộ do công ty cấp.
3. Nếu trình duyệt hỏi mật khẩu Proxy liên tục, vào Credential Manager xóa mật khẩu cũ và đăng nhập lại.
4. Nếu cần đặt lại cấu hình proxy hệ thống, yêu cầu Kỹ thuật viên CNTT mở cmd quyền Administrator và chạy lệnh `netsh winhttp reset proxy` để đưa cấu hình WinHTTP về mặc định.

## Source and scope
- Microsoft Learn, [Troubleshoot Web Proxy Auto-Discovery (WPAD)](https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/troubleshoot-wpad), accessed 2026-10-06.
