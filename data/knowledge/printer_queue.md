# Printer Queue and Print Spooler

## Symptoms
- Jobs remain stuck in queue.
- Printer status is offline or paused.
- User cannot print from one application only.

## Checks
1. Verify the printer has power and is connected to the local network or USB port.
2. Confirm the Windows print spooler service is running.
3. Clear the print queue if there are stale jobs.
4. Reinstall the network printer driver from the standard driver package.

## Resolution
- Restart the "Print Spooler" service.
- Clear the queue and resubmit the document after checking the selected printer.
- If the error is related to the driver, update or reinstall the printer driver.
- For multifunction devices, ensure the correct tray and paper size are selected.

## Escalation
Escalate to the local IT technician if multiple users on the same shared printer are impacted or if the device itself is not reachable.

## Hướng dẫn nhanh (Tiếng Việt)
1. Kiểm tra máy in có nguồn, giấy và đang kết nối mạng.
2. Xác nhận đã chọn đúng máy in và khổ giấy.
3. Nếu lệnh in bị treo, mở hàng đợi in; IT có thể khởi động lại dịch vụ Print Spooler và xóa lệnh lỗi.
4. Nếu nhiều người cùng bị hoặc máy in không truy cập được, báo kỹ thuật viên tại chỗ; không tự cài driver từ nguồn lạ.
