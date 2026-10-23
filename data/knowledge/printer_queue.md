# Xử lý kẹt lệnh in và khởi động lại Print Spooler cho máy in để bàn và photocopy

**Từ khóa:** kẹt lệnh in, lệnh in bị kẹt, hàng đợi máy in, Print Spooler, máy in để bàn, máy photocopy, restart spooler, hủy lệnh in, hàng đợi, queue, driver, Windows 10, Windows 11.

## Triệu chứng / Dấu hiệu nhận biết
- Bấm lệnh in tài liệu từ Word, Excel hoặc PDF nhưng máy in không chạy, biểu tượng máy in xuất hiện ở thanh Taskbar với thông báo "1 document pending" hoặc "Error - Printing".
- Nhiều người trong văn phòng cùng in vào một máy in chia sẻ nhưng máy in dừng hoàn toàn, hàng đợi in (print queue) bị tắc nghẽn và các lệnh in sau không thể thực hiện được.
- Cửa sổ hàng đợi in hiển thị lệnh in ở trạng thái "Deleting..." hoặc "Restarting..." nhiều phút nhưng không biến mất.

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra trạng thái vật lý của máy in:** Kiểm tra máy in để bàn hoặc máy in photocopy xem có đang bị kẹt giấy (Paper Jam), hết giấy ở khay nạp, nắp máy bị hở hoặc hết mực báo đèn vàng hay không.
2. **Hủy lệnh in bị lỗi trong Print Queue:** Nhấp đúp vào biểu tượng máy in ở góc phải Taskbar (hoặc vào *Settings -> Bluetooth & devices -> Printers & scanners* chọn máy in -> chọn *Open print queue*). Nhấp chuột phải vào lệnh in đang bị kẹt đầu tiên -> chọn *Cancel* để hủy lệnh.
3. **Tắt bật lại nguồn máy in:** Tắt công tắc nguồn máy in, chờ khoảng 15 giây rồi bật lại để máy xóa bộ nhớ đệm tạm thời (Buffer).
4. **Khởi động lại dịch vụ Print Spooler trên máy tính:** Nếu hàng đợi vẫn kẹt:
   - Nhấn `Windows + R`, gõ `services.msc` rồi nhấn Enter.
   - Tìm dịch vụ tên là **Print Spooler**, nhấp chuột phải chọn **Restart**.
   - Sau khi Print Spooler khởi động lại, kiểm tra xem hàng đợi in đã được giải phóng hay chưa.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Lệnh in bị kẹt trên máy chủ in dùng chung của công ty (Print Server) mà người dùng cá nhân không có quyền xóa.
- Dịch vụ Print Spooler liên tục tự động dừng (crash) ngay sau khi khởi động (thường do xung đột driver máy in).
- Cần kỹ thuật viên IT can thiệp xóa các tệp đệm in hỏng trong thư mục hệ thống `C:\Windows\System32\spool\PRINTERS`.
