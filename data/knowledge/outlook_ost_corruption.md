# Outlook Data File (.OST / .PST) Corruption and Repair

## Symptoms
- Outlook displays startup error: 'Cannot start Microsoft Outlook. Cannot open the Outlook window. The set of folders cannot be opened'.
- Error: 'Errors have been detected in the file C:\Users\...\AppData\Local\Microsoft\Outlook\user@company.com.ost'.
- Outlook freezes, enters continuous 'Loading Profile...' or 'Not Responding' state upon launch.

## Checks
1. Close all Outlook processes via Task Manager (`outlook.exe`).
2. Locate the offline cache data file at `%LOCALAPPDATA%\Microsoft\Outlook`.
3. Check the file size of the `.ost` file; if it exceeds 50 GB, Outlook may experience corrupt indexing headers.
4. Try launching Outlook in Safe Mode: press Win+R > type `outlook.exe /safe` > press Enter.

## Resolution
- For Exchange/Microsoft 365 accounts: Re-create the `.ost` cache file (Safe and standard procedure):
  1. Close Outlook completely.
  2. Press Win+R > type `%LOCALAPPDATA%\Microsoft\Outlook` > press Enter.
  3. Rename `user@company.com.ost` to `user@company.com.ost.old`.
  4. Launch Outlook: Outlook will automatically create a fresh `.ost` file and re-synchronize emails from the Exchange server.
- For POP3 local `.pst` archives: Run the Inbox Repair Tool (`scanpst.exe` located in `C:\Program Files\Microsoft Office\root\Office16`):
  Browse to the `.pst` file, click Start, and click Repair.

## Escalation
If profile recreation fails with autodiscover errors, open a ticket for IT Helpdesk to rebuild the Windows Mail profile in Control Panel > Mail (Microsoft Outlook).

## Hướng dẫn nhanh (Tiếng Việt)
1. Nhấn chuột phải vào thanh Taskbar mở Task Manager, tìm `Microsoft Outlook` và bấm End Task để đóng hoàn toàn.
2. Thử mở Outlook ở chế độ Safe Mode bằng cách nhấn Win+R gõ `outlook.exe /safe`.
3. Nếu file dữ liệu `.ost` bị lỗi, nhấn Win+R gõ `%localappdata%\Microsoft\Outlook`, đổi tên file `.ost` thành `.old`. Khi mở lại Outlook, hệ thống sẽ tự động tải lại hòm thư mới từ máy chủ.
4. Đối với file lưu trữ `.pst` cá nhân, sử dụng công cụ `scanpst.exe` có sẵn của Office để quét và sửa lỗi.

## Source and scope
- Microsoft Learn, [Repair Outlook Data Files (.pst and .ost)](https://support.microsoft.com/en-us/office/repair-outlook-data-files-pst-and-ost-25663bc3-11ec-4412-86c4-60488afc52f0), accessed 2026-10-06.
