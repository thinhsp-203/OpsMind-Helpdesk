# Tiếp thu góp ý của GVHD — bổ sung báo cáo tuần 6

Ngày cập nhật: 20/11/2026. Mục này bổ sung cho báo cáo đã nộp, không thay đổi kết quả chạy lịch sử.

## 1. Thống nhất thông tin xử lý hai tài khoản đã lộ

Nhóm xác nhận **Thịnh đã đổi mật khẩu của hai tài khoản từng xuất hiện trong báo cáo tuần 4**, thực hiện trực tiếp trên giao diện web bằng tài khoản quản trị. Nội dung này theo xác nhận của người phụ trách; không phải kết quả agent tự kiểm tra tài khoản.

- Người thực hiện: Thịnh.
- Cách thực hiện: đổi mật khẩu trực tiếp trên giao diện web với quyền quản trị.
- Thời điểm đổi: chưa được cung cấp/xác nhận trong hồ sơ bổ sung này; không dùng ngày soạn báo cáo làm ngày đổi mật khẩu.
- Kiểm tra phiên cũ: người phụ trách xác nhận **chỉ đổi mật khẩu, chưa kiểm tra lại phiên cũ** của hai tài khoản.
- Trạng thái thống nhất cho mục 1 và bảng mục 7: **Đã đổi mật khẩu; chưa hoàn tất xác minh thu hồi phiên cũ và bổ sung thời điểm xử lý.**

Nhóm chưa ghi điều kiện này là hoàn tất. Thịnh phụ trách bổ sung thời điểm có căn cứ và kết quả kiểm tra phiên cũ. Không đưa mật khẩu/token mới hoặc cũ vào báo cáo, log hay GitHub. Các log về tài khoản thử trong phần kiểm thử Render không được dùng thay bằng chứng cho hai tài khoản đã lộ.

## 2. Bổ sung tệp minh chứng kiểm tra Render ngày 12/11

Bộ minh chứng được đính kèm tại [docs/verification/2026-11-12](../verification/2026-11-12/README.md), gồm log JSON/JSONL, định danh triển khai, bản giải thích lệch hash và năm ảnh vùng kết quả kiểm thử tổng hợp. Có thể kiểm tra trực tiếp từng tệp trên GitHub; các bản local gốc được giữ nguyên.

Đợt chạy dùng commit `a128aa71883531930b403fef92edf171908e7caa`, deploy `dep-dbqplvbrjlhs73a3nvog`. Kết quả đối chiếu từ log: **45 PASS**, một lần kiểm tra hash byte local thất bại do CRLF/LF được giữ nguyên và giải thích bằng Git blob; **176 bản ghi HTTP, không có 5xx**. Hai lần đăng nhập thủ công trả 401 cũng được giữ trong log.

Đây là các kiểm tra chức năng được chọn trên URL Render. Không suy ra đã nghiệm thu toàn bộ hệ thống, hiệu năng p95/tải, persistence qua redeploy hoặc chất lượng RAG độc lập.

XML `local-issue12/issue12-tests.xml` thuộc lượt kiểm thử **Windows/local ngày 12/11 trên head `26a1c18`**, gồm 12 ca đạt; được đặt riêng và ghi rõ nguồn. Lượt Chrome/API trên Render không xuất JUnit XML. Không gọi XML local hoặc CI là XML chạy trên Render.

## 3. Các góp ý tiếp tục theo dõi

- MC07: chưa có bản báo cáo tuần 6 đã nộp trong repository/workspace này để sửa đúng vị trí. Khi ghép mục bổ sung vào bản gốc, sửa tiền tố `Ihttps://` thành `https://`; chưa ghi là đã sửa trong bản nộp.
- Người duyệt runbook và người chuẩn bị bộ 30 ca độc lập: chưa có tên được nhóm xác nhận để ghi vào mục này. Không suy danh tính chuyên gia từ các ID mẫu trong bộ ca.
- [Issue #17](https://github.com/thinhsp-203/OpsMind-Helpdesk/issues/17): tiếp tục review/triển khai bản sửa rồi đo lại trên đúng SHA thực tế đang chạy. [PR #18](https://github.com/thinhsp-203/OpsMind-Helpdesk/pull/18) vẫn draft tại thời điểm đối chiếu; số đo mô phỏng local không phải kết quả sau sửa trên Render.

Bổ sung này không tự thay kết luận **CHƯA DUYỆT** của GVHD. Điều kiện xác nhận mật khẩu/phiên cũ còn thiếu như mục 1; phần công khai tệp minh chứng được kiểm tra qua liên kết mục 2 sau khi nhánh tài liệu được đưa lên GitHub.
