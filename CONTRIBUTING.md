# Hướng dẫn đóng góp

Repository này chứa prototype học thuật Helpdesk RAG. Giữ thay đổi đúng phạm vi hiện có, ưu tiên sửa nhỏ có kiểm thử và không mô tả mục tiêu hoặc đề xuất tương lai như tính năng đã hoàn thành.

## Thiết lập môi trường

Yêu cầu Python 3.11 trở lên và Git. Trên Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

Chạy ứng dụng bằng `py -m uvicorn app.main:app --reload`. Chế độ local mặc định tạo tài khoản demo trong DB mới; chỉ dùng dữ liệu giả. Xem [hướng dẫn triển khai](docs/DEPLOYMENT.md) trước khi dùng cấu hình khác.

## Quy trình thay đổi

1. Tạo nhánh tính năng/lỗi từ `main`; không commit trực tiếp lên `main`.
2. Giữ quyền truy cập theo vai trò, trạng thái ticket và migration SQLite tương thích dữ liệu hiện hữu.
3. Thêm/cập nhật test cho hành vi và quyền bị ảnh hưởng. Không dùng DB demo cục bộ làm fixture hoặc đưa dữ liệu DB vào commit.
4. Cập nhật tài liệu liên quan để khớp đúng hành vi hiện tại; ghi rõ phần chưa kiểm chứng.
5. Mở pull request mô tả lý do, cách triển khai, các lệnh xác minh và giới hạn còn lại.

## Kiểm tra trước khi mở pull request

```powershell
py -m ruff check app tests scripts
node --check app/static/app.js
node --check app/static/i18n.js
node tests/test_i18n.js
py -m compileall -q app tests scripts
py -m pytest --cov=app --cov-report=term-missing --cov-report=xml
py -m scripts.evaluate_rag
```

Docker image được build trong GitHub Actions. Nếu thay đổi Dockerfile/Compose, kiểm tra build bằng Docker khi có môi trường hỗ trợ; nêu rõ nếu không chạy được.

## Vệ sinh repository

- Không commit `.env`, secret/token, `data/helpdesk.sqlite3`, WAL/SHM, `data/attachments/`, cache, bytecode, `.coverage` hoặc report coverage phát sinh.
- Chỉ thêm runbook Markdown đã rà soát; không đưa mật khẩu, cấu hình nhạy cảm, thông tin khách hàng hay dữ liệu cá nhân vào KB và bộ câu hỏi.
- Không đưa ảnh chụp chứa dữ liệu người dùng hoặc ticket thật vào repository.
- Không thêm dependency/dịch vụ (LLM, vector DB, Redis, PostgreSQL, email, WebSocket) nếu chưa có yêu cầu, thiết kế, kiểm thử và cập nhật tài liệu tương ứng.

## Quy tắc báo cáo bằng chứng

Nêu số test, coverage và kết quả retrieval kèm lệnh, ngày/môi trường, cỡ mẫu và giới hạn diễn giải. Bộ 30 câu hiện tại là draft tự soạn; hit@3 không đo faithfulness, chất lượng câu trả lời sinh hoặc khả năng sử dụng. Không tự tạo số khảo sát, SUS, pilot, hiệu năng production hay so sánh giá/feature chưa kiểm chứng.
