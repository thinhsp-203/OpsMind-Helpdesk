# Hướng dẫn cài đặt driver máy in để bàn và máy photocopy qua mạng LAN

**Từ khóa:** cài đặt driver máy in, thêm máy in, kết nối máy in qua mạng, máy in để bàn, máy in photocopy, Canon, HP, Ricoh, Toshiba, TCP/IP port, Print Management, Windows 11, driver máy in.

## Triệu chứng / Dấu hiệu nhận biết
- Máy tính mới bàn giao hoặc vừa cài lại hệ điều hành Windows 11 chưa có sẵn máy in văn phòng.
- In tài liệu xuất hiện các ký tự rác lạ mắt, chữ bị vỡ hoặc in sai khổ giấy do máy tính đang dùng driver mặc định Generic/Microsoft thay vì driver chuẩn của nhà sản xuất.
- Khi bấm thêm máy in trong Windows hiển thị thông báo thiếu driver (Missing driver) hoặc yêu cầu quyền Quản trị viên (Administrator).

## Các bước tự khắc phục nhanh (Self-service)
1. **Tìm kiếm máy in tự động trong mạng nội bộ:**
   - Đảm bảo máy tính đang kết nối cùng mạng Wi-Fi hoặc mạng dây LAN với máy in.
   - Vào *Settings -> Bluetooth & devices -> Printers & scanners*, chọn nút *Add device*.
   - Chờ Windows quét danh sách máy in trong mạng. Nếu thấy tên máy in văn phòng (ví dụ: Canon LBP, Ricoh Aficio), bấm nút *Add device* để hệ thống tự tải driver tương thích.
2. **Thêm máy in bằng địa chỉ IP (Nếu biết địa chỉ IP):**
   - Nếu quét tự động không thấy, bấm dòng chữ *Add manually*.
   - Chọn *Add a printer using an IP address or hostname*, chọn giao diện *TCP/IP Device*.
   - Nhập chính xác địa chỉ IP của máy in do IT niêm yết trên thân máy (ví dụ: `192.168.1.200`) rồi bấm Next.
3. **In thử trang kiểm tra (Print Test Page):** Sau khi máy in đã được cài xong, vào *Printer properties* bấm nút *Print Test Page* để kiểm tra chất lượng bản in.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Windows yêu cầu mật khẩu Quản trị viên (Admin credentials) để cho phép cài đặt driver vào hệ thống.
- Các dòng máy in photocopy đa chức năng chuyên dụng (Ricoh, Toshiba, Xerox) yêu cầu bộ cài driver chuẩn PCL6/PostScript và mã xác thực hạch toán in ấn (User Code / Department Code).
- Cần IT hỗ trợ triển khai kết nối máy in tự động thông qua chính sách Group Policy (GPO) hoặc Print Server của công ty.
