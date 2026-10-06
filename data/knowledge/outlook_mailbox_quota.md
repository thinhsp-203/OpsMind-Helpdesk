# Outlook Mailbox Storage Quota Exceeded and Cleanup

## Symptoms
- User receives bounce message (NDR): '554 5.2.2 mailbox full; message size 30000000 bytes exceeds size limit'.
- Outlook displays warning bar: 'Mailbox Cleanup: Your mailbox is full. You cannot send or receive new messages'.
- Outgoing emails remain stuck in Outbox indefinitely.

## Checks
1. In Outlook, click File tab > Info > check the 'Mailbox Cleanup' capacity bar (e.g., 49.5 GB of 50.0 GB used).
2. Right-click Deleted Items folder and Junk Email folder to check their current storage size.
3. Check Sent Items folder for large email attachments (> 20 MB).
4. Verify if Online Archive (In-Place Archive) is enabled for the user Exchange/M365 license.

## Resolution
- Empty the 'Deleted Items' folder: Right-click Deleted Items > 'Empty Folder'.
- Permanently purge recovered items: Open Deleted Items > click 'Recover Deleted Items from Server' > Purge unwanted items.
- Filter and remove large attachments:
  1. In Outlook search bar, type `hasattachments:yes size:verylarge (>25 MB)`.
  2. Save bulky attachments to OneDrive or company file share, then delete the heavy emails.
- Run Mailbox Cleanup Tool: File > Tools > Mailbox Cleanup > 'Find items older than 180 days'.
- Move old email folders into Online Archive or local PST archive (`.pst`).

## Escalation
If mailbox cleanup cannot reduce storage below quota due to business audit requirements, submit an IT ticket requesting an Exchange storage quota expansion (e.g., upgrade to Exchange Online Plan 2).

## Hướng dẫn nhanh (Tiếng Việt)
1. Vào Outlook > File > Info để xem dung lượng hòm thư đã dùng bao nhiêu GB.
2. Chuột phải vào thư mục 'Deleted Items' (Thùng rác) và 'Junk Email' (Thư rác) chọn 'Empty Folder' để xóa sạch các thư không cần thiết.
3. Tìm các email có file đính kèm nặng bằng cách gõ `size:>25MB` vào ô tìm kiếm, tải tệp lưu lên OneDrive rồi xóa email đi.
4. Di chuyển email các năm trước vào thư mục Online Archive (Lưu trữ trực tuyến) do công ty cấp.

## Source and scope
- Microsoft Support, [Manage my mailbox size in Outlook](https://support.microsoft.com/en-us/office/manage-my-mailbox-size-792b521c-3f4e-4e74-b328-0cd2492edd7d), accessed 2026-10-06.
