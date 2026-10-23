# Định tuyến VPN Split Tunnel và truy cập dịch vụ cục bộ (Chính sách Lễ tân & IT)

**Từ khóa:** VPN Split Tunnel, Split Tunnel, VPN chậm mạng, dịch vụ cục bộ, mất mạng cục bộ khi bật VPN, không vào được máy in nội bộ khi bật VPN, định tuyến VPN, split tunneling, subnet routing, mạng chậm.

> **QUY ĐỊNH ĐẶC THÙ VỀ VPN NỘI BỘ:**
> Hệ thống VPN công ty chỉ cấp và cho phép sử dụng đối với nhân sự thuộc bộ phận **Lễ tân** và **IT**. Nhân sự thuộc các phòng ban khác khi có nhu cầu làm việc từ xa cần có phê duyệt từ Quản lý trực tiếp/Giám đốc và liên hệ IT để được xem xét ngoại lệ đặc biệt.

## Triệu chứng / Dấu hiệu nhận biết
- Bật VPN xong thì bị chậm mạng và không truy cập được các dịch vụ cục bộ (máy in Wi-Fi tại nhà, thiết bị lưu trữ NAS gia đình, hoặc router nội bộ mạng gia đình).
- Tốc độ duyệt web thông thường bị suy giảm nghiêm trọng do toàn bộ dữ liệu bị định tuyến qua cổng VPN công ty.
- Ứng dụng công ty mở bình thường nhưng các tài nguyên mạng cục bộ tại nơi làm việc từ xa bị gián đoạn.

## Các bước người dùng tự khắc phục nhanh (Self-service)
1. **Tạm ngắt kết nối khi in ấn tại nhà:** Nếu cần in ra máy in cục bộ hoặc truy cập thiết bị nội bộ gia đình, tạm ngắt kết nối VPN (Disconnect) để hoàn thành tác vụ in ấn.
2. **Kiểm tra dải địa chỉ IP mạng nhà:** Đảm bảo router gia đình không sử dụng trùng dải địa chỉ IP với mạng nội bộ công ty (ví dụ dải 10.0.0.0/8 hoặc 192.168.1.0/24 của hệ thống doanh nghiệp).
3. **Khởi động lại phần mềm VPN:** Ngắt kết nối và kết nối lại sau 30 giây để làm mới bảng định tuyến (routing table) của hệ điều hành.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- **Người dùng không thuộc Lễ tân / IT:** Nêu rõ quy định chỉ nhân sự Lễ tân và IT mới được kích hoạt VPN; người dùng khác cần gửi yêu cầu có xác nhận của trưởng bộ phận.
- **Cấu hình Split Tunneling:** Khi nhân sự Lễ tân / IT cần làm việc đồng thời giữa tài nguyên mạng công ty và thiết bị cục bộ, chuyển IT Network để cấu hình phân luồng Split Tunnel (chỉ định tuyến dải IP công ty qua VPN, lưu lượng internet và dịch vụ cục bộ đi trực tiếp qua mạng ngoài).
