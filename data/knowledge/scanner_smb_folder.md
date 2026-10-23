# Hướng dẫn xử lý lỗi scan từ máy photocopy về thư mục SMB trên máy tính và NAS

**Từ khóa:** máy scan, máy quét, scan to folder, quét tài liệu, giao thức SMB, máy photocopy, scan về máy tính, scan về NAS, SMBv2, SMBv3, chia sẻ thư mục, phân quyền mạng.

## Triệu chứng / Dấu hiệu nhận biết
- Thao tác quét tài liệu từ màn hình cảm ứng máy in photocopy về thư mục máy tính cá nhân nhưng máy photocopy báo lỗi: "Transmission failed", "Cannot connect to server" hoặc "Authentication error".
- Tài liệu quét không xuất hiện trong thư mục `Scan` chia sẻ trên máy tính hoặc trên ổ cứng mạng NAS.
- Lỗi xuất hiện sau khi người dùng vừa đổi mật khẩu tài khoản máy tính hoặc sau khi Windows cập nhật bản vá bảo mật.

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra thông tin tài khoản đăng nhập máy photocopy:** Khi đổi mật khẩu đăng nhập Windows của tài khoản cá nhân, mật khẩu lưu trên máy photocopy để truy cập thư mục scan cũng phải được cập nhật lại tương ứng. Nhờ đồng nghiệp kiểm tra hoặc nhập lại mật khẩu mới trên danh bạ (Address Book) của máy photocopy.
2. **Kiểm tra quyền chia sẻ của thư mục Scan trên máy tính:**
   - Nhấp chuột phải vào thư mục `Scan` trên máy tính -> chọn *Properties*.
   - Chuyển sang thẻ *Sharing* -> kiểm tra thư mục đã được *Shared* hay chưa. Bấm *Advanced Sharing -> Permissions*, đảm bảo tài khoản người dùng có đầy đủ quyền *Read* và *Change*.
3. **Kiểm tra địa chỉ IP của máy tính cá nhân:** Nếu cấu hình scan sử dụng địa chỉ IP của máy tính, hãy kiểm tra xem IP của máy tính mình có bị thay đổi hay không (nhấn `Windows + R`, gõ `cmd`, gõ `ipconfig` để kiểm tra IPv4).
4. **Kiểm tra tường lửa Windows Firewall:** Đảm bảo tường lửa không chặn giao thức chia sẻ file và máy in (File and Printer Sharing).

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Toàn bộ nhân viên trong văn phòng đều không thể scan tài liệu về máy tính hoặc scan về ổ đĩa mạng NAS.
- Máy photocopy đời cũ chỉ hỗ trợ giao thức SMBv1 (đã bị Windows 10/11 tắt mặc định vì lý do an ninh mạng), cần IT thẩm định và cấu hình giải pháp chuyển tiếp an toàn.
- Cần quản trị viên IT cấp tài khoản chuyên dụng dùng riêng cho chức năng quét tài liệu mạng trên máy chủ NAS.
