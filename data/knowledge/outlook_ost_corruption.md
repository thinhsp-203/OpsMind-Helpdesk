# Outlook Data File (.OST / .PST) Corruption and Repair

**Từ khóa:** tệp OST, file OST hỏng, lỗi dữ liệu Outlook, sửa lỗi OST, tạo lại profile Outlook, lỗi mở hòm thư, SCANPST.

## Symptoms
- Outlook displays startup error: 'Cannot start Microsoft Outlook. Cannot open the Outlook window. The set of folders cannot be opened'.
- Error: 'Errors have been detected in the file C:\Users\...\AppData\Local\Microsoft\Outlook\user@company.com.ost'.
- Outlook freezes, enters continuous 'Loading Profile...' or 'Not Responding' state upon launch.

## Checks
1. Close all Outlook processes via Task Manager (`outlook.exe`).
2. Verify Webmail status: Log in to Webmail (`https://outlook.office.com`) to confirm that server mailbox data is intact.
3. Locate the offline cache data file at `%LOCALAPPDATA%\Microsoft\Outlook`.
4. Try launching Outlook in Safe Mode: press Win+R > type `outlook.exe /safe` > press Enter.

## Resolution
- Prerequisite & Synchronization Safety Check:
  Before modifying or recreating the `.ost` cache file, verify in Webmail that recent sent emails and calendar items have synchronized to the Exchange server. If Outlook was used offline with critical unsent messages in Outbox, contact IT Helpdesk for assistance before altering local files to prevent unsynced data loss.
- Safe Cache Re-creation (Preserving Rollback Backup):
  1. Close Outlook completely (ensure no `outlook.exe` process in Task Manager).
  2. Press Win+R > type `%LOCALAPPDATA%\Microsoft\Outlook` > press Enter.
  3. Rename `user@company.com.ost` to `user@company.com.ost.old` (do NOT delete directly, keeping the file for rollback if needed).
  4. Launch Outlook: Outlook will automatically create a fresh `.ost` cache file and re-synchronize all emails from the Exchange server.
- For POP3 local `.pst` archives: Run the Inbox Repair Tool (`scanpst.exe` located in `C:\Program Files\Microsoft Office\root\Office16`):
  Browse to the `.pst` file, click Start, and click Repair.

## Escalation
If profile recreation fails with autodiscover errors, open a ticket for IT Helpdesk to rebuild the Windows Mail profile in Control Panel > Mail (Microsoft Outlook).

## Hướng dẫn nhanh (Tiếng Việt)
1. Đăng nhập Webmail (`https://outlook.office.com`) xác nhận hòm thư trên máy chủ vẫn nguyên vẹn và các thư gần nhất đã được đồng bộ.
2. Nhấn chuột phải vào thanh Taskbar mở Task Manager, tìm `Microsoft Outlook` và bấm End Task để đóng hoàn toàn. Thử mở lại ở Safe Mode (`outlook.exe /safe`).
3. Nếu file dữ liệu `.ost` bị lỗi và không có thư kẹt chưa gửi, nhấn Win+R gõ `%localappdata%\Microsoft\Outlook`, đổi tên file `.ost` thành `.old` (giữ bản sao lưu rollback, không xóa thẳng). Khi mở lại Outlook, hệ thống sẽ tự động tải lại hòm thư mới từ máy chủ.
4. Đối với file lưu trữ `.pst` cá nhân, sử dụng công cụ `scanpst.exe` có sẵn của Office để quét và sửa lỗi.

## Source and scope
- Microsoft Learn, [Repair Outlook Data Files (.pst and .ost)](https://support.microsoft.com/en-us/office/repair-outlook-data-files-pst-and-ost-25663bc3-11ec-4412-86c4-60488afc52f0), accessed 2026-10-06.
