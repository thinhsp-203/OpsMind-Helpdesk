# Khắc phục sự cố kết nối VPN FortiClient (Chính sách Lễ tân & IT)

**Từ khóa:** VPN, FortiClient, kết nối VPN, cổng VPN, cổng kết nối, gateway outage, client version, certificate, chứng thư, supported client, chuyển đội mạng, liên hệ IT Security, làm việc từ xa, remote access, authentication timeout, kiểm tra mạng.

> **QUY ĐỊNH ĐẶC THÙ VỀ VPN NỘI BỘ:**
> Hệ thống VPN công ty chỉ cấp và cho phép sử dụng đối với nhân sự thuộc bộ phận **Lễ tân** và **IT**. Nhân sự thuộc các phòng ban khác khi có nhu cầu làm việc từ xa cần có phê duyệt từ Quản lý trực tiếp/Giám đốc và liên hệ IT để được xem xét ngoại lệ đặc biệt.

## Triệu chứng / Dấu hiệu nhận biết
- Phần mềm FortiClient VPN báo lỗi không kết nối được đến cổng VPN công ty hoặc dừng lại ở mức 40% - 98%.
- Không kết nối được VPN FortiClient sau khi chứng thư hết hạn hoặc cập nhật phiên bản mới.
- Báo lỗi 'Authentication timeout', sai thông tin đăng nhập hoặc kết nối cổng VPN báo timeout.
- User receives notification: 'VPN connection fails after a certificate update' or gateway unavailable.

## Các bước người dùng tự khắc phục nhanh (Self-service)
1. **Kiểm tra kết nối mạng (Internet check):** Đảm bảo máy tính đã kết nối internet ổn định (duyệt được web bình thường) trước khi khởi chạy kết nối VPN FortiClient.
2. **Kiểm tra thông số cấu hình cổng VPN:**
   - Mở FortiClient -> Chọn cấu hình VPN công ty.
   - Kiểm tra địa chỉ cổng VPN (Remote Gateway) và cổng kết nối (Port) có khớp với tài liệu hướng dẫn của IT hay không.
3. **Kiểm tra tài khoản và chứng thư:** Xác nhận nhập đúng tên người dùng (corporate account) và mật khẩu, kiểm tra ngày giờ máy tính để tránh lỗi xác thực chứng thư (certificate).
4. **Kiểm tra phiên bản phần mềm (Supported client):** Đảm bảo máy tính đang cài phiên bản FortiClient được bộ phận IT chuẩn hóa, không tự ý cài đặt các bản client không được hỗ trợ.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- **Người dùng không thuộc Lễ tân hoặc IT:** Hướng dẫn người dùng gửi phiếu yêu cầu kèm phê duyệt của Quản lý để IT xem xét cấp tài khoản VPN ngoại lệ.
- **Lỗi chứng thư hoặc cổng VPN (Gateway outage):** Cổng kết nối máy chủ VPN gặp sự cố hoặc chứng thư số máy chủ hết hạn -> Chuyển đội mạng (network team) hoặc liên hệ IT Security xử lý khẩn cấp.
- **Tài khoản VPN bị khóa hoặc lỗi xác thực xác minh 2 bước:** Chuyển ticket cho IT Service Desk để kiểm tra chính sách tài khoản và phân quyền truy cập.
