# Minh chứng kiểm tra Render — 12/11/2026

Bản công khai được chuẩn bị ngày 20/11/2026 từ hồ sơ chạy thật ngày 12/11. Đây là bản sao đã rà soát và che metadata, không phải một lượt chạy mới. Phần bổ sung báo cáo ở [WEEK6_RESUBMISSION_2026-11-20.md](../../reports/WEEK6_RESUBMISSION_2026-11-20.md).

## Kết quả có thể kiểm tra trực tiếp

- [cases.jsonl](cases.jsonl): **46 dòng**, gồm **45 PASS và 1 FAIL** gốc của phép so hash raw byte local.
- [http.jsonl](http.jsonl): **176 dòng**, không có 5xx. Hai 401 khi đăng nhập thủ công được giữ nguyên; chúng không nằm trong số ca tự động bị lỗi.
- [static-verified.json](static-verified.json): phép đối chiếu tiếp theo có Git blob và SHA-256 sau chuẩn hóa khớp nhau; giải thích lệch CRLF/LF, không xóa FAIL ban đầu.
- [FINAL.json](FINAL.json), [STATUS.json](STATUS.json), [results.json](results.json): bản tổng hợp lịch sử, không phải chấm điểm chuyên gia độc lập.
- [deployment.json](deployment.json): bản Render live trên SHA `a128aa71883531930b403fef92edf171908e7caa`, deploy `dep-dbqplvbrjlhs73a3nvog`. [CI.json](CI.json) dẫn [CI sau merge](https://github.com/thinhsp-203/OpsMind-Helpdesk/actions/runs/43203520890), tách khỏi lượt chạy trên Render.
- [test-data.jsonl](test-data.jsonl): bốn tài khoản thử đã tạo/xóa; ticket thử `HD-0006` closed và `HD-0007` new giữ để truy vết, người gửi ẩn danh. Những tài khoản thử này không phải bằng chứng đã xử lý hai tài khoản lộ trong báo cáo tuần 4.

## Ảnh kết quả tổng hợp

Chỉ chọn năm ảnh vùng kết quả; hai ảnh trang đăng nhập không đưa vào bản công khai. Các ảnh dưới đây giữ nguyên byte gốc và không chứa hồ sơ người dùng/ticket thật:

- [Máy in — hỏi thêm dữ kiện](rag-printer-control.png).
- [Ảnh gốc câu máy in có từ thời tiết](rag-mixed-it-weather.png); ảnh vùng chụp nhỏ được giữ nguyên, đọc log để xem đầy đủ trạng thái.
- [Từ chối câu ngoài phạm vi](rag-pure-weather.png).
- [Dừng an toàn](rag-safety-stop.png).
- [User xác nhận bàn giao tạo ticket thử qua UI](user-ui-handoff-created.png).

## XML thuộc lượt local, không phải Render

[local-issue12/issue12-tests.xml](local-issue12/issue12-tests.xml) có 12 ca PASS của lượt Windows/local ngày 12/11, đối chiếu head PR #13 `26a1c18`. Nó không thuộc 45 kiểm tra Chrome/API trên Render. Lượt Render không xuất JUnit XML. [local-issue12/CI.json](local-issue12/CI.json) là snapshot đối chiếu trước merge; các trường PR draft/chưa merge/credential trong snapshot là lịch sử, không phải trạng thái hiện tại. CI head PR có thể đối chiếu tại [run 43135288701](https://github.com/thinhsp-203/OpsMind-Helpdesk/actions/runs/43135288701).

## Tự kiểm tra bộ tệp

Từ repository root, dùng Python 3.11+ (chỉ đọc tệp, không cần tài khoản hoặc kết nối mạng):

```text
python docs/verification/2026-11-12/verify_evidence.py
```

Lệnh đối chiếu hash, số dòng/status, FAIL gốc, Git blob giải thích CRLF và XML local riêng. [PROVENANCE.json](PROVENANCE.json) ghi hash bản gốc/bản công khai, thay đổi metadata và các ảnh không công khai. Hash giúp phát hiện thay đổi so với bộ tệp này; không chứng minh nguồn gốc, danh tính người thực hiện hoặc việc đã nghiệm thu.

JSON được chuẩn hóa UTF-8/LF. Workspace ID, ID ticket có sẵn không thuộc ca thử và metadata hostname/đường dẫn home local được che. Không công khai mật khẩu, token, cookie, header đăng nhập, email hay nội dung ticket thật. Timestamp/status và số lượng bản ghi được giữ nguyên. Năm ảnh vùng kết quả đã được xem trước khi chọn; không dùng công cụ sửa ảnh để tái tạo kết quả.

Giới hạn giữ nguyên: kiểm thử chức năng được chọn; chưa chứng minh toàn bộ FR, p95/tải, receipt email/Telegram, persistence qua redeploy, duyệt chuyên môn runbook hoặc bộ đánh giá độc lập. Hồ sơ 18/11 và kết quả sửa script TDD sau đó không được gộp vào số liệu 12/11.
