# Sửa lỗi sau rà soát khóa luận — 29/10/2026

## Phạm vi và trạng thái

Bản làm việc xuất phát từ commit `0dd9defc8a1ef10bcec36d6f457368b7d3a60bd9`; các kết quả bên dưới được chạy local trước khi tạo commit chứa bản sửa và tài liệu này. Chưa xác minh CI/cloud/deploy. Không dùng dữ liệu/tài khoản thật để kiểm thử. Môi trường: macOS ARM64, Python 3.12.14, Node 24.22.1, SQLite; PostgreSQL 16 trong container thử nghiệm riêng. Không gọi LLM, SMTP hoặc Telegram thật.

## Thay đổi

1. **Bảo toàn runbook:** seed chỉ thêm tài liệu thiếu. Nội dung, metadata, trạng thái duyệt và lịch sử phiên bản đã lưu không bị thay bằng file đóng gói khi restart. Kiểm thử cả published/pending_review/archived và đọc bằng tiến trình Python mới; PostgreSQL cũng kiểm tra bảo toàn tài liệu.
2. **Đính chính đánh giá:** dùng chung bộ chấm nguyên cụm có ranh giới từ, chuẩn hóa Unicode NFC; không nối cụm xuyên hai đoạn, không chấm chỉ từ tiêu đề, không chấp nhận một từ trùng đơn lẻ hoặc coi nhãn rỗng là điểm hoàn hảo. Đổi tên thành chẩn đoán từ vựng, không gọi là chất lượng câu trả lời.
3. **Giữ nguyên cổng hồi quy truy xuất:** không hạ ngưỡng Hit@1, Hit@3, MRR và từ chối. Loại bỏ ngưỡng coverage của bộ chấm lỏng cũ vì chưa hiệu chuẩn cho cách chấm mới; không thay bằng ngưỡng thấp hơn để đạt. Chất lượng ngữ nghĩa cần chấm độc lập.
4. **Metadata dữ liệu:** không sửa CSV; cập nhật SHA-256 theo UTF-8/LF đúng trong Git, thêm `.gitattributes`. Script dừng khi checksum tập đóng băng không khớp. Dataset Card ghi đính chính CRLF.
5. **Đo tải đúng xác thực:** đăng nhập qua `/auth/login`, kiểm tra quyền đọc kho tri thức và endpoint trước khi đo. Mặc định gọi HTTP thật; `--in-process` chỉ chẩn đoán local. Báo riêng thành công/lỗi, mã HTTP, attempt/success RPS, độ trễ; không tính lỗi xác thực là thông lượng nghiệp vụ thành công. Có JSON output và mã thoát lỗi.
6. **Ngữ cảnh nối tiếp có giới hạn:** câu ngắn như “Vẫn không được” dùng một mô tả CNTT của người dùng trong 6 tin gần nhất, cùng phiên và đúng chủ sở hữu. Không dùng nội dung trợ lý làm sự thật; không ghép chủ đề CNTT mới hoặc mẫu ngoài phạm vi rõ ràng. Lưu nguyên câu người dùng nhập. Đây là quy tắc đơn giản, chưa phải bộ nhớ hội thoại hay hiểu ngữ cảnh tổng quát.
7. **Diễn giải trạng thái RAG:** bổ sung `has_sources`, `answer_verification=not_verified`, `context_used`. Giữ `grounded` để tương thích với nghĩa tìm được tài liệu; không bảo đảm mọi mệnh đề sinh ra đều đúng. OpenAPI mô tả rõ giới hạn.
8. **Kiểm thử và CI:** chạy toàn bộ `tests/test_*.js`. Sửa đường dẫn `/api/auth/*` cho tài khoản buộc đổi mật khẩu. Đồng bộ hai test outbox PostgreSQL theo việc Discord đã ngừng dùng: một delivery Telegram/sự kiện; vẫn kiểm tra nhận việc và cập nhật đồng thời.

## Kết quả xác minh

