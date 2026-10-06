# Multifunction Printer Scan to Folder (SMB) Error Troubleshooting

## Symptoms
- User scans document on office photocopier/MFP, but scanned PDF never arrives in their shared PC folder.
- Printer LCD displays error: 'Server connection error', 'SMB Transmission failed (Code 0x0C)', or 'Authentication failed'.

## Checks
1. Verify the shared scan folder exists on the user computer (e.g., `C:\Scans`) and is shared with appropriate permissions.
2. Verify user Windows account password has not changed recently. MFP stores saved credentials in its address book.
3. Check if SMBv1 is required by older legacy scanners, or if SMBv2/SMBv3 signing restrictions block connection.
4. Check if Windows Defender Firewall blocks inbound TCP port 445 (File and Printer Sharing).

## Resolution
- Update credentials in Printer Address Book:
  1. Access printer web interface (`http://<printer_ip>`) as admin.
  2. Navigate to Address Book > Edit user entry > update username (`DOMAIN\username`) and new corporate password.
- Verify NTFS and Sharing permissions on scan folder:
  1. Right-click `C:\Scans` > Properties > Sharing tab > Advanced Sharing > Permissions > Ensure user has Full Control.
  2. Security tab > Ensure user account has Modify/Write permissions.
- In Windows Firewall, ensure 'File and Printer Sharing (SMB-In)' is allowed on Private/Domain network profile.

## Escalation
If corporate security policies disable NTLMv1/SMBv1 across domain machines, coordinate with Office Admin to configure Scan to Email (SMTP) instead of Scan to Folder.

## Hướng dẫn nhanh (Tiếng Việt)
1. Nếu bạn vừa đổi mật khẩu máy tính, cần vào trang web quản trị của máy in (hoặc báo IT) cập nhật lại mật khẩu mới cho mục Scan của bạn.
2. Kiểm tra thư mục scan trên máy tính (ví dụ `C:\Scans`) có đang được bật Share và cấp quyền Write/Modify không.
3. Kiểm tra Firewall Windows không chặn tính năng File and Printer Sharing trên mạng công ty.
4. Trong trường hợp máy in đời cũ không hỗ trợ SMBv2/v3, đề xuất chuyển sang phương thức Scan to Email.

## Source and scope
- Microsoft Learn, [Troubleshoot SMB file and printer sharing issues](https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/troubleshoot-smb-issues), accessed 2026-10-06.
