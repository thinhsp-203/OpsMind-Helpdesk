# Sửa lỗi 500 khi xóa tài khoản — Issue #14

Ngày kiểm tra: 03/11/2026. Baseline: `8fd66044e4aabc556b06eb4e6a28486139065a05`.
Issue: https://github.com/thinhsp-203/OpsMind-Helpdesk/issues/14.
Nhánh: `fix/admin-delete-postgres`.

## Lỗi và nguyên nhân

Người dùng xác nhận thông báo `Yêu cầu thất bại (500)` xuất hiện khi xóa tài khoản.
Render đang chạy baseline nêu trên. Log ngày 03/11/2026 lúc 02:53:29 UTC ghi nhận
`DELETE /admin/users/<redacted>` trả 500. Cảnh báo đầu tiên là
`relation "email_outbox" does not exist`; câu SQL tiếp theo lỗi
`psycopg.errors.InFailedSqlTransaction`.

`delete_user_and_anonymize()` dùng tên module `email_outbox` làm tên bảng,
trong khi schema thật là `email_deliveries`. Hàm bắt và bỏ qua lỗi SQL này.
SQLite tiếp tục transaction và có khóa ngoại cascade nên các test cũ vẫn đạt;
PostgreSQL hủy transaction sau câu SQL sai và từ chối các câu lệnh tiếp theo.

Đã tái hiện bằng PostgreSQL 16.9 thật, riêng trên localhost với DB trống và tài
khoản tổng hợp. Không thử xóa tài khoản thật trên Render. Python 3.11.17,
Windows; dependency theo lockfile hiện tại. Binary PostgreSQL dùng để test lấy
từ artifact `io.zonky.test.postgres:embedded-postgres-binaries-windows-amd64:16.9.0`
trên Maven Central và đối chiếu checksum SHA-1 của artifact. Binary và DB test
không phải dependency ứng dụng, không đưa vào repository.

## Bản sửa

- Xóa job email ở đúng bảng `email_deliveries` trong cùng transaction.
- Không bỏ qua lỗi ở các bước xóa email và ẩn danh notification snapshot:
  lỗi phải rollback toàn bộ thao tác, tránh báo xóa thành công khi còn dữ liệu.
- Route Admin chuyển `LookupError` của tài khoản không tồn tại thành HTTP 404.
- Giữ nguyên kiểm tra vai trò, tên xác nhận, tự xóa từ trang Admin và Admin cuối.

Regression nằm trong `tests/test_system_audit_regressions.py`, đã được workflow
hiện tại chạy trong bước PostgreSQL. Bao phủ Admin xóa, tự xóa, JWT cũ bị từ
chối, email/reset token/chat/rate limit được xóa, ticket/comment/snapshot được
ẩn danh, thiếu tài khoản, rollback khi JSON snapshot hỏng và các chốt phân quyền.

## Kiểm chứng trước sửa

Lệnh từ root repository với `DATABASE_URL` trỏ tới DB PostgreSQL localhost riêng:

```powershell
python -m pytest tests/test_system_audit_regressions.py -k 'account_deletion or missing_account' -q
```

Kết quả: **4 failed, 2 passed, 12 deselected**. Admin xóa và tự xóa trên PostgreSQL
đều trả 500; cả hai backend trả 500 khi Admin xóa một tài khoản không tồn tại.
Chỉ đổi tên bảng: bốn biến thể xóa tài khoản đều đạt (**4 passed**).
Thêm ca snapshot JSON hỏng cho thấy cả hai backend vẫn báo xóa thành công
khi bỏ qua lỗi ẩn danh (**2 failed**); bản sửa yêu cầu rollback.

## Lệnh xác minh sau sửa

```powershell
python -m pytest tests/test_postgres.py tests/test_system_audit_regressions.py -q
# Chạy bộ toàn bộ riêng với DATABASE_URL rỗng:
python -m pytest --cov=app --cov-report=term-missing -q
python -m ruff check app tests scripts
python -m compileall -q app tests scripts
node --check app/static/app.js
node --check app/static/i18n.js
node tests/test_i18n.js
node tests/test_frontend_boot.js
python -m scripts.evaluate_rag
git diff --check
```

Các test phải dùng DB tổng hợp riêng: fixture PostgreSQL có `reset_store()`.
Tuyệt đối không trỏ lệnh pytest tới DATABASE_URL production.

## Kết quả cuối

Bằng chứng chạy ngày 03/11/2026, được đối chiếu lại ngày 07/11/2026 trước khi phát hành:

- Bộ toàn bộ với SQLite: **375 passed, 54 skipped**, 793,69 giây; coverage **90%**.
  54 skip gồm 41 ca PostgreSQL, 11 biến thể PostgreSQL của file audit, một ca
  cần Docker CLI và một ca cần quyền symlink. Skip không được tính là đạt.
- Bộ PostgreSQL riêng: **63 passed, 0 skipped**, 250,19 giây. Gồm 41 ca backend
  cũ và 22 biến thể SQLite/PostgreSQL trong file audit. Cụm PostgreSQL test đã dừng.
- Ruff, compileall, kiểm tra cú pháp JavaScript, hai script test JavaScript
  (15 kiểm tra) và `git diff --check` đạt.
- Retrieval: dev Hit@3 100%; tập hồi quy đóng băng Hit@1/Hit@3 96,7%, MRR@3
  0,967; từ chối ngoài phạm vi 30/30. H03 vẫn sai. Đây không phải đánh giá
  độc lập, không đo faithfulness hoặc chất lượng câu trả lời sinh.

XML và log được giữ trong thư mục bằng chứng ngoài repository. CI sẽ chạy lại
bộ kiểm tra cho commit phát hành; SHA, CI và trạng thái deploy được cập nhật
trong Issue #14. Không xóa tài khoản thật trên production để thử nghiệm.
HTTP health và trạng thái deploy live không thay thế việc xác nhận lại thao
tác xóa qua giao diện với tài khoản do người quản trị lựa chọn.
