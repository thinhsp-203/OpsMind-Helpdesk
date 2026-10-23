# Khắc phục lỗi máy in để bàn và máy photocopy báo trạng thái Offline

**Từ khóa:** máy in offline, máy in ngoại tuyến, máy in không nhận, mất kết nối máy in, SNMP, trạng thái offline, máy in photocopy, máy in để bàn, IP máy in, Print Spooler, cáp mạng máy in.

## Triệu chứng / Dấu hiệu nhận biết
- Trong danh sách máy in của Windows, tên máy in hiển thị chữ mờ đi kèm thông báo trạng thái "Offline" (Ngoại tuyến).
- Khi bấm in, Windows thông báo: "Printer is offline. Check connection" và không gửi được lệnh in đến thiết bị.
- Sự cố xảy ra với cả máy in để bàn cắm cổng USB/mạng hoặc máy in photocopy đa chức năng kết nối qua mạng LAN.

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra dây cáp và nguồn điện:**
   - Đối với máy in để bàn cắm USB: Kiểm tra dây cáp USB cắm chắc chắn vào cả máy in và máy tính.
   - Đối với máy in kết nối mạng (Network Printer): Kiểm tra dây cáp mạng cắm vào phía sau máy in, đèn cổng mạng (xanh/cam) phải sáng nhấp nháy. Đảm bảo màn hình máy in đã bật và không ở chế độ ngủ sâu (Sleep).
2. **Kiểm tra tùy chọn "Use Printer Offline" trong Windows:**
   - Mở *Open print queue* của máy in bị lỗi.
   - Nhấp vào menu *Printer* ở góc trên cửa sổ.
   - Nếu mục *Use Printer Offline* đang có dấu tích chọn, hãy nhấp vào đó để bỏ tích.
3. **Thử tắt tính năng SNMP Status Enabled:**
   - Vào *Control Panel -> Devices and Printers*, nhấp chuột phải vào máy in chọn *Printer properties*.
   - Chuyển sang thẻ *Ports*, chọn cổng IP của máy in rồi bấm *Configure Port*.
   - Nếu có mục *SNMP Status Enabled*, thử bỏ dấu tích ở ô này rồi bấm OK để khắc phục trường hợp giao thức SNMP bị chặn bởi tường lửa.
4. **Khởi động lại máy in và máy tính:** Tắt bật lại máy in và khởi động lại máy tính để làm mới nhận diện thiết bị.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Địa chỉ IP của máy in hoặc máy photocopy bị thay đổi do máy chủ DHCP cấp lại địa chỉ mới khác với cổng in đã cấu hình trên máy tính.
- Card mạng trên máy photocopy bị lỗi phần cứng không nhận tín hiệu mạng nội bộ.
- Cần IT cấu hình lại địa chỉ IP tĩnh (Static IP) chuẩn cho máy in và chia sẻ lại trên mạng nội bộ.
