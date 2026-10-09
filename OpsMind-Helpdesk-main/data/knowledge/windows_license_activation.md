# Windows and Office Volume License (KMS) Activation Fix

## Symptoms
- Desktop background turns black; watermark displays 'Activate Windows - Go to Settings to activate Windows'.
- Microsoft Office applications (Word, Excel) display yellow banner: 'Product Notice: Word hasn\'t been activated. Most features will be disabled'.
- Error codes: `0xC004F074` (No Key Management Service could be contacted) or `0xC004C003`.

## Checks
1. Verify if the workstation is connected to the corporate internal network or corporate VPN. KMS servers only respond from inside corporate network.
2. Open Command Prompt (Admin) and test reachability to corporate KMS server:
   `powershell Test-NetConnection -ComputerName kms.company.internal -Port 1688`.
3. Check current activation status: run `slmgr.vbs /dli` or `slmgr.vbs /xpr`.
4. Check local PC system date and time; clock skew greater than 4 hours causes KMS authentication rejections.

## Resolution
- Connect computer to corporate network or establish corporate VPN connection.
- Force Windows KMS re-activation via elevated Command Prompt:
  ```cmd
  slmgr.vbs /skms kms.company.internal:1688
  slmgr.vbs /ato
  ```
- For Microsoft Office KMS activation:
  Navigate to Office installation directory (e.g., `cd "C:\Program Files\Microsoft Office\Office16"`) and execute:
  ```cmd
  cscript ospp.vbs /sethst:kms.company.internal
  cscript ospp.vbs /act
  ```
- If computer has been offline for > 180 days, KMS volume lease has expired; computer must maintain VPN connection for at least 30 minutes to refresh lease.

## Escalation
If error 0xC004F074 persists while on corporate LAN, escalate to System Administration to inspect corporate KMS host server status and DNS SRV record (`_vlmcs._tcp.company.internal`).

## Hướng dẫn nhanh (Tiếng Việt)
1. Kết nối vào mạng nội bộ công ty hoặc bật VPN: Máy tính cần nhìn thấy máy chủ kích hoạt bản quyền nội bộ (KMS Server).
2. Kiểm tra giờ hệ thống máy tính phải đúng với giờ hiện tại.
3. Mở Command Prompt với quyền Run as Administrator, chạy lệnh `slmgr.vbs /ato` để yêu cầu Windows kích hoạt lại bản quyền.
4. Đối với lỗi bản quyền Office, mở cmd chạy lệnh `cscript ospp.vbs /act` trong thư mục cài đặt Office.

## Source and scope
- Microsoft Learn, [Troubleshoot KMS activation error codes](https://learn.microsoft.com/en-us/troubleshoot/windows-server/licensing-and-activation/troubleshoot-kms-activation-codes), accessed 2026-10-06.
