# Cài đặt và chạy prototype

Tài liệu này hướng dẫn chạy demo trên máy cá nhân. Cấu hình trong repository chưa phải hướng dẫn triển khai production; không mở trực tiếp dịch vụ ra Internet.

## Chạy local trên Windows

Yêu cầu Python 3.11 trở lên. Từ thư mục gốc repository:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload
```

Mở `http://127.0.0.1:8000`; health check tại `/health` và OpenAPI UI tại `/docs`. Lưu ý: Trong mã nguồn `app/config.py`, `DEMO_MODE` mặc định là `false` để đảm bảo an toàn. Khi muốn chạy chế độ demo trên máy cá nhân, hãy gán `$env:DEMO_MODE = "true"`. Khi `DEMO_MODE=true`, trên DB mới ứng dụng sẽ tạo ba tài khoản demo `user/user`, `agent/agent`, `admin/admin`. Chỉ dùng dữ liệu giả.

Nếu muốn đặt secret cố định trong phiên PowerShell local:

```powershell
$env:SECRET_KEY = (py -c "import secrets; print(secrets.token_urlsafe(48))")
```

Secret demo ngẫu nhiên mới được tạo khi mỗi lần khởi động nếu biến này không đặt; phiên JWT cũ có thể mất hiệu lực sau restart.

## Chạy bằng Docker Compose

Build context loại `.env`, `.env.*` ở mọi cấp (kể cả `.env.example`), SQLite trong `data`, attachment, thư mục `runtime` và log. Truyền cấu hình khi chạy qua môi trường/Compose; không sao chép secret vào source hoặc thêm vào Dockerfile. `.gitignore` không thay thế `.dockerignore`. Nội dung KB mặc định và `data/rag_dictionary.json` vẫn cần trong image.

Kiểm chứng chính sách bằng Docker BuildKit với dữ liệu giả: `python -m pytest tests/test_docker_context.py -q -rs`. Test build một image `FROM scratch`, xuất filesystem rồi kiểm tra tệp bị loại và tài nguyên cần giữ; không khởi động ứng dụng hoặc đọc `.env` thật. Test tự bỏ qua khi không có Docker CLI; khi có CLI nhưng daemon/build lỗi thì test thất bại.

Yêu cầu Docker Engine/Desktop và Docker Compose:

```powershell
docker compose up --build -d
docker compose logs -f helpdesk
```

Mở `http://127.0.0.1:8000`. Compose chạy PostgreSQL 16 cho ứng dụng và chỉ bind web/API vào loopback. Ba named volume tách biệt lưu PostgreSQL (`postgres-data`), tệp runtime/attachment (`helpdesk-runtime`) và runbook (`helpdesk-knowledge`). `docker compose down` giữ dữ liệu; không chạy `docker compose down -v` nếu muốn giữ các volume.

Compose mặc định bật demo mode và dùng mật khẩu PostgreSQL chỉ dành cho demo local. Đặt `POSTGRES_PASSWORD` mạnh và `SECRET_KEY` riêng trong môi trường trước khi chạy trên máy chia sẻ. Có thể đặt `DATABASE_URL` để ứng dụng kết nối PostgreSQL bên ngoài; giá trị URI cần URL-encode thông tin đăng nhập có ký tự đặc biệt. Compose vẫn khởi động service PostgreSQL cục bộ.

Đối với **database mới** ở chế độ non-demo, đặt `DEMO_MODE=false`, secret riêng, username Admin bootstrap và mật khẩu duy nhất ít nhất 12 ký tự:

```powershell
$env:DEMO_MODE = "false"
$env:SECRET_KEY = (py -c "import secrets; print(secrets.token_urlsafe(48))")
$env:INITIAL_ADMIN_USERNAME = "itadmin"
$securePassword = Read-Host "Initial Admin password (12+ characters)" -AsSecureString
$env:INITIAL_ADMIN_PASSWORD = [System.Net.NetworkCredential]::new("", $securePassword).Password
docker compose up --build -d
```

Nhập mật khẩu riêng tại prompt; không lưu secret vào Git hoặc gõ mật khẩu rõ vào lệnh trong shell dùng chung. Ứng dụng từ chối khởi động non-demo nếu DB còn hash mật khẩu demo mặc định; không đổi mode trên DB demo rồi kỳ vọng tự chuyển đổi. Prototype chưa có luồng đổi/reset mật khẩu.

## Cấu hình

