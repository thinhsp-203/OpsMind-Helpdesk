# Network Shared Folder Access Denied and NTFS Permissions

## Symptoms
- User opens network share path (e.g., `\\fileserver\Finance`) and receives error: 'Windows cannot access \\fileserver\Finance. You do not have permission to access... Contact your network administrator'.
- Error code: `0x80070005` (Access Denied).
- Shared drive mapped as `Z:` displays red X and fails to reconnect on startup.

## Checks
1. Test network share connectivity: `ping fileserver.company.internal` and `Test-NetConnection fileserver -Port 445`.
2. Check user\'s Active Directory security group memberships: `whoami /groups`.
3. If user was recently added to a new security group (e.g., `SG_Finance_ReadWrite`), check if user has logged off and logged back on. Windows Kerberos security tokens are only refreshed upon logoff/logon.
4. Verify NTFS and Share permissions on the file server.

## Resolution
- Refresh user Kerberos security token:
  User MUST sign out of Windows (Start > User icon > Sign out) and sign back in. Locking/unlocking the screen does NOT refresh Kerberos token groups.
- Alternatively, purge Kerberos ticket cache via Command Prompt without full reboot:
  ```cmd
  klist purge
  gpupdate /force
  ```
- Remap the network drive via Command Prompt:
  ```cmd
  net use Z: /delete
  net use Z: \\fileserver\Finance /persistent:yes
  ```

## Escalation
If user has signed out and signed in but still receives Access Denied, escalate to File Server Administrator to verify NTFS Access Control Lists (ACLs) on the target folder.

## Hướng dẫn nhanh (Tiếng Việt)
1. Nếu bạn vừa được cấp quyền vào thư mục chung mới, bạn BẮT BUỘC phải Đăng xuất (Sign out) Windows rồi đăng nhập lại để hệ thống nạp token quyền mới (chỉ Khóa màn hình Lock Screen sẽ không có tác dụng).
2. Hoặc mở cmd chạy lệnh `klist purge` rồi chạy `gpupdate /force` để làm mới vé Kerberos.
3. Nếu ổ đĩa mạng (Z:, Y:) có dấu chéo đỏ, mở cmd gõ `net use Z: /delete` rồi kết nối lại.
4. Nếu vẫn báo Access Denied, báo IT kiểm tra xem tài khoản AD của bạn đã được thêm vào nhóm phân quyền (Security Group) của thư mục đó chưa.

## Source and scope
- Microsoft Learn, [Troubleshoot 'Access Denied' errors in shared folders](https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/troubleshoot-access-denied-in-shared-folders), accessed 2026-10-06.
