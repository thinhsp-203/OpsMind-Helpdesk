# Xử lý sự cố phần mềm kế toán MISA, FAST và hệ thống ERP nội bộ

**Từ khóa:** ERP, kế toán, phần mềm nghiệp vụ, MISA, FAST, không đăng nhập được ERP, lỗi kết nối database, phần mềm kế toán, mất quyền module, support ERP, cơ sở dữ liệu.

## Triệu chứng / Dấu hiệu nhận biết
- Mở phần mềm kế toán MISA, FAST hoặc hệ thống ERP nội bộ xuất hiện thông báo: "Không kết nối được với máy chủ dữ liệu (Database Server)" hoặc "Mất kết nối máy chủ SQL".
- Đăng nhập vào phần mềm thành công nhưng một số phân hệ/module kế toán (Kho, Bán hàng, Tài sản, Báo cáo tài chính) bị biến mất hoặc báo không có quyền truy cập sau khi thay đổi vị trí công việc.
- Quá trình nạp chứng từ kế toán hoặc xuất báo cáo tài chính bị treo đơ ở mức 0% hoặc tự động văng ứng dụng.

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra mạng dây LAN nội bộ:** Các phần mềm kế toán MISA/FAST và máy chủ dữ liệu SQL Server yêu cầu kết nối mạng nội bộ tốc độ cao và ổn định. Hãy ưu tiên cắm mạng dây LAN thay vì dùng Wi-Fi.
2. **Dừng ngay các thao tác ghi dữ liệu nếu báo lỗi đồng bộ:** Nếu phần mềm thông báo lỗi khi đang lưu chứng từ, người dùng dừng thao tác, không cố ghi đè nhiều lần và tuyệt đối không tự can thiệp sửa đổi cấu trúc cơ sở dữ liệu (Database) để tránh làm sai lệch số liệu kế toán.
3. **Khởi động lại ứng dụng và máy tính:** Tắt hoàn toàn phần mềm kế toán (kiểm tra trong Task Manager để đóng các tiến trình ngầm của MISA/FAST), sau đó mở lại phần mềm để tạo lại phiên kết nối mới đến máy chủ.
4. **Kiểm tra tài khoản và mật khẩu:** Đảm bảo đăng nhập đúng tên tài khoản phân quyền và mật khẩu hợp lệ của phần mềm kế toán.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Dịch vụ máy chủ cơ sở dữ liệu (SQL Server Database Service) trên máy chủ trung tâm bị treo hoặc mất nguồn điện.
- Nhân sự mới chuyển phòng ban hoặc tiếp nhận công việc mới cần cấp quyền truy cập phân hệ ERP/kế toán tương ứng (cần có xác nhận phê duyệt từ Kế toán trưởng).
- Cần đội ngũ kỹ thuật IT và chuyên viên hỗ trợ phần mềm (Support ERP) can thiệp khôi phục dữ liệu từ bản sao lưu (Backup) gần nhất.
