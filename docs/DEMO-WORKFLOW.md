# Kiểm tra quy trình trình diễn

Dùng tài khoản và dữ liệu thử riêng; không thay đổi ticket đang xử lý thực tế.

1. Nhân viên tạo ticket, chọn đúng danh mục và ưu tiên. Ghi lại mã ticket.
2. Admin lọc “Chưa phân công · đang mở”, giao ticket cho agent.
3. Agent lọc “Giao cho tôi · đang mở”, chuyển Mới → Đang xử lý.
4. Agent thêm phản hồi, chuyển sang Chờ người gửi.
5. Nhân viên phản hồi; kiểm tra ticket trở lại Đang xử lý.
6. Agent giải quyết; nhân viên xác nhận đóng hoặc mở lại nếu chưa khắc phục.
7. Xem lịch sử ticket và Báo cáo. Đối chiếu người thao tác, trạng thái và số liệu.
8. Đăng nhập nhân viên khác: không được đọc/sửa ticket này bằng giao diện hay API.

Bộ lọc SLA chỉ tính ticket chưa giải quyết/chưa đóng. Sắp quá hạn = hạn từ hiện tại đến 2 giờ tiếp theo. Các bộ lọc kết hợp với trạng thái, danh mục, từ khóa và ngày đang chọn. Tải lại hàng đợi để cập nhật thời gian.

Không tạo dữ liệu quá hạn bằng cách sửa trực tiếp cơ sở dữ liệu thật. Có thể chuẩn bị dữ liệu quá hạn trong môi trường thử riêng.

Ghi nhận kết quả từng bước (đạt/chưa đạt, ảnh minh chứng, lỗi) trong báo cáo khóa luận. Hướng dẫn này không phải kết quả kiểm thử đã thực hiện.
