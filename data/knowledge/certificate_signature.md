# Hướng dẫn xử lý chứng thư số, chữ ký số văn bản và đồng bộ ngày giờ máy tính

**Từ khóa:** chứng thư, certificate, chữ ký số, token, gia hạn chứng thư, ký số bị lỗi, ngày giờ, đồng hồ máy tính, USB token, chữ ký điện tử, phần mềm ký số, liên hệ IT/Security.

## Triệu chứng / Dấu hiệu nhận biết
- Khi ký số tài liệu PDF, hóa đơn điện tử hoặc văn bản hành chính xuất hiện thông báo lỗi: "Chứng thư số không hợp lệ", "Chứng thư đã hết hạn" hoặc "Lỗi thời gian ký số (Invalid Signing Time)".
- Trình duyệt web hoặc phần mềm ký số chuyên dụng không nhận diện được chứng thư số khi cắm USB Token.
- Đồng hồ ngày giờ hiển thị ở góc màn hình máy tính bị chạy chậm, sai ngày tháng năm do pin CMOS trên máy tính bị yếu.

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra đồng hồ ngày giờ máy tính:** Nhấp chuột vào phần đồng hồ ở góc phải thanh Taskbar, kiểm tra xem ngày, tháng, năm và giờ hiện tại có đúng với giờ thực tế hay không. Nếu bị lệch, vào *Settings -> Time & Language -> Date & Time*, bật *Set time automatically* và bấm nút *Sync now* để đồng bộ lại giờ.
2. **Kiểm tra kết nối và đèn USB Token:** Rút thiết bị USB Token ra cắm lại vào cổng USB khác trên máy tính, đảm bảo đèn tín hiệu trên thân Token sáng ổn định.
3. **Mở phần mềm quản lý chứng thư (Token Manager):** Mở phần mềm quản lý chữ ký số (ví dụ: VNPT-CA, Viettel-CA, BKAV-CA) trên máy để kiểm tra xem hệ thống đã nhận diện được chứng thư số hay chưa và kiểm tra hạn sử dụng của chứng thư.
4. **Không chia sẻ mã PIN:** Người dùng tự bảo quản mã PIN của USB token, tuyệt đối không chia sẻ mã PIN cho người khác.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Chứng thư số của cá nhân hoặc đơn vị đã thực sự hết hạn sử dụng ghi trên hệ thống, cần liên hệ IT/Security để làm thủ tục gia hạn với nhà cung cấp chứng thực số CA.
- Máy tính bị hết pin CMOS, cứ mỗi lần tắt máy bật lại là giờ lại bị nhảy về nhiều năm trước (cần IT tháo vỏ máy thay pin CMOS mới).
- Phần mềm ký số bị lỗi phân quyền hệ điều hành hoặc lỗi xung đột Java, cần kỹ thuật viên IT hỗ trợ cài đặt cấu hình lại.
