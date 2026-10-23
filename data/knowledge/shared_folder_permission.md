# Khắc phục lỗi Access Denied và phân quyền ghi thư mục chia sẻ trên NAS

**Từ khóa:** phân quyền thư mục, quyền truy cập, shared folder, cấp quyền folder, permission denied, không mở được thư mục mạng, ổ đĩa chia sẻ, Access Denied, quyền ghi, NTFS, NAS, ổ đĩa mạng dùng chung, 0x80070005, folder_access, shared_folder_permission.

## Triệu chứng / Dấu hiệu nhận biết
- Thư mục dùng chung trên mạng báo lỗi Access Denied không có quyền ghi dữ liệu khi sao chép, tạo mới hoặc chỉnh sửa tệp tin.
- Màn hình xuất hiện mã lỗi Windows `0x80070005` (Access Denied) hoặc thông báo 'Destination Folder Access Denied - You need permission to perform this action'.
- Người dùng có thể mở và đọc nội dung tệp tin trong thư mục dùng chung trên NAS (`\\nas\shared`) nhưng không thể lưu (Save) thay đổi hoặc xóa tệp.
- Ổ đĩa mạng đã ánh xạ (ví dụ ổ `Z:`) hiển thị dấu gạch đỏ hoặc không cho phép ghi dữ liệu.

## Các bước người dùng tự khắc phục nhanh (Self-service)
1. **Kiểm tra trạng thái tệp tin bị khóa (File in use / Read-only):**
   - Kiểm tra xem tệp tin có đang được đồng nghiệp khác mở trên mạng hay không (chế độ bảo vệ khóa file chia sẻ).
   - Nhấp chuột phải vào tệp tin -> Chọn **Properties** -> Tại mục Attributes, kiểm tra xem ô **Read-only** có bị đánh dấu chọn hay không; nếu có hãy bỏ chọn và nhấn OK.
2. **Kiểm tra đường dẫn và trạng thái kết nối ổ đĩa mạng NAS:**
   - Mở File Explorer -> Kiểm tra ổ đĩa mạng `\\nas\shared` có đang kết nối ổn định không.
   - Thử lưu tệp vào thư mục tạm trên máy tính cục bộ (Desktop / Documents) để tránh mất dữ liệu đang làm dở.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- **Cấp quyền ghi / phân quyền NTFS trên máy chủ NAS:** Người dùng chỉ có quyền đọc (Read) nhưng công việc yêu cầu quyền ghi (Write/Modify) -> Cần gửi ticket đến IT kèm phê duyệt của Quản lý thư mục để IT Quản trị tiến hành cấp quyền NTFS trên hệ thống lưu trữ mạng NAS.
- **Xử lý xung đột phân quyền nhóm (Security Group ACL):** Tài khoản người dùng mới chuyển phòng ban hoặc thay đổi vị trí công tác cần được IT thêm vào nhóm quyền tương ứng trên Active Directory / NAS.
- **Hết hạn ngạch lưu trữ (Storage Quota):** Nếu thư mục chia sẻ trên NAS bị giới hạn dung lượng và đạt ngưỡng 100%, IT Quản trị hạ tầng lưu trữ sẽ kiểm tra và nâng hạn mức dung lượng cho phòng ban.
