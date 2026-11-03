# Sửa hai nhóm lỗi P2 từ đợt rà hệ thống

Ngày: 03/11/2026. Baseline `67a525e9575e97641adb5f9a5ec28aba80ff3287`; nhánh local riêng `fix/system-audit-p2`. Đây là bản sửa SYS-02/SYS-03; lỗi RAG SYS-01 được theo dõi riêng trong Issue #12/PR #13.

## Ca tái hiện và kết quả sửa

### SYS-02 — source runbook trùng tên vượt giới hạn

Hai runbook cùng tiêu đề hợp lệ dài 64 ký tự đều được tạo, nhưng bản thứ hai có hậu tố `_1` ngoài giới hạn 64 ký tự của validator xóa/reindex. Trước sửa hai thao tác trả 422 trong khi GET tài liệu vẫn 200.

Bộ sinh slug nay chừa chỗ cho hậu tố, gồm cả hậu tố nhiều chữ số. Validator quản trị còn chấp nhận dạng hậu tố số do bản cũ sinh ra, để tài liệu đã tồn tại tiếp tục quản lý được mà không đổi identifier hoặc lịch sử. Vẫn giới hạn ký tự ASCII an toàn và bảo vệ tài liệu builtin như trước.

Hồi quy kiểm 12 tiêu đề trùng nhau, uniqueness/giới hạn stem và reindex/delete của cả source mới lẫn source dài được tạo bởi bản cũ. Chrome thực tế xác nhận Admin reindex và xóa tài liệu trùng tên thành công sau sửa.

### SYS-03 — upload đua với đóng/archive ticket

Ca tái hiện dùng điểm đồng bộ trước hàm persistence gốc: file đã ghi, sau đó ticket được đóng hoặc archive bằng API bình thường, rồi tiếp tục lưu attachment. Trước sửa nhánh đóng trả 201 và lưu tệp; nhánh archive trả 500 và để lại file mồ côi.

Persistence nay dùng cùng cơ chế khóa với các mutator ticket khác: BEGIN IMMEDIATE ở SQLite, FOR UPDATE ở PostgreSQL, kiểm lại closed/archive trong transaction trước insert/audit. Route xóa file mới khi persistence từ chối, trả 409 cho ticket đã đóng và 404 cho ticket không còn tồn tại/đã archive. Upload bình thường vẫn trả 201 và tải lại đúng nội dung.

## Bằng chứng tập trung

- Trước sửa: `tests/test_system_audit_regressions.py` có **5 failed, 1 passed, 6 skipped**. Năm failure đúng ở slug mới, delete/reindex legacy và hai nhánh race.
- Sau sửa: **6 passed, 6 skipped**. Sáu skip là biến thể PostgreSQL khi chưa có DATABASE_URL test, không phải kết quả đạt.
- Chạy lại ca audit gốc 46 request: upload đóng trả 409, archive trả 404; cả hai có 0 attachment rows và 0 file dư. Không còn tái hiện lỗi source dài.
- Chrome + Uvicorn với SQLite riêng: năm kiểm tra vòng đời ticket, CSAT, reindex/delete runbook và duyệt tài liệu đạt; không có pageerror.
- CI đã bổ sung file hồi quy mới vào bước PostgreSQL; chưa có kết quả CI cho nhánh này khi viết mục trên.

Hồi quy toàn bộ local: **370 passed, 49 skipped, 0 failures/errors**, coverage **89%**, 313.32 giây. Skip gồm 41 ca PostgreSQL cũ và 6 biến thể PostgreSQL mới chưa có DB test, một ca cần Docker CLI và một ca cần quyền symlink. JavaScript **15/15**, Ruff, compileall, kiểm tra cú pháp JS và diff check đạt. Workflow YAML đã parse và xác nhận bước PostgreSQL có thu thập file mới. Retrieval dev Hit@3 28/28, tập hồi quy đóng băng 29/30; H03 vẫn sai, các chỉ số này không đo faithfulness hay chất lượng câu trả lời.

## Lệnh tái lập

Từ root repository, dùng Python 3.11.17 trong venv sạch đã cài dependency khóa bằng `pip install --require-hashes -r requirements.txt`. Local dùng dữ liệu tổng hợp và cấu hình cách ly:

```powershell
$env:DATABASE_URL = ''
$env:DEMO_MODE = 'true'
$env:ENABLE_LLM_GENERATION = 'false'
$env:EMAIL_PROVIDER = 'console'
$env:SMTP_ENABLED = 'false'
$env:HELPDESK_DB_PATH = Join-Path (Get-Location) 'data/p2-test-scratch.sqlite3'
python -m pytest tests/test_system_audit_regressions.py -q --tb=short
python -m pytest --cov=app --cov-report=term-missing --cov-report=xml --junitxml=pytest-results.xml -q --tb=short
python -m ruff check app tests scripts
python -m compileall -q app tests scripts
node --check app/static/app.js
node --check app/static/i18n.js
node --test tests/test_*.js
python -m scripts.evaluate_rag
git diff --check
```

CI dùng DATABASE_URL của PostgreSQL 16 sandbox và chạy `python -m pytest tests/test_postgres.py tests/test_system_audit_regressions.py -q`. Các test PostgreSQL reset dữ liệu; chỉ chạy với DB test riêng, không dùng DB vận hành.

Không đổi schema hoặc tự sửa/đổi tên bản ghi hiện có. Chưa push, merge, deploy hoặc thay dữ liệu Render. Local chưa chạy PostgreSQL; không coi kiểm thử SQLite là bằng chứng khóa dòng PostgreSQL đã được xác minh runtime.
