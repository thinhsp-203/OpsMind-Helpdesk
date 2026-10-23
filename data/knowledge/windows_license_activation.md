# Hướng dẫn kích hoạt bản quyền Windows và Microsoft Office qua máy chủ KMS nội bộ

**Từ khóa:** bản quyền Windows, kích hoạt Windows, license key, KMS, Activate Windows, Office 2016, Office 2019, Office 2021, Office 365, bản quyền hết hạn, slmgr, kích hoạt bản quyền.

## Triệu chứng / Dấu hiệu nhận biết
- Góc phải phía dưới màn hình Windows xuất hiện dòng chữ mờ: "Activate Windows - Go to Settings to activate Windows".
- Khi mở các ứng dụng văn phòng Word, Excel, Outlook xuất hiện thanh thông báo màu vàng hoặc đỏ ở phía trên: "Product Activation Failed" hoặc "Your license will expire soon".
- Trong cửa sổ *Settings -> System -> Activation* báo trạng thái Windows chưa được kích hoạt bản quyền hợp lệ hoặc không kết nối được máy chủ cấp khóa bản quyền.

## Các bước tự khắc phục nhanh (Self-service)
1. **Kết nối vào mạng nội bộ công ty:** Bản quyền Windows và Office của công ty được quản lý và kích hoạt tự động thông qua máy chủ KMS (Key Management Service) nội bộ. Hãy cắm dây mạng LAN hoặc kết nối Wi-Fi nội bộ tại văn phòng công ty.
2. **Giữ kết nối mạng và khởi động lại máy:** Khi máy tính kết nối mạng nội bộ công ty, hệ thống sẽ tự động gửi gói tin xác thực đến máy chủ KMS để gia hạn bản quyền (thời hạn mỗi chu kỳ gia hạn là 180 ngày).
3. **Kiểm tra ngày giờ hệ thống:** Đảm bảo ngày, giờ và múi giờ trên máy tính hoàn toàn chuẩn xác. Nếu sai lệch giờ quá 5 phút so với máy chủ miền Active Directory, việc kích hoạt bản quyền sẽ bị từ chối.
4. **Kiểm tra trạng thái kích hoạt trong Settings:** Vào *Settings -> System -> Activation*, chọn nút *Troubleshoot* nếu có để hệ thống kiểm tra lại khóa bản quyền.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Máy tính đã kết nối mạng nội bộ nhiều ngày nhưng vẫn không tự kích hoạt được bản quyền.
- Máy tính của nhân sự làm việc từ xa dài ngày không thể đến văn phòng để kết nối mạng nội bộ.
- Cần kỹ thuật viên IT cấp phát khóa bản quyền riêng (MAK / Digital License) hoặc xử lý lệnh kích hoạt nâng cao qua dòng lệnh máy chủ KMS.
