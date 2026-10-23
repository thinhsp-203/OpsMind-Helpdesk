# Hướng dẫn xử lý sự cố Windows Update và cập nhật hệ điều hành Windows

**Từ khóa:** cập nhật Windows, Windows Update, lỗi update, cập nhật thất bại, disk space, troubleshooter, restart, hoàn tác, lỗi cập nhật, giải phóng ổ đĩa, 0x80070002, 0x80240034, Windows 10, Windows 11, Endpoint Management.

## Triệu chứng / Dấu hiệu nhận biết
- Quá trình Windows Update báo lỗi với các mã phổ biến như 0x80070002, 0x80070070, 0x80240034 hoặc tải mãi ở mức 0% / 100%.
- Máy tính thông báo dung lượng ổ đĩa C không đủ (low disk space) để tải hoặc giải nén bản vá cập nhật.
- Máy tính bị treo ở màn hình "Working on updates" hoặc tự động hoàn tác (undoing changes) sau khi khởi động lại.

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra dung lượng ổ đĩa C (Disk space):** Bản cập nhật Windows thường yêu cầu tối thiểu 10GB - 20GB dung lượng trống. Nhấp chuột phải vào ổ đĩa C -> chọn *Properties* hoặc vào *Settings -> System -> Storage* để dọn dẹp các tệp tạm thời (Temporary files).
2. **Chạy trình sửa lỗi Windows Update Troubleshooter:** Vào *Settings -> Update & Security (hoặc System) -> Troubleshoot -> Other troubleshooters -> Windows Update* và chọn *Run*. Chờ hệ thống tự động quét và sửa các lỗi service.
3. **Khởi động lại máy tính (Restart):** Nhiều bản cập nhật yêu cầu khởi động lại máy để áp dụng các gói trước đó. Chọn *Start -> Restart* (không chọn Shutdown).
4. **Kiểm tra ngày giờ hệ thống:** Đảm bảo ngày giờ và múi giờ trên máy tính trùng khớp với thời gian thực tế để không bị lỗi xác thực chứng chỉ máy chủ cập nhật.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Máy tính công ty được quản lý tập trung qua máy chủ WSUS / Endpoint Management, người dùng không bỏ qua policy cập nhật của công ty.
- Bản cập nhật liên tục báo lỗi sau khi đã chạy Troubleshooter và giải phóng ổ đĩa.
- Lỗi vòng lặp khởi động (boot loop) hoặc màn hình xanh sau khi cài đặt bản vá.
- Cần quyền Quản trị viên (Administrator) để can thiệp xóa thư mục SoftwareDistribution hoặc đặt lại service cập nhật (Update service).