| Biến | Mặc định | Ghi chú |
|---|---|---|
| `DEMO_MODE` | `false` | Mặc định trong code là `false` để an toàn. Cần gán tường minh `true` khi chạy demo local để tự tạo tài khoản mẫu trên DB mới rỗng. |
| `ALLOW_DEMO_CREDENTIALS` | `false` | CỜ NGOẠI LỆ THỬ NGHIỆM: Chỉ cho phép tài khoản demo khi chuyển đổi hoặc kiểm thử local ở chế độ non-demo; tuyệt đối tắt (`false`) trên production. |
| `SECRET_KEY` | Sinh ngẫu nhiên khi demo; bắt buộc non-demo | Đặt secret mạnh, ổn định và quản lý ngoài source control nếu muốn phiên JWT còn hiệu lực qua restart. |
| `DATABASE_URL` | Rỗng | PostgreSQL connection URI; khi rỗng, ứng dụng dùng SQLite tại `HELPDESK_DB_PATH`. Compose mặc định trỏ tới service PostgreSQL `postgres`. |
| `POSTGRES_PASSWORD` | Mật khẩu demo trong Compose | Mật khẩu service PostgreSQL của Compose; bắt buộc thay trước khi dùng ngoài máy demo. |
| `HELPDESK_DB_PATH` | `data/helpdesk.sqlite3` | Đường dẫn SQLite khi không cấu hình `DATABASE_URL`. |
| `HELPDESK_STORAGE_PATH` | `data` | Thư mục lưu attachment; Compose đặt trong named volume runtime. |
| `INITIAL_ADMIN_USERNAME` | Rỗng | Dùng bootstrap Admin khi tạo DB non-demo rỗng. |
| `INITIAL_ADMIN_PASSWORD` | Rỗng | Bootstrap password tối thiểu 12 ký tự và không trùng username. |
| `TOKEN_EXPIRE_MINUTES` | `60` | Thời hạn JWT; phải là số nguyên dương. |

PostgreSQL được khởi tạo lặp lại an toàn cho schema của prototype. Không có công cụ chuyển dữ liệu SQLite cũ sang PostgreSQL hoặc migration tổng quát cho cơ sở dữ liệu PostgreSQL production sẵn có; sao lưu/export và lên kế hoạch migration riêng trước khi chuyển backend. PostgreSQL volume, attachment và Knowledge Base là ba đơn vị persistence riêng, nên cần sao lưu nhất quán cả database **và** hai file volume. Repository chưa có chức năng backup/restore.

## Kiểm tra và chẩn đoán

```powershell
py -m ruff check app tests scripts
node --check app/static/app.js
node --check app/static/i18n.js
node tests/test_i18n.js
py -m compileall -q app tests scripts
py -m pytest --cov=app --cov-report=term-missing
py -m scripts.evaluate_rag
```

- `GET /health` trả lỗi khi database backend không sẵn sàng; xem log server/container và xác minh `DATABASE_URL`, kết nối PostgreSQL hoặc quyền ghi SQLite.
- Nếu thiếu module, xác nhận virtual environment đang hoạt động rồi cài `requirements.txt`.
- Nếu user bootstrap không xuất hiện, kiểm tra DB path thực tế, trạng thái `DEMO_MODE` và log khởi động; seed chỉ tạo tài khoản khi bảng user rỗng.
- Nếu retrieval không thấy tài liệu vừa nạp, xác nhận tệp Markdown hợp lệ; thử thao tác re-index của Admin.

## Giới hạn vận hành

SQLite và file storage cục bộ chỉ dành cho development/demo đơn máy. Compose cung cấp PostgreSQL persistent, nhưng cấu hình hiện tại vẫn là demo: chưa cấu hình HTTPS/reverse proxy, rate limiting, email/WebSocket notifications, task queue, object storage, malware scan, backup tự động, monitoring, HA, thử tải hoặc quy trình nâng cấp production. Không đưa dữ liệu ticket/người dùng thật vào môi trường này.


## AUD-09 — Render: attachment trên persistent disk

`render.yaml` hiện là cấu hình đề xuất **trả phí**: `starter`, một instance,
disk `opsmind-runtime` 1 GB mount tại `/app/runtime`, và
`HELPDESK_STORAGE_PATH=/app/runtime`. Attachment đi vào
`/app/runtime/attachments`; metadata vẫn dùng Neon qua `DATABASE_URL`.
`HELPDESK_DB_PATH` trên disk chỉ là đường SQLite dự phòng, không tự migration
Neon/SQLite. Phải kiểm tra DATABASE_URL trước triển khai.

