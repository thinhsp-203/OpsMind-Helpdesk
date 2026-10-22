# High CPU, RAM, and 100% Disk Usage Performance Fix

**Từ khóa:** quạt kêu to, máy nóng, đơ máy, treo máy, chậm máy, CPU cao, 100% disk, đầy ổ cứng, RAM đầy, SysMain, Task Manager, hiệu năng kém.

## Symptoms
- PC response is sluggish; applications take over 30 seconds to launch or freeze with 'Not Responding'.
- Laptop cooling fans run at maximum speed continuously even when idle.
- Task Manager shows CPU, Memory, or Disk usage pinned at 99%-100%.

## Checks
1. Press Ctrl+Shift+Esc to open Task Manager > click on Processes tab.
2. Sort columns by CPU, Memory, and Disk to identify top offending processes.
3. Common high usage services: `SysMain`, `Antimalware Service Executable`, `Windows Modules Installer Worker (TiWorker.exe)`, `WmiPrvSE.exe`.
4. Check available storage on drive `C:\`; storage below 10% free capacity causes severe Windows virtual memory thrashing.

## Resolution
- User Self-Service Actions (Safe & Recommended):
  1. Sort Task Manager to identify runaway user processes and close heavy unneeded applications or browser tabs.
  2. Disable unneeded startup applications: Task Manager > Startup apps tab > Disable unnecessary third-party utilities.
  3. Run Disk Cleanup: Run `cleanmgr.exe` > select Drive C > clean temporary user files to free disk space.
  4. Ensure drive C: has at least 15-20 GB of free space for virtual memory paging file.
  5. Restart the computer to clear leaked memory handles.
- IT Tier 2 Administration Actions (Requires Local Administrator Privileges):
  1. If disk usage remains pegged at 100% after restart, an authorized IT technician may inspect `SysMain` (SuperFetch) in `services.msc` for diagnosis (avoid permanent disabling without corporate baseline review).
  2. If Windows Update indexing is corrupt, IT Administrator stops Windows Update service (`net stop wuauserv`), cleans corrupted update cache in `C:\Windows\SoftwareDistribution`, and restarts the service.

## Escalation
If high disk usage is accompanied by mechanical clicking noises or disk read errors, immediately back up user data and request an SSD replacement from IT Hardware team.

## Hướng dẫn nhanh (Tiếng Việt)
1. Nhấn `Ctrl + Shift + Esc` mở Task Manager, bấm vào cột Disk hoặc CPU để xem ứng dụng nào đang ngốn 100% tài nguyên. Đóng các tab trình duyệt hoặc ứng dụng nặng không dùng.
2. Tắt các ứng dụng tự khởi động cùng máy: Vào thẻ Startup apps trong Task Manager và Disable các phần mềm bên thứ ba không cần thiết.
3. Kiểm tra ổ đĩa C: chạy công cụ dọn đĩa `cleanmgr.exe` và bảo đảm ổ đĩa trống tối thiểu 15-20 GB để Windows có không gian tạo bộ nhớ ảo (virtual memory).
4. Khởi động lại máy tính. Nếu tình trạng 100% disk vẫn kéo dài sau khi khởi động, tạo ticket yêu cầu Kỹ thuật viên CNTT kiểm tra dịch vụ hệ thống và phần cứng ổ đĩa (người dùng không tự ý tắt dịch vụ hệ thống).

## Source and scope
- Microsoft Support, [Tips to improve PC performance in Windows](https://support.microsoft.com/en-us/windows/tips-to-improve-pc-performance-in-windows-b3b3ef5b-5953-fb62-2c31-ffade2652b30), accessed 2026-10-06.
