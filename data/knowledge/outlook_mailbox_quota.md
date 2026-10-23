# Hướng dẫn xử lý hộp thư Outlook bị đầy dung lượng (Mailbox Quota Exceeded)

**Từ khóa:** hộp thư đầy, đầy hòm thư, dung lượng email, quá hạn ngạch, mailbox quota, cleanup, lưu trữ email, Archive, hạn ngạch, dung lượng hộp thư, đầy mailbox, xóa thư rác, Outlook 2016, Outlook 2019, Office 365.

## Triệu chứng / Dấu hiệu nhận biết
- Nhận được email cảnh báo từ hệ thống tự động: "Your mailbox is almost full" hoặc "Mailbox quota exceeded".
- Không thể gửi được email mới, thư gửi đi bị bật ngược lại với thông báo lỗi quá hạn ngạch dung lượng.
- Thanh chỉ số dung lượng trong *File -> Info* của Outlook chuyển sang màu vàng hoặc đỏ cảnh báo đã dùng hết dung lượng được cấp.

## Các bước tự khắc phục nhanh (Self-service)
1. **Dọn sạch thư mục Thùng rác (Deleted Items):** Nhấp chuột phải vào thư mục *Deleted Items* -> chọn *Empty Folder* để giải phóng dung lượng của các thư đã xóa tạm thời.
2. **Dọn sạch thư mục Thư rác (Junk Email):** Nhấp chuột phải vào thư mục *Junk Email* -> chọn *Empty Folder*.
3. **Sắp xếp và xóa email có tệp đính kèm lớn:** Vào hộp thư đến (Inbox), nhấp vào bộ lọc sắp xếp chọn *Sort by Size* (Sắp xếp theo dung lượng từ lớn đến nhỏ). Tìm các email có file đính kèm video, ảnh, slide lớn không còn cần thiết để lưu trữ ra ổ cứng ngoài rồi xóa bỏ.
4. **Sử dụng tính năng lưu trữ cục bộ (Archive PST):** Sử dụng tính năng xuất email cũ sang file dữ liệu `.pst` trên máy tính để lưu trữ lâu dài mà không chiếm dung lượng trên máy chủ mail.

> **Quy định bảo toàn dữ liệu:** Người dùng chỉ thực hiện dọn dẹp các thư rác và sao lưu định kỳ, không thực hiện purge (không xóa vĩnh viễn cưỡng bức hàng loạt các thư mục hệ thống trên server khi chưa có bản lưu trữ an toàn).

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Đã dọn dẹp thư mục rác nhưng dung lượng hiển thị trên máy chủ vẫn không giảm sau 2 giờ.
- Công việc phát sinh dữ liệu lớn thường xuyên và cần làm đề xuất gửi IT nâng hạn ngạch (tăng quota dung lượng hộp thư) theo phê duyệt của Trưởng bộ phận.
- Cần kỹ thuật viên IT hướng dẫn cấu hình chính sách tự động lưu trữ Online Archive trên hệ thống Office 365.
