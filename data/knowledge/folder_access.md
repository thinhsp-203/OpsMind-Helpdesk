# Quy trình cấp quyền và truy cập thư mục dùng chung trên mạng (NAS)

**Từ khóa:** folder, shared folder, thư mục mạng, thư mục chia sẻ, network folder, phân quyền, access denied, ổ đĩa mạng, NAS, quyền truy cập, quyền cần, đường dẫn, quản lý phê duyệt, tạo ticket, read/write, VPN, corporate account, owner approval.

## Triệu chứng / Dấu hiệu nhận biết
- Tôi không thể truy cập vào thư mục chia sẻ nội bộ của phòng ban trên hệ thống lưu trữ mạng NAS (`\\nas\shared` hoặc `\\fileserver\shared`).
- Nhận thông báo lỗi 'Windows cannot access... Access is denied' khi nhấp vào thư mục dùng chung.
- Cần xin quyền truy cập mới hoặc mở rộng quyền chỉnh sửa (read/write) để phục vụ dự án công việc mới.
- Khi kết nối qua VPN (đối với bộ phận Lễ tân / IT), không nhìn thấy hoặc không mở được thư mục mạng đã gán ổ đĩa (mapped network drive).

## Các bước người dùng tự khắc phục nhanh (Self-service)
1. **Kiểm tra kết nối mạng và tài khoản:**
   - Đảm bảo máy tính đang cắm mạng dây LAN hoặc kết nối Wi-Fi nội bộ công ty (hoặc đã kết nối VPN hợp lệ nếu là nhân viên Lễ tân / IT làm việc từ xa).
   - Đảm bảo đang đăng nhập bằng tài khoản công ty (corporate account) được cấp, không dùng tài khoản cục bộ cá nhân (Local User).
2. **Kiểm tra và ghi nhận đường dẫn thư mục:**
   - Bấm tổ hợp phím **Windows + R** -> Nhập đường dẫn thư mục dùng chung (ví dụ: `\\nas\shared` hoặc `\\fileserver\data`).
   - Ghi lại chính xác tên thư mục con cần truy cập và chụp ảnh màn hình thông báo lỗi (lưu ý không chụp các dữ liệu tệp nhạy cảm).
3. **Thử ánh xạ lại ổ đĩa mạng (Map Network Drive):**
   - Mở File Explorer -> Nhấp chuột phải vào This PC -> Chọn **Map network drive...** -> Nhập đường dẫn thư mục và chọn 'Reconnect at sign-in'.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- **Yêu cầu cấp quyền truy cập mới (Folder Permission Request):**
  - Người dùng tạo ticket yêu cầu cấp quyền gửi cho IT Helpdesk.
  - Ticket phải cung cấp đầy đủ:
    1. Đường dẫn thư mục chia sẻ cụ thể trên NAS (ví dụ: `\\nas\shared\KeToan`).
    2. Mức quyền cần thiết: Chỉ đọc (Read-only) hay Đọc & Ghi (Read/Write).
    3. Xác nhận phê duyệt từ Quản lý phòng ban hoặc chủ sở hữu dữ liệu (owner approval / quản lý phê duyệt).
- **Sự cố máy chủ NAS / File Server:** Nếu toàn bộ phòng ban không thể truy cập ổ đĩa mạng chung, IT sẽ kiểm tra dịch vụ lưu trữ mạng NAS và hạ tầng chia sẻ file.
