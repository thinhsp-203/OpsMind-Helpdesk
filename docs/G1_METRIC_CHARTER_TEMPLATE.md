# Mẫu chốt sản phẩm và metric G1

> **Trạng thái: CHƯA KÝ / CHƯA ĐƯỢC GVHD PHÊ DUYỆT.** Đây là bản nháp để nhóm thảo luận. Không dùng làm minh chứng đã thông qua cho đến khi điền đầy đủ, thống nhất và ký trước mốc thời gian theo quy định.

## 1. Thông tin xác nhận

| Trường | Nội dung cần điền |
|---|---|
| Tên đề tài / mã lớp | |
| Nhóm / thành viên | |
| Giảng viên hướng dẫn | |
| Ngày thống nhất | |
| Mốc 50% thời gian của học phần | |
| Link repository và phiên bản chốt | |

## 2. Sản phẩm dự kiến

- Web app Helpdesk có đăng nhập và ba vai trò demo.
- Luồng ticket: tạo, phân công, trao đổi, chuyển trạng thái, lưu audit và tính SLA.
- Trợ lý truy xuất tài liệu Markdown, dẫn nguồn và từ chối khi không có tài liệu phù hợp.
- Tài liệu SRS/SDD, kiểm thử tự động, pipeline CI và báo cáo thực nghiệm.

Phạm vi phải được GVHD chấp thuận; hạ tầng hiện tại chưa có SSO, attachment, LLM sinh câu trả lời, HA hoặc triển khai công khai.

## 3. Metric đề xuất cần chốt

| Metric | Giá trị đề xuất trong kế hoạch | Định nghĩa/điều kiện đo cần thống nhất |
|---|---:|---|
| Luồng chức năng | Toàn bộ AC mức ưu tiên cao pass | Danh sách use case, môi trường và tiêu chí pass |
| Context retrieval | Hit@3 ≥ 0.80 trên tập 30 câu hỏi được duyệt | Ground truth do ai xác nhận; xử lý câu ngoài phạm vi |
| Latency | p95 ≤ 3 giây | Môi trường, kích thước KB, concurrency và điểm bắt đầu/kết thúc |
| Unit test coverage | ≥ 70% module lõi | Module nằm trong phạm vi, lệnh và ngưỡng coverage |
| Usability | SUS mục tiêu ≥ 80 | Cỡ mẫu, đối tượng, nhiệm vụ và cách tính |
| Tải / availability | Chưa xác nhận | Có thể loại khỏi cam kết nếu không có môi trường đo phù hợp |

**Đơn vị đo thực tế cần điền sau khi thử nghiệm; không điền mục tiêu thay cho kết quả.**

## 4. Ký xác nhận

| Đại diện nhóm | Giảng viên hướng dẫn |
|---|---|
| Họ tên / chữ ký / ngày: | Họ tên / chữ ký / ngày: |

## 5. Lịch sử thay đổi

| Phiên bản | Ngày | Nội dung | Người thống nhất |
|---|---|---|---|
| 0.1 | 05/10/2026 | Bản nháp đề xuất, chưa phê duyệt | |
