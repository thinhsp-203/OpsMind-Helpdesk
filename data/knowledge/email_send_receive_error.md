# Khắc phục lỗi gửi và nhận email trên Microsoft Outlook (2016, 2019, 2021, 365)

**Từ khóa:** gửi email, nhận email, gửi nhận thư, lỗi gửi mail, lỗi nhận mail, Outlook 2016, Outlook 2019, Outlook 2021, Office 365, 0x800CCC0E, 0x80042109, kết nối máy chủ, cấu hình, Work Offline, máy chủ mail.

## Triệu chứng / Dấu hiệu nhận biết
- Nhấn nút *Send/Receive All Folders* trong Outlook nhưng thanh tiến trình báo lỗi, xuất hiện mã lỗi 0x800CCC0E, 0x80042108 hoặc 0x80042109.
- Email gửi đi bị kẹt trong thư mục *Outbox*, người nhận không nhận được thư mới hoặc hộp thư không tải thư đến.
- Góc dưới bên phải của cửa sổ Outlook hiển thị trạng thái "Disconnected" (Đã ngắt kết nối) hoặc "Trying to connect..." (Đang cố kết nối...).

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra kết nối Internet:** Mở trình duyệt web và truy cập một trang web bất kỳ hoặc trang Webmail của công ty để đảm bảo đường truyền Internet vẫn đang hoạt động ổn định.
2. **Kiểm tra trạng thái Work Offline:** Trong giao diện Outlook, chuyển sang thẻ *Send / Receive*. Nếu nút *Work Offline* đang có màu xám/xanh kích hoạt, hãy nhấp vào để chuyển về chế độ kết nối trực tuyến bình thường.
3. **Kiểm tra dung lượng tệp đính kèm:** Đảm bảo thư gửi đi trong Outbox không chứa tệp đính kèm vượt quá giới hạn cho phép của hệ thống mail công ty (thường tối đa 20MB - 25MB). Nếu vượt quá, xóa thư trong Outbox và gửi qua đường dẫn lưu trữ đám mây.
4. **Khởi động lại Outlook và máy tính:** Tắt hoàn toàn ứng dụng Outlook, chờ 10 giây rồi mở lại để nạp lại phiên kết nối mạng.

> **Lưu ý an toàn quan trọng (Security Policy):** Người dùng tuyệt đối không tắt phần mềm bảo mật (do not disable endpoint antivirus) trên máy tính để thử gửi mail. Mọi rủi ro an toàn mạng phải được tuân thủ nghiêm ngặt theo chính sách CNTT.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Lỗi kết nối máy chủ mail xảy ra đồng loạt với nhiều nhân sự trong cùng phòng ban (nghi ngờ sự cố máy chủ Exchange / Mail Server).
- Cần kỹ thuật viên IT kiểm tra lại thông số cấu hình cổng kết nối SSL/TLS (IMAP/SMTP/Exchange) và cấu hình tài khoản người dùng trên hệ thống.
- Hộp thư bị khóa gửi do nghi ngờ gửi spam hoặc bị chặn bởi bộ lọc tường lửa công ty.
