# Chẩn đoán chi phí kết nối DB — 14/11/2026

Theo dõi: [Issue #17](https://github.com/thinhsp-203/OpsMind-Helpdesk/issues/17).
Issue giữ mở đến khi review, triển khai và đo lại trên Render hoàn tất.

## Phạm vi và phép đo trên Render

Nguồn baseline: `main` và Render đều ở `a128aa71883531930b403fef92edf171908e7caa`.
Deploy `dep-dbqplvbrjlhs73a3nvog` vẫn live. Không thay cấu hình, deploy hay dữ liệu
production trong lượt chẩn đoán này.

Hai lượt đo GET xen kẽ `/config` và `/health`, mỗi lượt một cặp warm-up và ba
cặp dùng tính median: `/health` 2.235/2.260 ms, `/config` 277/319 ms. Chênh lệch
median khoảng 1.958/1.941 ms. Lượt GET đầu tiên mất 42.882 ms được giữ riêng,
không đưa vào số đo warm. Không kết luận nguyên nhân của lượt đầu chỉ từ timing.

Lệnh chạy từ workspace ngoài repository:

```text
node work/perf-diagnosis-2026-11-14/public-loop.cjs
```

Cả hai lượt exit 1 vì health vượt ngưỡng chẩn đoán 1.500 ms. Ngưỡng này chỉ
phát hiện độ trễ để debug; không thay NFR-01 của SRS (RAG p95 ≤ 3 giây với ít
nhất 30 truy vấn). Mẫu trên không phải phép đo tải hoặc p95 nghiệm thu.

## Giả thuyết và kiểm chứng

Đã xét theo thứ tự: chi phí mở kết nối lặp lại; số lượt SQL nối tiếp; chờ tài
nguyên dịch vụ/DB. Mẫu CPU/RAM Render lấy cùng đợt chưa sát giới hạn nhưng quá
ít để loại trừ mọi vấn đề tài nguyên.

Trace thực trên PostgreSQL 16.9 tại `127.0.0.1:55449/opsmind_perf_test`, dữ liệu
giả, LLM/SMTP/Telegram tắt, cho thấy mỗi request health mở một kết nối vật lý;
đọc ticket hai kết nối; hỏi làm rõ RAG và thêm comment ba kết nối. Mỗi helper
store cũ mở mới `psycopg.connect()` rồi commit/rollback và đóng. Các helper chạy
nối tiếp nên chi phí kết nối bị cộng nhiều lần trên một request.

Khi chỉ thêm 120 ms vào thao tác mở kết nối local, số kết nối vẫn là 1/2/3/3,
còn thời gian quan sát health/ticket-read/RAG/comment lần lượt khoảng
250/449/772/684 ms. Đây là mô hình chi phí kết nối có kiểm soát, không mô phỏng
đầy đủ đường truyền, tải hoặc cấu hình production.

## Bản sửa

`app/postgres.py` sở hữu pool đồng bộ theo process: tối thiểu một, tối đa bốn
kết nối; connect timeout 5 giây, chờ lease tối đa 10 giây; check kết nối khi
mượn và trả lease bằng context manager của Psycopg. Mỗi helper store vẫn là
một giao dịch riêng, commit khi thành công và rollback khi có lỗi. Không tự
replay câu SQL lỗi, không chia sẻ giao dịch đang hoạt động và không cache
thông tin tài khoản/quyền. Query kiểm tra kết nối thêm một round trip mỗi lease;
đánh đổi này phải được tính trong phép đo Render sau triển khai.

Pool mở và chờ kết nối tối thiểu trước khi cấp lease đầu tiên, tránh tạo thêm
kết nối chỉ vì request đầu đến trong lúc pool đang khởi tạo. App shutdown đóng
pool sau khi dừng worker; có cleanup khi process kết thúc. URL đổi hoặc pool đã
đóng thì tạo pool mới. SQLite giữ đường kết nối hiện có. Không migration/schema
hay thay đổi hạ tầng trả phí. Mỗi worker process có pool riêng; tổng ngân sách
kết nối phải nhân theo số worker/instance, không mặc nhiên đạt mục tiêu tải.

Thêm dependency `psycopg-pool==3.3.3`, khóa hash bằng uv 0.13.4. Audit ngày
14/11 phát hiện advisory mới cập nhật 13/11 cho OpenTelemetry 1.45.1, nên chỉ
nâng transitive `opentelemetry-api` lên 1.45.2. Không gán advisory này làm nguyên
nhân của độ trễ quan sát. Các dependency khác giữ phiên bản cũ.

## Bằng chứng trước/sau và giới hạn

Test `test_postgres_reuses_physical_connection_between_store_operations` viết
trước sửa: **1 failed**, do PID backend khác nhau giữa hai thao tác nối tiếp.
Bộ pool sau sửa: **7 passed**; có commit, rollback sau lỗi SQL, lease song song,
kết nối đóng, đổi URL và shutdown/reopen. CI PostgreSQL đã thêm file này để
không bỏ qua các test chỉ vì suite mặc định không có DATABASE_URL.

Với cùng chi phí kết nối local 120 ms và pool đã được warm bằng đăng nhập,
các API trên không mở kết nối mới; timing một lượt health/ticket-read/RAG/comment
khoảng 45/10/36/14 ms. Đây là số đo local quan sát, không phải benchmark thống kê
hoặc mức giảm đã chứng minh trên Render. Trace giữ cả query kiểm tra lease.

Vòng lặp chẩn đoán bổ sung qua API thật dùng cùng venv cuối, DB local riêng
`opsmind_perf_trace`, cùng chi phí kết nối 120 ms và ngưỡng đọc ticket 200 ms:
baseline đọc ticket 623 ms (exit 1), bản sửa 16 ms (exit 0). Biến `PERF_REPO`
chọn source baseline hoặc bản sửa cho cùng script `profile_api.py`; không sửa
fixture/query để tạo màu xanh. Các ngưỡng này không phải NFR production.

PostgreSQL trên bộ dependency cuối: **70 passed**, gồm bảy test pool mới.
Full suite local trên cùng bộ dependency: **387 passed, 61 skipped, 0 failures/errors**,
chạy đủ 448 node qua bốn nhóm độc lập, mỗi nhóm 112 node. Manifest và JUnit
được đối chiếu không thiếu hoặc trùng case; coverage gộp 2.949/3.291 dòng,
89,61% (CLI làm tròn 90%). Trong 61 skip có 59 ca cần PostgreSQL đã được chạy
ở suite riêng; hai ca còn lại cần quyền symlink và Docker CLI. Các lượt full
suite không hoàn tất do thay dependency hoặc runner bị ngắt không được cộng
vào kết quả. Đây là phương pháp chạy local, không thay một kết quả CI chưa có.
JavaScript **15/15**, ruff và compileall đạt. Audit lockfile sau patch không
còn advisory được nhận diện trên môi trường Windows; chưa có audit Linux hoặc
Docker build/CI cho nhánh này. Retrieval baseline và bản sửa đều exit 0 khi
console đặt UTF-8, dev Hit@3 28/28 và hồi quy Hit@1/Hit@3 29/30, MRR@3 0,967;
H03 vẫn sai. Lượt console CP1252 ban đầu exit 1 vì UnicodeEncodeError, được giữ
trong log, không đổi dữ liệu hoặc rubric để bỏ qua lỗi.

Kết quả suite, audit và lệnh tái lập được lưu trong thư mục workspace
`outputs/PERF_DIAGNOSIS_2026-11-14`, không commit DB hoặc log sinh ra. Chỉ tuyên bố
khắc phục độ trễ Render sau khi review, triển khai bản sửa và đo lại cùng
endpoint/API; RAG cần đủ mẫu theo NFR. Các lượt GET production trước sửa vẫn
là baseline, không phải kết quả sau sửa.

Tham khảo chính thức:

- [Psycopg: connection pools](https://www.psycopg.org/psycopg3/docs/advanced/pool.html)
- [Psycopg pool API](https://www.psycopg.org/psycopg3/docs/api/pool.html)
- [OpenTelemetry advisory](https://github.com/advisories/GHSA-mf5v-w3w3-f6cg)
