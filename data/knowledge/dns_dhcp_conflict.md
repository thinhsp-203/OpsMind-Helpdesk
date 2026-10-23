# Khắc phục sự cố xung đột địa chỉ IP trong mạng LAN và xử lý lỗi DNS / DHCP

**Từ khóa:** DNS, DHCP, xung đột IP, trùng IP, lỗi phân giải tên miền, ipconfig, ipconfig /renew, nslookup, mạng LAN, cấp phát IP, router, xung đột địa chỉ IP.

## Triệu chứng / Dấu hiệu nhận biết
- Màn hình Windows hiện thông báo cảnh báo màu vàng ở góc phải: "Windows has detected an IP address conflict" (Xung đột địa chỉ IP).
- Máy tính đột ngột bị mất kết nối mạng Internet hoặc mất truy cập vào các dịch vụ mạng nội bộ sau khi có thiết bị lạ cắm vào mạng.
- Truy cập vào các trang web nội bộ qua tên miền (ví dụ: `company.internal`) bị báo lỗi không tìm thấy máy chủ (DNS probe finished nxdomain).

## Các bước tự khắc phục nhanh (Self-service)
1. **Giải phóng và xin cấp lại địa chỉ IP qua DHCP:**
   - Nhấn phím `Windows + R`, gõ `cmd` rồi nhấn Enter để mở cửa sổ dòng lệnh.
   - Gõ lệnh sau để giải phóng địa chỉ IP cũ:
     ```cmd
     ipconfig /release
     ```
   - Tiếp tục gõ lệnh sau để xin máy chủ DHCP cấp địa chỉ IP mới không bị trùng lặp:
     ```cmd
     ipconfig /renew
     ```
2. **Xóa bộ nhớ đệm phân giải tên miền (DNS Cache):**
   - Trong cửa sổ Command Prompt, gõ lệnh:
     ```cmd
     ipconfig /flushdns
     ```
3. **Kiểm tra phân giải tên miền bằng nslookup:**
   - Kiểm tra phân giải tên miền máy chủ nội bộ bằng lệnh:
     ```cmd
     nslookup company.internal
     ```
   - Kiểm tra phân giải tên miền Internet công cộng bằng lệnh:
     ```cmd
     nslookup google.com
     ```
4. **Khởi động lại máy tính:** Khởi động lại máy để hệ điều hành đăng ký lại địa chỉ IP duy nhất với switch và router mạng.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Đã chạy lệnh `ipconfig /renew` nhưng vẫn liên tục bị báo lỗi xung đột IP (do có thiết bị trong mạng đang bị đặt IP tĩnh trùng với dải IP động của DHCP).
- Cần quản trị viên IT đăng nhập vào Router / Switch mạng công ty để kiểm tra bảng ARP và cô lập thiết bị đang gây xung đột IP.
- Máy chủ DNS nội bộ của công ty gặp sự cố không thể phân giải tên miền nội bộ cho toàn bộ văn phòng.
