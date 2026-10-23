# Hướng dẫn xử lý màn hình yêu cầu mã khóa khôi phục BitLocker Recovery Key

**Từ khóa:** BitLocker, recovery key, khóa bitlocker, mã khôi phục, 48 chữ số, Recovery Key ID, mã hóa ổ đĩa, TPM, BIOS, màn hình xanh bitlocker.

## Triệu chứng / Dấu hiệu nhận biết
- Khi bật nguồn máy tính hoặc laptop công ty, máy không vào thẳng Windows mà dừng lại ở màn hình xanh BitLocker.
- Màn hình hiển thị tiêu đề "BitLocker" và yêu cầu: "Enter the recovery key for this drive".
- Có hiển thị dãy ký tự *Recovery Key ID* (ví dụ: dạng 8 ký tự đầu như `3A4B5C6D...`) và yêu cầu nhập chuỗi gồm 48 chữ số.

## Các bước tự khắc phục nhanh (Self-service)
1. **Ghi lại Recovery Key ID:** Chụp ảnh màn hình hoặc ghi lại chính xác dòng *Recovery Key ID* (gồm các nhóm ký tự) hiển thị trên màn hình.
2. **Kiểm tra tài khoản Microsoft công ty:** Nếu máy tính đăng nhập bằng tài khoản Microsoft 365 cơ quan, dùng điện thoại truy cập trang web `https://aka.ms/myrecoverykey`, đăng nhập tài khoản công ty để tìm mã khôi phục tương ứng với Key ID.
3. **Nhập chính xác 48 chữ số:** Dùng bàn phím số phía trên hoặc bàn phím số bên phải để nhập chuỗi 48 số (chỉ có số, không có chữ). Sau khi nhập đủ, nhấn Enter để mở khóa vào Windows.
4. **Kiểm tra các thiết bị ngoại vi:** Nếu máy vừa cắm thêm ổ cứng ngoài lạ hoặc thay đổi thứ tự boot trong BIOS, hãy rút ra và khởi động lại.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Người dùng không tìm thấy mã khóa khôi phục trong tài khoản cá nhân.
- Sau khi nhập đúng 48 số nhưng máy báo lỗi và tiếp tục quay lại màn hình BitLocker ở các lần khởi động tiếp theo (lỗi chip bảo mật TPM trên bo mạch chủ).
- Cần quản trị viên IT truy cập cổng quản trị Active Directory / Azure AD để tra cứu mã BitLocker Recovery Key chính chủ cho thiết bị.
