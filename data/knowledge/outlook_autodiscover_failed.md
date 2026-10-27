# Xử lý lỗi Exchange Autodiscover khi cấu hình tài khoản Microsoft Outlook

**Từ khóa:** Outlook, Autodiscover, cấu hình mail, thêm tài khoản, Exchange, Office 365, Outlook 2016, Outlook 2019, không tìm thấy máy chủ, CNAME, DNS mail, thiết lập email.

## Triệu chứng / Dấu hiệu nhận biết
- Khi thêm tài khoản email công ty mới vào Outlook (2016, 2019, 2021 hoặc Office 365), hệ thống dò tìm cấu hình rất lâu rồi báo lỗi: "An encrypted connection to your mail server is not available" hoặc "Searching for your mail server settings... Failed".
- Xuất hiện hộp thoại yêu cầu nhập thông số máy chủ thủ công (Manual Setup) do không tìm thấy dịch vụ tự động Autodiscover.
- Cửa sổ yêu cầu mật khẩu hiển thị liên tục lặp đi lặp lại nhưng không thể hoàn tất thiết lập.

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra chính xác địa chỉ email và mật khẩu:** Nhập cẩn thận từng ký tự địa chỉ email đầy đủ (bao gồm cả phần đuôi `@company.com`) và mật khẩu tài khoản.
2. **Kiểm tra mạng nội bộ hoặc DNS:** Đảm bảo máy tính đang kết nối đúng mạng Wi-Fi hoặc mạng dây LAN nội bộ công ty (vì dịch vụ Autodiscover nội bộ chỉ phân giải được qua DNS công ty).
3. **Đăng nhập thử trên Webmail:** Truy cập cổng Webmail bằng trình duyệt để chắc chắn tài khoản email không bị khóa và mật khẩu hoàn toàn chính xác.
4. **Khởi động lại máy tính:** Khởi động lại hệ điều hành Windows để làm mới bộ nhớ đệm phân giải tên miền.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Máy tính bên ngoài mạng công ty không thể tự động nhận diện thông số máy chủ qua Autodiscover CNAME công khai.
- Cần quản trị viên IT cung cấp thông số cấu hình máy chủ Exchange / Office 365 thủ công cho các phiên bản Outlook đời cũ (2016/2019).
- Cần IT kiểm tra bản ghi DNS Autodiscover hoặc cấu hình chứng thư số SSL trên máy chủ thư điện tử.
