# Xử lý lỗi kết nối và chứng chỉ OpenVPN Client (Chính sách Lễ tân & IT)

**Từ khóa:** OpenVPN, lỗi openvpn, kết nối openvpn, ngắt kết nối, server nội bộ, TLS error, chứng chỉ TLS, file ovpn, đồng bộ thời gian, client certificate, kết nối bị ngắt, lỗi chứng chỉ.

> **QUY ĐỊNH ĐẶC THÙ VỀ VPN NỘI BỘ:**
> Hệ thống VPN công ty chỉ cấp và cho phép sử dụng đối với nhân sự thuộc bộ phận **Lễ tân** và **IT**. Nhân sự thuộc các phòng ban khác khi có nhu cầu làm việc từ xa cần có phê duyệt từ Quản lý trực tiếp/Giám đốc và liên hệ IT để được xem xét ngoại lệ đặc biệt.

## Triệu chứng / Dấu hiệu nhận biết
- Kết nối OpenVPN bị ngắt giữa chừng và không vào được server nội bộ công ty.
- Biểu tượng OpenVPN Client hiển thị màu vàng liên tục hoặc ngắt kết nối hiển thị biểu tượng màu đỏ.
- Nhật ký kết nối (Log) xuất hiện lỗi: `TLS Error: TLS key negotiation failed to occur within 60 seconds` hoặc `VERIFY ERROR: certificate has expired`.
- Ứng dụng OpenVPN báo lỗi chứng chỉ máy khách (client certificate) không hợp lệ hoặc hết hạn.

## Các bước người dùng tự khắc phục nhanh (Self-service)
1. **Kiểm tra kết nối internet:** Kiểm tra đường truyền Wi-Fi hoặc mạng dây tại nhà đảm bảo kết nối internet đang hoạt động ổn định.
2. **Đồng bộ thời gian hệ thống:** Vào Windows Settings -> Time & Language -> Nhấn **Sync now** để đồng bộ thời gian chuẩn xác, tránh lỗi kiểm tra tính hợp lệ của chứng chỉ TLS.
3. **Khởi động lại OpenVPN Client:** Nhấp chuột phải vào biểu tượng OpenVPN dưới khay hệ thống -> Chọn Disconnect -> Chờ 10 giây -> Nhấp Connect lại.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- **Người dùng không thuộc diện cấp VPN:** Thông báo chính sách VPN chỉ áp dụng cho bộ phận Lễ tân và IT; chuyển ticket yêu cầu phê duyệt từ cấp quản lý.
- **Chứng chỉ TLS / File cấu hình .ovpn hết hạn:** Cần IT Quản trị cấp lại bộ tệp cấu hình mới kèm client certificate hợp lệ.
- **Sự cố máy chủ OpenVPN Server nội bộ:** Nếu nhiều nhân sự trong bộ phận IT / Lễ tân cùng mất kết nối đến server nội bộ, chuyển thẳng cho IT Hạ tầng kiểm tra Gateway VPN.
