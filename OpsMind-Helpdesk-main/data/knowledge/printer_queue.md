# Printer Queue and Print Spooler

## Symptoms
- Jobs remain stuck in queue.
- Printer status is offline or paused.
- User cannot print from one application only.

## Checks
1. Verify the printer has power and is connected to the local network or USB port.
2. Confirm the selected printer and whether printing fails from more than one application.
3. Record whether the issue affects one user or a shared printer.
4. Have IT check the Print Spooler service, driver package, and relevant policy.

## Resolution
- If a job is stuck, IT can clear the print queue or restart the Print Spooler service with administrator permission.
- If the error is related to the driver, IT can update or reinstall the approved printer driver.
- For multifunction devices, ensure the correct tray and paper size are selected.

## Escalation
Escalate to the local IT technician if multiple users on the same shared printer are impacted or if the device itself is not reachable.

## Hướng dẫn nhanh (Tiếng Việt)
1. Kiểm tra máy in có nguồn, giấy và đang kết nối mạng.
2. Xác nhận đã chọn đúng máy in và khổ giấy.
3. Nếu lệnh in bị treo, mở hàng đợi in; IT có thể khởi động lại dịch vụ Print Spooler và xóa lệnh lỗi.
4. Nếu nhiều người cùng bị hoặc máy in không truy cập được, báo kỹ thuật viên tại chỗ; không tự cài driver từ nguồn lạ.

## Source and scope
- Microsoft Learn, [Printing issues caused by Print Spooler service not running](https://learn.microsoft.com/en-us/troubleshoot/windows-server/printing/print-spooler-service-not-running), accessed 2026-10-05. Covers stuck jobs, service restart, system-resource checks, Group Policy, drivers, and antivirus conflicts. Service and policy changes require IT administrator review.
