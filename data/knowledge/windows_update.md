# Windows Update and Software Patching

## Symptoms
- Updates fail repeatedly.
- Device shows update pending for hours.
- User cannot install new software because a required patch is stuck.

## Procedure
1. Check whether the device has enough disk space.
2. Restart the Windows Update service if there is a stale update state.
3. Run Windows Update troubleshooting from the Settings panel.
4. Remove the problematic update package if it triggers repeated failure.

## Resolution
- Reboot the device after deleting stuck update files from the local cache.
- Run the update again after the service is restarted.
- If the problem persists, confirm the device time and time zone are correct.
- For corporate-managed devices, validate the group policy configuration for patch deployment.

## Escalation
Escalate to the endpoint management team if the issue affects multiple machines or the update service is failing at the organization level.

## Hướng dẫn nhanh (Tiếng Việt)
1. Kiểm tra dung lượng ổ đĩa, nguồn điện và kết nối mạng ổn định.
2. Khởi động lại máy một lần nếu có yêu cầu restart đang chờ.
3. Dùng Windows Update Troubleshooter; không tắt công cụ bảo vệ hoặc bỏ qua chính sách cập nhật của công ty.
4. Nếu máy quản lý tập trung hoặc nhiều thiết bị cùng lỗi, gửi mã lỗi và thời điểm cho đội Endpoint Management.
