# Giao diện Trợ lý — 26/10/2026

Baseline: `af1bda34df21f398bd217614e950f4864f958806`, branch `fix/aud-01-frontend-boot`.
Tham chiếu trực quan: https://demo.naviwebsite.vn/ai-workplace/assistant?q=m%C3%A0n%20h%C3%ACnh%20xanh

## UI-01 — Bố cục Trợ lý

Khung chat bên trái, thông tin hỗ trợ bên phải trên desktop. Vùng hội thoại cuộn độc lập, composer ở cuối khung, nguồn tài liệu thu gọn/mở được. CSS riêng `app/static/assistant.css`; giữ ID của các control cũ. Các view khác vẫn dùng layout hiện hành.

## UI-02 — Hội thoại và phím tắt

Thêm lượt hỏi thay vì ghi đè lượt trước. Enter gửi, Shift+Enter xuống dòng; không gửi trong lúc IME đang ghép chữ hoặc đang đợi phản hồi. Nút phiên mới và mở lịch sử được bảo vệ khi request đang chạy. Phản hồi từ token đăng nhập cũ không được hiển thị trong phiên mới. Khi request lỗi, giữ câu hỏi và khôi phục nội dung ô nhập để người dùng thử lại.

## UI-03 — Các khối thông tin

- Kho tri thức: số tài liệu từ `/knowledge?status=published`.
- Lỗ hổng tri thức: trạng thái có/không có nguồn của câu hỏi mới nhất; chưa có chức năng lưu/gom gap hoặc giao biên soạn, không tuyên bố đã gửi yêu cầu.
- Việc cần làm: ticket đang mở theo quyền backend. Staff xem ticket phụ trách hoặc quá hạn; user xem ticket của mình.
- Hoạt động: nhật ký thực của tối đa 3 ticket cập nhật gần nhất được phép xem, hiển thị tối đa 5 sự kiện. Không phải toàn bộ timeline công ty.
- Chặn response context cũ ghi đè request mới; lỗi một nguồn không xóa dữ liệu của nguồn khác.

## UI-04 — Responsive, song ngữ và kiểm thử

Desktop 1440×1000, mobile 390×844, ba vai trò được kiểm bằng Chrome với Uvicorn HTTP thật và SQLite tổng hợp riêng. Không lỗi page JavaScript hoặc tràn ngang. Các nhãn mới có VI/EN; nội dung runbook theo ngôn ngữ tài liệu gốc.

`node --test tests/test_*.js`: 9/9 PASS, gồm boot, i18n, handoff, logout, queue, assignment, status concurrency và test phím tắt mới. Browser kiểm Enter gửi đúng một request; Shift+Enter không gửi; hai lượt chat được giữ; phiên mới; mở lịch sử; reload session; nhãn VI/EN. `git diff --check` PASS.

Chưa thay đổi backend/RAG classifier, chưa chạy lại toàn bộ pytest/PostgreSQL trong đợt chỉ sửa frontend này. Chưa commit/push/deploy. Kho kiến thức và các lỗi backend từ audit trước nằm ngoài phạm vi giao diện Trợ lý.
