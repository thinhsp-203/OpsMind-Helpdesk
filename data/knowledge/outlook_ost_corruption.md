# Sửa lỗi tệp dữ liệu Outlook .OST / .PST và khắc phục profile hỏng

**Từ khóa:** tệp OST, file OST hỏng, lỗi dữ liệu Outlook, sửa file pst, scanpst, corrupt profile, tạo profile mới, Outlook không mở được, Webmail, prerequisite & synchronization safety check, user@company.com.ost.old.

## Triệu chứng / Dấu hiệu nhận biết
- Mở Outlook xuất hiện thông báo lỗi: "Cannot start Microsoft Outlook. Cannot open the Outlook window. The set of folders cannot be opened."
- Outlook báo tệp dữ liệu `.ost` hoặc `.pst` bị lỗi và yêu cầu chạy công cụ quét sửa chữa Scanpst.exe.
- Outlook thường xuyên bị treo đơ khi đang tải hoặc gửi email, một số thư mục hiển thị sai số lượng thư chưa đọc.

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra an toàn dữ liệu trên Webmail (Prerequisite & synchronization safety check):** Trước khi thao tác sửa tệp cục bộ trên máy, hãy mở trình duyệt web đăng nhập vào Webmail công ty để xác nhận toàn bộ thư từ quan trọng vẫn còn nguyên vẹn trên máy chủ.
2. **Khởi động Outlook ở chế độ Safe Mode:** Nhấn tổ hợp phím `Windows + R`, gõ `outlook.exe /safe` rồi nhấn Enter. Nếu Outlook mở được bình thường, nguyên nhân do add-in xung đột.
3. **Đổi tên tệp OST bị hỏng để hệ thống tự tạo lại:**
   - Tắt hoàn toàn Outlook (kiểm tra trong Task Manager không còn tiến trình Outlook).
   - Nhấn `Windows + R`, dán đường dẫn `%localappdata%\Microsoft\Outlook` rồi nhấn Enter.
   - Tìm file dữ liệu có đuôi `.ost` tương ứng với tài khoản mail của bạn, đổi tên tệp (ví dụ từ file hiện tại thành `user@company.com.ost.old`).
   - Mở lại Outlook, hệ thống sẽ tự động kết nối máy chủ Exchange và tạo mới tệp `.ost` sạch sẽ để tải dữ liệu về.
4. **Sử dụng công cụ Scanpst.exe:** Đối với file `.pst` lưu trữ cục bộ, mở công cụ `SCANPST.EXE` trong thư mục cài đặt Office (`C:\Program Files\Microsoft Office\root\Office16`) để quét và khắc phục các lỗi hỏng tệp dữ liệu.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Tệp dữ liệu dung lượng quá lớn (trên 45GB - 50GB) bị phân mảnh nặng, Scanpst không thể khắc phục được.
- Đã đổi tên tạo lại tệp OST nhưng Outlook vẫn báo lỗi không thể tạo profile mới hoặc lỗi xác thực máy chủ.
- Cần kỹ thuật viên IT hỗ trợ khôi phục lại dữ liệu lịch sử email từ các bản sao lưu dự phòng máy chủ.
