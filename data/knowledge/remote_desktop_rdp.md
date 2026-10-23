# Hướng dẫn xử lý sự cố kết nối Remote Desktop (RDP / mstsc) mạng nội bộ

**Từ khóa:** Remote Desktop, RDP, mstsc, kết nối máy chủ, máy tính từ xa, lỗi NLA, cổng 3389, điều khiển từ xa, mạng nội bộ, xác thực từ xa.

## Triệu chứng / Dấu hiệu nhận biết
- Mở ứng dụng Remote Desktop Connection (`mstsc`) gõ tên máy hoặc IP nhưng báo lỗi: "Remote Desktop can't connect to the remote computer for one of these reasons".
- Xuất hiện lỗi xác thực tài khoản cấp độ mạng NLA: "An authentication error has occurred. The function requested is not supported" hoặc "The remote computer requires Network Level Authentication".
- Kết nối được vài giây rồi tự động bị ngắt kết nối hoặc màn hình điều khiển từ xa bị đen kịt.

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra kết nối mạng cùng lớp mạng:** Đảm bảo máy tính của bạn và máy tính/máy chủ đích đang cùng kết nối trong mạng nội bộ công ty (hoặc đã kết nối VPN được cấp phép đối với Lễ tân/IT).
2. **Kiểm tra chính xác địa chỉ IP và tài khoản:**
   - Nhập đúng địa chỉ IP nội bộ của máy đích (ví dụ: `192.168.1.50`).
   - Khi đăng nhập, nhập đúng tên miền công ty trước tên tài khoản (ví dụ: `COMPANY\username` hoặc `username@company.com`) cùng mật khẩu hiện tại.
3. **Kiểm tra máy tính đích có đang bật nguồn không:** Đảm bảo máy tính ở văn phòng đang bật nguồn, cắm dây mạng và không bị rơi vào trạng thái ngủ sâu (Sleep / Hibernate).
4. **Thử ping kiểm tra thông mạng:** Mở `cmd`, gõ `ping <địa chỉ IP máy đích>` để xác nhận đường truyền hai máy thông suốt.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Máy tính đích chưa được bật tính năng cho phép điều khiển từ xa (Enable Remote Desktop) trong System Properties.
- Tường lửa Windows Firewall của máy đích hoặc tường lửa mạng đang chặn cổng dịch vụ TCP 3389.
- Cần quản trị viên IT cấp quyền tài khoản vào nhóm *Remote Desktop Users* trên máy chủ đích.
