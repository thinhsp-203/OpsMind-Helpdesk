# Hướng dẫn cấu hình Proxy và tệp PAC truy cập mạng nội bộ

**Từ khóa:** Proxy, tệp PAC, không tải được trang web nội bộ, proxy bypass, cấu hình mạng, winhttp, mạng công ty, netsh, proxy server.

## Triệu chứng / Dấu hiệu nhận biết
- Trình duyệt web Chrome, Edge thông báo lỗi: "The proxy server is refusing connections" hoặc "ERR_PROXY_CONNECTION_FAILED".
- Không thể truy cập được các trang web nghiệp vụ nội bộ hoặc không vào được Internet dù máy tính vẫn hiển thị biểu tượng kết nối mạng.
- Cài đặt Proxy trên máy tính tự ý bị bật lên hoặc trỏ sai đường dẫn tệp PAC cấu hình tự động.

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra thiết lập Proxy trong Windows Settings:**
   - Vào *Settings -> Network & internet -> Proxy*.
   - Tại mục *Automatically detect settings*: Bật sang **On**.
   - Tại mục *Use setup script*: Nếu công ty có quy định dùng file PAC, kiểm tra đường dẫn script xem có chính xác hay không.
   - Tại mục *Manual proxy setup*: Nếu không có yêu cầu dùng Proxy thủ công, hãy tắt mục *Use a proxy server* sang **Off**.
2. **Khởi động lại trình duyệt web:** Tắt hẳn trình duyệt Chrome/Edge rồi mở lại để áp dụng cài đặt mạng mới.
3. **Đặt lại cấu hình Proxy WinHTTP bằng dòng lệnh:**
   - Nhấn phím `Windows + R`, gõ `cmd` rồi nhấn Enter.
   - Chạy lệnh sau để đặt lại cấu hình proxy cho các tiến trình hệ điều hành:
     ```cmd
     netsh winhttp reset proxy
     ```
4. **Khởi động lại máy tính:** Khởi động lại máy tính để hệ điều hành làm mới toàn bộ tiến trình mạng.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Cài đặt Proxy bị khóa cứng bởi chính sách quản trị tập trung (Group Policy) và người dùng không thể tự thay đổi.
- Cần quản trị viên IT cung cấp đường dẫn tệp PAC chuẩn hoặc danh sách các dải IP được miễn trừ qua Proxy (Bypass Proxy).
- Máy chủ Proxy trung gian của công ty gặp sự cố ngắt quãng dịch vụ.
