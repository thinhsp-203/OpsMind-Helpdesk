# High CPU, RAM, and 100% Disk Usage Performance Fix

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
- Resolve 100% Disk caused by SysMain (SuperFetch):
  1. Press Win+R > type `services.msc` > press Enter.
  2. Locate 'SysMain' > right-click Properties > set Startup type to 'Disabled' > click Stop > OK.
- Resolve runaway Windows Update indexing:
  Stop Windows Update service, clear cached temp updates in `C:\Windows\SoftwareDistribution`, and restart service.
- Disable unneeded startup applications: Task Manager > Startup apps tab > Disable unnecessary third-party utilities.
- Run disk cleanup: Run `cleanmgr.exe` > select Drive C > Clean up system files.

## Escalation
If high disk usage is accompanied by mechanical clicking noises or disk read errors, immediately back up user data and request an SSD replacement from IT Hardware team.

## Hướng dẫn nhanh (Tiếng Việt)
1. Nhấn `Ctrl + Shift + Esc` mở Task Manager, bấm vào cột Disk hoặc CPU để xem ứng dụng nào đang ngốn 100% tài nguyên.
2. Nhấn Win+R gõ `services.msc`, tìm dịch vụ `SysMain`, chuột phải chọn Properties > chỉnh Startup type thành `Disabled` và bấm Stop.
3. Tắt các ứng dụng tự khởi động cùng máy: Vào thẻ Startup apps trong Task Manager và Disable các phần mềm không cần thiết.
4. Kiểm tra ổ đĩa C: phải còn trống tối thiểu 15-20 GB để Windows có không gian tạo bộ nhớ ảo (virtual memory).

## Source and scope
- Microsoft Support, [Tips to improve PC performance in Windows](https://support.microsoft.com/en-us/windows/tips-to-improve-pc-performance-in-windows-b3b3ef5b-5953-fb62-2c31-ffade2652b30), accessed 2026-10-06.
