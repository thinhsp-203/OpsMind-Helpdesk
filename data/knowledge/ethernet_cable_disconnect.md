# Khắc phục lỗi mất kết nối mạng dây LAN và thông báo Cable Unplugged

**Từ khóa:** cáp mạng, dây mạng, ethernet, ngắt kết nối, cáp bị rút, cable unplugged, quả cầu gạch chéo, mạng dây, cổng LAN, cổng RJ45, switch mạng, mạng nội bộ.

## Triệu chứng / Dấu hiệu nhận biết
- Biểu tượng mạng ở góc phải dưới thanh Taskbar hiển thị hình quả cầu có dấu gạch chéo màu đỏ hoặc dấu chấm than tam giác vàng.
- Cửa sổ Network Connections hiển thị card mạng Ethernet ở trạng thái "Network cable unplugged" (Dây cáp mạng chưa cắm hoặc bị ngắt kết nối).
- Đèn tín hiệu đèn LED (xanh/cam) ở cổng mạng RJ45 phía sau máy tính hoặc trên dock cắm laptop bị tắt hoàn toàn.

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra và cắm chặt lại đầu cáp mạng (Cổng RJ45):**
   - Rút nhẹ đầu bấm cáp mạng RJ45 ở cổng máy tính ra, kiểm tra xem lẫy nhựa có bị gãy hay không, cắm lại thật chặt sao cho nghe tiếng "tách" nhỏ.
   - Lần theo dây cáp mạng đến ổ cắm mạng trên tường (Wall plate) hoặc switch mạng nhánh dưới chân bàn, rút ra cắm lại tương tự.
2. **Quan sát đèn tín hiệu cổng mạng:** Sau khi cắm chặt, quan sát đèn LED tại cổng mạng trên thân máy. Đèn phải sáng đứng màu xanh lá cây hoặc nhấp nháy màu vàng cam thể hiện có tín hiệu truyền nhận dữ liệu.
3. **Thử đổi sang dây cáp mạng khác:** Nếu có sẵn một sợi dây cáp mạng hoạt động tốt bên cạnh, hãy mượn cắm thử vào máy tính để xác định lỗi do sợi dây cáp bị đứt ngầm hay do card mạng của máy tính.
4. **Khởi động lại card mạng:** Nhấn `Windows + R`, gõ `ncpa.cpl` rồi nhấn Enter. Nhấp chuột phải vào biểu tượng *Ethernet* -> chọn *Disable*, chờ 5 giây rồi nhấp chuột phải chọn *Enable* để bật lại.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Đã thay dây mạng mới và cắm các cổng khác nhưng đèn tín hiệu cổng RJ45 trên máy tính vẫn không sáng (nghi ngờ hỏng card mạng onboard).
- Toàn bộ dãy bàn hoặc toàn phòng làm việc đều bị mất mạng dây cùng lúc (nghi ngờ thiết bị switch mạng trung tâm của tầng bị mất nguồn hoặc lỗi cổng uplink).
- Đầu hạt mạng RJ45 hoặc ổ cắm âm tường bị gãy vỡ, cần IT mang kìm bấm mạng chuyên dụng bấm lại đầu dây mới.
