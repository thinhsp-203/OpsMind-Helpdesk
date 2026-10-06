# Windows Blue Screen of Death (BSOD) Crash Triage

## Symptoms
- System crashes abruptly to a blue screen displaying 'Your PC ran into a problem and needs to restart'.
- Stop codes: `CRITICAL_PROCESS_DIED`, `PAGE_FAULT_IN_NONPAGED_AREA`, `IRQL_NOT_LESS_OR_EQUAL`, `KERNEL_SECURITY_CHECK_FAILURE`.
- Computer enters a recurring reboot loop (Automatic Repair loop).

## Checks
1. Record the exact Stop Code and the failing driver file shown on the blue screen (e.g., `nvlddmkm.sys`, `netwtw10.sys`, `iaStorA.sys`).
2. Check if a new hardware peripheral, docking station, or RAM module was recently installed.
3. Check if a major Windows Update or BIOS update was applied immediately prior to the crash.
4. Verify whether the PC can boot successfully into Windows Safe Mode.

## Resolution
- If crash occurred after driver or Windows update:
  1. Boot into Windows Recovery Environment (WinRE) by holding Shift while clicking Restart.
  2. Troubleshoot > Advanced options > Uninstall Updates (Uninstall latest quality or feature update).
- Run System File Checker and DISM image repair in Command Prompt (Administrator):
  ```cmd
  DISM /Online /Cleanup-Image /RestoreHealth
  sfc /scannow
  ```
- Run Memory Diagnostic to rule out faulty RAM hardware: Press Win+R > type `mdsched.exe` > select 'Restart now and check for problems'.
- Check Minidump files located at `C:\Windows\Minidump` using BlueScreenView or WinDbg for root cause identification.

## Escalation
If memory diagnostics report hardware errors or BSOD persists in Safe Mode, log a Priority 1 Hardware Incident for IT Helpdesk to replace memory modules or storage SSD.

## Hướng dẫn nhanh (Tiếng Việt)
1. Dùng điện thoại chụp lại màn hình xanh, đặc biệt là dòng mã lỗi 'Stop Code' và tên file `.sys` (nếu có).
2. Nếu máy bị khởi động lại liên tục, giữ phím Shift khi bấm Restart để vào màn hình Recovery > chọn Uninstall Updates để gỡ bản cập nhật vừa cài.
3. Mở Command Prompt (Admin) chạy lệnh `sfc /scannow` để Windows tự động tìm và vá các file hệ thống bị hỏng.
4. Bấm Win+R gõ `mdsched.exe` để kiểm tra xem thanh RAM có bị lỗi phần cứng hay không.

## Source and scope
- Microsoft Support, [Troubleshoot blue screen errors in Windows](https://support.microsoft.com/en-us/windows/troubleshoot-blue-screen-errors-in-windows-5c62726c-6489-52da-a372-3f73142c14ad), accessed 2026-10-06.