Render mặc định dùng filesystem tạm; chỉ dữ liệu dưới mount path được giữ.
Disk cần dịch vụ trả phí, giới hạn một instance và làm deploy có gián đoạn.
Xem [Render disks](https://render.com/docs/disks) và
[Blueprint reference](https://render.com/docs/blueprint-spec).
Thay đổi repository chưa tạo disk, nâng gói hay triển khai cloud.

### Chuyển dữ liệu và nghiệm thu trước khi đóng AUD-09

1. Trước **mọi** thao tác gây restart/redeploy (kể cả nâng gói/gắn disk),
   tạm dừng upload và sao lưu attachment đang có từ instance còn sống cùng
   metadata DB tại cùng mốc. Giữ nguyên tên file UUID lưu trong metadata,
   không đổi sang tên hiển thị. Kiểm số lượng, kích thước và SHA-256.
   Nếu instance hiện tại không cho xuất file, phải giải quyết việc xuất trước;
   không redeploy để thử lấy lại file. File đã mất không thể tái tạo từ metadata.
2. Kiểm tra Blueprint bằng Render CLI/API chính thức, rà soát chi phí và lịch
   gián đoạn trước khi áp dụng. Không áp dụng trực tiếp vào production khi chưa
   có bản sao lưu đã kiểm tra và cửa sổ bảo trì.
3. Sau khi mount, kiểm tra đường storage và quyền ghi dưới đúng UID/GID
   `10001:10001` của Dockerfile bằng runtime shell. Chown trong image không
   chứng minh quyền trên volume được mount. Không đổi ứng dụng sang root để
   bỏ qua lỗi quyền. Disk không có ở build/pre-deploy, nên kiểm ở runtime.
4. Khôi phục file vào `/app/runtime/attachments`, giữ tên UUID, đối chiếu
   checksum và bản ghi DB. Chỉ mở lại upload sau khi kiểm tra hoàn tất.
5. Upload file giả qua API, ghi ticket/attachment ID và SHA-256. Download
   phải đúng bytes; kiểm quyền requester/agent/admin và ticket khác.
   Restart rồi redeploy **cùng disk**, đăng nhập lại, download ID cũ và so hash.
   Lưu bằng chứng mount, UID, timestamp, hash; không ghi secret/dữ liệu thật.
6. Sao lưu DB và file theo cùng mốc, giữ bản ngoài service và diễn tập restore
   vào môi trường cách ly. Snapshot disk không phải backup đồng bộ với Neon.
   Theo dõi dung lượng; 1 GB là cấu hình khởi đầu, chưa có quota/retention tự động.

Rollback code phải giữ disk, mount path và biến storage. Không detach/xóa disk
hoặc quay lại gói Free như một bước rollback. Nếu phục hồi dữ liệu, dừng ghi và
phục hồi DB + file theo cùng checkpoint đã kiểm tra. Chưa có migration/restore
tự động. Nếu cần nhiều instance hoặc giữ gói Free, cần thiết kế object storage;
cấu hình này chưa triển khai phương án đó.

Trạng thái: **IMPLEMENTED LOCAL; chờ Render validation, quyền volume thực và
kiểm tra restart/redeploy cloud**. Kiểm thử local không chứng minh độ bền disk Render.


## AUD-10 — kiểm chứng event loop

Chạy `python -m pytest tests/test_event_loop.py -q -s` từ repository.
Test khởi động Uvicorn một process/worker, không reload, cổng loopback ngẫu
nhiên; DB/storage/dữ liệu giả được cách ly trong pytest tmp. Client HTTP ở
process pytest riêng với process server. Không gọi LLM/email provider thật.
Mỗi ca giữ một thao tác đồng bộ chờ file release, gửi 8 HTTP health đồng thời
với timeout 1.5s và chỉ release sau khi nhận health; safety deadline tác vụ 8s.
Ghi p95 nearest-rank của 8 mẫu (chính là max); số mẫu nhỏ, không là benchmark tải.
Ca gồm generate_answer, DB list, PBKDF2 verify, notification, lưu KB file,
attachment metadata sau khi ghi file và xác thực DB trên async upload KB.
Test được pytest/CI thu thập tự động; Linux/CI chưa được xác nhận local.

LLM vẫn dùng timeout cấu hình `LLM_TIMEOUT_SECONDS` (mặc định 8s), SQLite
connection timeout 15s; không thay timeout hay thêm retry. Test giữ toàn bộ hàm
generate_answer, không đo provider thật. Cần đo lại staging với DB/provider
thật, nhiều request đồng thời, worker count và pool saturation trước khi chốt
p95/error budget production. PostgreSQL runtime và multi-worker còn chờ kiểm.


## AUD-11 — chuyển KB cũ sang nguồn DB

Upload Markdown không cần thư mục runbook có quyền ghi hoặc volume KB. Khi
DATABASE_URL là Neon, DB chứa nội dung và version; khi dùng SQLite, phải backup
file SQLite đúng quy trình nhất quán. Attachment vẫn cần disk theo AUD-09.
File runbook đóng gói chỉ dùng seed; API không import ngầm file thiếu DB.

Trước triển khai, giữ một bản DB nhất quán và bản sao các file KB cũ từ
instance còn sống, kèm checksum, nguồn, thời điểm và version code. Không
redeploy trước khi xuất file từ filesystem tạm. Giữ bản gốc để phục hồi;
không tự động xóa file hoặc sửa is_builtin/author hàng loạt.

1. Lập inventory slug/tên file, nội dung, checksum, DB status/author/is_builtin
   và versions. Phân biệt runbook gốc theo phiên bản repository đã dùng với
   tài liệu upload cũ; không suy đoán provenance chỉ từ vị trí thư mục.
2. File có bản ghi DB: DB là nguồn phục vụ. Nếu nội dung khác, review khác
   biệt rồi cập nhật qua editor để có version; không ghi đè bản published bằng
   bản file cũ. Helper cũ có thể thêm heading khi ghi file nên checksum file
   và raw content DB khác nhau không tự chứng minh tài liệu sai.
3. File không có bản ghi DB: API sẽ trả 404, kể cả reindex/delete. Sau khi
   duyệt nội dung, Admin nhập qua multipart (published) hoặc JSON editor ở
   trạng thái draft để review. Kiểm slug chuẩn hóa và trùng 409 trước khi
   chấp nhận mapping citation cũ/mới; không tự rename hoặc thêm hậu tố ngầm.
4. Bản ghi custom đã bị seed thành builtin, hoặc có tên trùng runbook gốc:
   giữ nguyên và đối chiếu bằng chứng trước khi sửa provenance bằng quy trình
   bảo trì có review. Bản vá không thể suy ra tác giả/thời điểm đã mất.
5. Kiểm list/get, version/author/is_builtin, truy vấn RAG, restart rồi kiểm lại.
   Khi xóa custom qua API, DB/version bị xóa, file cũ vẫn giữ offline và không
   xuất hiện lại qua GET. Chỉ dọn bản lưu cũ sau nghiệm thu backup/restore.

Rollback code phải xét lại việc bản cũ có thể phục vụ file lẻ; không dùng các
file chưa duyệt làm nguồn live. Nếu rollback dữ liệu, dừng ghi và phục hồi DB
theo checkpoint được kiểm tra. Chưa có migration/repair tự động, chưa chạy với
DB/file production. Kiểm local: `python -m pytest tests/test_knowledge_persistence.py -q`;
PostgreSQL còn hai case import/rollback chờ môi trường DATABASE_URL thử nghiệm.


## AUD-13 — vận hành outbox và đối soát notification

Upgrade thêm bảng notification_outbox/index bằng initializer idempotent; không
xóa dữ liệu cũ. Backup DB trước upgrade và kiểm quyền CREATE TABLE/INDEX trên
DB thử nghiệm. SQLite cần đường DB bền vững, Neon dùng DB hiện có. Outbox chỉ
có event từ phiên bản mới; không backfill ticket/SLA quá hạn lịch sử.

1. Trong staging, đặt target thử nghiệm Telegram/Discord và tạo ticket/chuyển
   cấp. Kiểm hai row chung event_id, snapshot đúng thời điểm, trạng thái tiến
   triển; accepted không là người đọc xác nhận. Không thử bằng dữ liệu thật.
2. Khi lỗi provider, xem admin GET /admin/notifications/deliveries?status=failed.
   Dùng limit tối đa 100 và before_id = id cuối trang để duyệt tiếp. Xem attempts,
   max_attempts, next_attempt_at, last_error (Unix seconds UTC). Các lỗi provider
   kể cả 4xx hiện được retry hữu hạn như nhau; sửa cấu hình trước retry thủ công.
3. not_configured không tự gửi backlog khi mới đặt kênh. config_changed chặn
   retarget sau đổi token/target. Review người nhận, nội dung snapshot và event
   trước POST /admin/notifications/deliveries/{id}/retry bằng admin; endpoint này
   cấp thêm 3 claim, ghi audit actor, không reset counter tổng. Không sửa SQL
   trực tiếp để bỏ fence hoặc đặt accepted khi chưa có bằng chứng.
4. Với lease_expired_delivery_unknown hoặc crash sau remote send: tìm event UUID
   trong kênh trước khi retry vì có thể đã gửi. Chưa lưu receipt ID của provider;
   đối soát cần bằng chứng ở kênh. Accepted không tự retry, tránh gửi lại kênh
   đã chấp nhận khi kênh khác lỗi. Theo dõi backlog pending/failed và đĩa DB.
5. Dừng/restart worker thử nghiệm sau claim, kiểm lease hết rồi recover. Kiểm
   hai worker chỉ có một claim còn hiệu lực, ack cũ không đổi trạng thái mới;
   kiểm 3 case PostgreSQL trong CI/staging. Local chưa có PostgreSQL/Docker.

Không có retention/purge outbox tự động hay monitoring/alert backlog ngoài
endpoint. Payload chứa snapshot ticket; phân quyền/retention/backup cần đưa
vào kế hoạch vận hành trước pilot. Soft archive ticket không hủy event đã xếp;
xóa vật lý ticket cascade outbox. Không có quy trình recall remote notification.
Timeout 10s là socket timeout của adapter, không chứng minh hard deadline tổng
gồm DNS/response streaming. Chưa benchmark saturation của threadpool dùng chung.

Rollback: dừng worker trước khi đổi code; giữ bảng và backup cùng DB ticket.
Không drop outbox để xử lý backlog. Bản cũ gửi trực tiếp và không enqueue nên
giai đoạn rollback có khoảng trống outbox; review event trước khi bật lại worker
để tránh gửi lặp. Chưa có exactly-once hay đồng bộ receipt provider tự động.
Chưa deploy, gửi provider thật hoặc diễn tập restore/cloud trong phiên local.


## AUD-15 — nâng cấp và vận hành thu hồi JWT

Backup DB trước upgrade. Migration additive thêm users.session_epoch và khởi
tạo giá trị cho tài khoản cũ; không log/export JWT, signing key hoặc nonce.
Với DB cũ, chạy một initializer và kiểm migration thành công trước khi mở
nhiều worker; chưa chứng minh concurrent ALTER TABLE trên SQLite legacy.
Tất cả JWT trước bản vá thiếu claim phải đăng nhập lại. Dừng/drain worker cũ
và rollout đồng bộ backend/frontend v9; không chạy lẫn worker cũ bỏ qua epoch
với worker mới. Reload tab cũ để nút logout gọi endpoint server. Client cũ chỉ
xóa localStorage không tự có semantics logout mới nếu tiếp tục dùng bundle cũ.

Staging cần kiểm cùng DB và SECRET_KEY ổn định: login hai client, logout một,
token đã chép ở client khác phải 401; login mới hợp lệ. Kiểm disable-enable và
role downgrade-upgrade không hồi sinh JWT, forced-password logout, no-op/profile
không ngắt phiên. Restart worker rồi kiểm token revoked vẫn 401. Bốn case PG
đã thêm (hai account cycle, concurrent CAS/idempotent init, atomic rollback)
chưa chạy local. Token cũ phải kiểm qua endpoint có auth; /health không có auth.

Logout DB lỗi/timeout không được coi là revoke thành công. Kiểm kết nối DB,
đăng nhập rồi logout lại khi có kết nối; nonce có thể đã rotate nếu response
mất sau commit, nên UI báo chưa xác nhận. Logout không reset password, thu hồi
reset link/email hay tắt tài khoản. Không có endpoint admin revoke-all riêng;
quản trị viên dùng khóa tài khoản/đổi mật khẩu theo policy để thu hồi khi cần.

Rollback về backend cũ bỏ qua epoch sẽ làm mất bảo đảm thu hồi, có thể nhận
lại JWT cùng signing key: không dùng rollback đó như một cách phục hồi auth.
Nếu restore DB snapshot cũ, epoch trước khi revoke có thể quay lại; phải phối
hợp xoay SECRET_KEY trên mọi worker và buộc đăng nhập lại. Không restore bảng
users riêng khỏi password/reset-token state mà không có kế hoạch nhất quán.
Chưa deploy/rotate key/account production hoặc diễn tập restore trong phiên local.
