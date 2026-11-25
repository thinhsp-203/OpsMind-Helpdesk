# Tiếp thu góp ý của GVHD — báo cáo tuần 6 nộp lại

Ngày cập nhật: 25/11/2026. Phần “Tiếp thu góp ý” chỉ giữ một bản này; các đoạn dán trùng ở đầu báo cáo đã được bỏ. Nội dung bên dưới chỉ sửa bốn điểm GVHD yêu cầu và không thay đổi kết quả chạy lịch sử.

## 1. Thống nhất thông tin xử lý hai tài khoản đã lộ

Hai tài khoản có mật khẩu từng xuất hiện ở cuối báo cáo tuần 4 đã được xử lý trực tiếp qua giao diện quản trị. Hồ sơ không còn giờ thao tác chính xác nên ghi **ước khoảng ngày 20/11/2026**, thay vì suy đoán một mốc giờ. Cả hai dòng dưới đây là xác nhận của người thực hiện Thịnh; không phải agent tự đăng nhập hay kiểm tra độc lập.

| Tài khoản | Thời điểm | Người và cách thực hiện | Quan sát sau xử lý |
| --- | --- | --- | --- |
| `user` | Ước khoảng 20/11/2026; không còn hồ sơ giờ chính xác | Thịnh đổi mật khẩu trên giao diện web bằng tài khoản quản trị. | Thịnh kiểm tra lại phiên có trước lần đổi; phiên cũ không tiếp tục dùng được và bị yêu cầu đăng nhập lại. |
| `huy` | Ước khoảng 20/11/2026; không còn hồ sơ giờ chính xác | Thịnh đổi mật khẩu trên giao diện web bằng tài khoản quản trị. | Thịnh kiểm tra lại phiên có trước lần đổi; phiên cũ không tiếp tục dùng được và bị yêu cầu đăng nhập lại. |

Trạng thái thống nhất cho mục 1 và bảng mục 7: **đã đổi mật khẩu hai tài khoản và đã kiểm tra phiên cũ — hoàn tất theo xác nhận của nhóm.** Không đưa mật khẩu, token, session ID hoặc ảnh có thông tin đăng nhập vào báo cáo hay GitHub. Log về tài khoản thử Render không được dùng thay hồ sơ trên.

## 2. Bổ sung tệp minh chứng kiểm tra Render ngày 12/11

Bộ minh chứng được công khai tại commit [`8ea71e2`](https://github.com/thinhsp-203/OpsMind-Helpdesk/commit/8ea71e25f49254017fd2367376503fdf36777554) ngày 20/11/2026, trong [docs/verification/2026-11-12](../verification/2026-11-12/README.md). Commit công khai này chứa log JSON/JSONL, định danh triển khai, giải thích lệch hash và năm ảnh vùng kết quả. Các bản local gốc được giữ nguyên.

Phân biệt hai mốc: đợt kiểm tra Render ngày 12/11 dùng commit `a128aa71883531930b403fef92edf171908e7caa`, deploy `dep-dbqplvbrjlhs73a3nvog`; **thư mục minh chứng không tồn tại tại `a128aa7`**. Thư mục được công khai sau đó tại `8ea71e2`. Kết quả đối chiếu từ log: **45 PASS**, một lần kiểm tra hash byte local thất bại do CRLF/LF được giữ nguyên và giải thích bằng Git blob; **176 bản ghi HTTP, không có 5xx**. Hai lần đăng nhập thủ công trả 401 cũng được giữ trong log.

Đây là các kiểm tra chức năng được chọn trên URL Render. Không suy ra đã nghiệm thu toàn bộ hệ thống, hiệu năng p95/tải, persistence qua redeploy hoặc chất lượng RAG độc lập.

XML `local-issue12/issue12-tests.xml` thuộc lượt kiểm thử **Windows/local ngày 12/11 trên head `26a1c18`**, gồm 12 ca đạt; được đặt riêng và ghi rõ nguồn. Lượt Chrome/API trên Render không xuất JUnit XML. Không gọi XML local hoặc CI là XML chạy trên Render.

## 3. Các chỉnh sửa biên tập và việc theo kế hoạch tuần sau

- MC07: đã bỏ ký tự `I` bị dư trước URL; liên kết trong bản nộp lại dùng tiền tố `https://`.
- Người duyệt runbook và người chuẩn bị bộ 30 ca độc lập: chưa có tên được nhóm xác nhận để ghi vào mục này. Không suy danh tính chuyên gia từ các ID mẫu trong bộ ca.
- [Issue #17](https://github.com/thinhsp-203/OpsMind-Helpdesk/issues/17): tiếp tục review/triển khai bản sửa rồi đo lại trên đúng SHA thực tế đang chạy. [PR #18](https://github.com/thinhsp-203/OpsMind-Helpdesk/pull/18) vẫn draft tại thời điểm đối chiếu; số đo mô phỏng local không phải kết quả sau sửa trên Render.

Bản nộp lại này dùng để GVHD xét duyệt. Các đầu việc còn lại ở hai dòng cuối được giữ theo kế hoạch tuần sau, không đổi trạng thái thành hoàn tất.
