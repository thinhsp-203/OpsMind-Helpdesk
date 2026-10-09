# Windows Update and Software Patching

## Symptoms
- Updates fail repeatedly.
- Device shows update pending for hours.
- User cannot install new software because a required patch is stuck.

## Procedure
1. Check whether the device has enough disk space.
2. Confirm the device is connected to the internet, plugged into power, and has the correct date and time.
3. Run the Windows Update troubleshooter from Settings or Get Help.
4. On organization-managed devices, report the error code and contact endpoint management before changing update services or policies.

## Resolution
- Restart the device if Windows requests it, then retry the update.
- Back up important files before any repair that could affect system state.
- Do not manually delete update-cache files, remove update packages, change Group Policy, or disable protection as an end-user workaround; IT should select any advanced repair for a managed device.

## Escalation
Escalate to the endpoint management team if the issue affects multiple machines or the update service is failing at the organization level.

## Hướng dẫn nhanh (Tiếng Việt)
1. Kiểm tra dung lượng ổ đĩa, nguồn điện và kết nối mạng ổn định.
2. Khởi động lại máy một lần nếu có yêu cầu restart đang chờ.
3. Dùng Windows Update Troubleshooter; không tắt công cụ bảo vệ hoặc bỏ qua chính sách cập nhật của công ty.
4. Nếu máy quản lý tập trung hoặc nhiều thiết bị cùng lỗi, gửi mã lỗi và thời điểm cho đội Endpoint Management.

## Source and scope
- Microsoft Support, [Troubleshoot problems updating Windows](https://support.microsoft.com/en-us/windows/deployment/updates-lifecycle/troubleshoot-problems-updating-windows), accessed 2026-10-05. Supports using the Windows Update troubleshooter, checking connectivity, administrator access, external hardware, free space, and date/time; it advises backing up files before troubleshooting. Organization-specific patch policy must be checked by IT.