| Kiểm tra | Kết quả | Output gốc |
|---|---|---|
| Python chính, gồm HTTP/event-loop và Docker build context | 322 đạt, 40 PostgreSQL bỏ qua trong lượt SQLite | [python-tests.txt](verification/2026-10-29/python-tests.txt) |
| PostgreSQL 16 riêng | 40/40 đạt | [postgres-tests.txt](verification/2026-10-29/postgres-tests.txt) |
| JavaScript | 14/14 đạt | [javascript-tests.txt](verification/2026-10-29/javascript-tests.txt) |
| Ruff | Đạt | [lint.txt](verification/2026-10-29/lint.txt) |
| Công cụ benchmark qua Uvicorn HTTP local | 12/12 request đo thành công, 3/endpoint, concurrency 2 | [http-smoke.json](verification/2026-10-29/http-smoke.json) |
| RAG trên DB mới chứa 30 runbook đóng gói | Đạt cổng hồi quy | [rag-evaluation.txt](verification/2026-10-29/rag-evaluation.txt) |

40 ca PostgreSQL bỏ qua ở lượt SQLite đã chạy riêng, không coi skip là pass. Còn warning TestClient/httpx có sẵn; không thay dependency trong đợt này. Mẫu HTTP 3 request/endpoint chỉ xác minh công cụ, **không đủ xác nhận NFR, tải thực tế hoặc tốc độ trên Render**. Preflight và đăng nhập không tính vào số request đo.

### RAG chạy lại

| Chỉ số | Dev: 28 in-scope, 2 OOS | Hồi quy: 30 in-scope, 30 OOS |
|---|---:|---:|
| Hit@1 | 23/28 | 29/30 |
| Hit@3 | 28/28 | 29/30 |
| MRR@3 | 0,911 | 0,967 |
| Từ chối OOS | 2/2 | 30/30 |
| Chẩn đoán coverage cụm từ | 47,0% | 75,6% |

H03 chưa truy xuất đúng `certificate_signature.md` trong top 3; giữ nguyên dữ liệu và ghi rõ trường hợp sai. Không tinh chỉnh câu hỏi/từ điển để che lỗi. Coverage chỉ đo khớp cụm: có thể bỏ sót diễn đạt tương đương và vẫn đếm cụm trong câu phủ định. Không suy ra faithfulness hay cải thiện chất lượng. Không so sánh trực tiếp coverage cũ/mới vì cách chấm khác nhau.

## Cập nhật runbook và chạy lại

Cập nhật file runbook trong Git **không tự thay** tài liệu đã có trong DB. Tài liệu mới vẫn được seed. Với bản cập nhật an toàn/nội dung của tài liệu cũ, Admin cần đối chiếu file mới, sửa qua luồng quản lý kho tri thức có lịch sử phiên bản và kiểm tra trạng thái công bố. Sao lưu DB trước khi cập nhật hàng loạt; không xóa DB/tài liệu để ép seed lại.

Chạy đánh giá trong môi trường thử nghiệm đã cấu hình:

```sh
python -m scripts.evaluate_rag
```

Đo tải dùng tài khoản thử nghiệm riêng, dữ liệu có thể xóa; đặt `OPSMIND_BENCHMARK_PASSWORD` trong môi trường, không lưu mật khẩu vào mã/biên bản:

```sh
python -m scripts.benchmark_load --base-url http://127.0.0.1:8000 --username benchmark --requests 150 --concurrency 10 --output benchmark.json
```

`/rag/ask` tạo lịch sử chat, kể cả preflight. Cần ghi commit/config server, cấu hình LLM, corpus và cỡ mẫu. HTTP local không thay cho đo trên môi trường triển khai.

## Thực nghiệm còn phải thực hiện

- Chốt hai commit trước/sau PR #6, cùng corpus, dữ liệu và môi trường; lưu output để so sánh.
- Thu thập câu hỏi độc lập chưa dùng tinh chỉnh; không sửa nhãn tập hồi quy để tăng điểm.
- Chuyên gia chấm đúng/đủ/bám nguồn/an toàn, kèm dẫn chứng và xử lý bất đồng. Chưa có kết quả người thật trong bản sửa này.
- Thử tác vụ với người dùng, xác minh email/Telegram và backup/restore trên staging. Mock/provider acceptance không đồng nghĩa người nhận đã đọc.

[source-manifest.json](verification/2026-10-29/source-manifest.json) ghi SHA-256 nguồn local đã kiểm tra. Khi nộp báo cáo, dùng link đầy đủ tới commit chứa bản sửa này; không dùng commit baseline để đại diện kết quả sau sửa.
