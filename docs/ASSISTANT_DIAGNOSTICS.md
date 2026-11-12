# Trợ lý chẩn đoán — thay đổi local 28/10/2026

## Phạm vi và trạng thái

Triển khai cục bộ theo đặc tả Q1–Q17, hai nhóm mạng dây và máy in Offline. Chưa push/deploy. Chưa nghiệm thu 30 tình huống độc lập. Không gọi kết quả này là production-ready.

## Luồng API và UI

`POST /rag/ask` giữ `question` và `session_id`; nhận thêm `fact_answers` (tối đa 3 cặp khóa/giá trị) và `action`: `confirm_switch`, `continue_incident`, `confirm_resolved`, `still_failing`.

Server lấy vai trò từ phiên đăng nhập. Dữ kiện hợp lệ theo nhóm sự cố có value/source/at. UI cung cấp các lựa chọn có nhãn và Không biết; văn bản không được suy diễn thành xác nhận hết lỗi. RESOLVED chỉ từ action xác nhận khi đã có bước CHECK_RESULT; feedback hữu ích vẫn độc lập. Dữ kiện có cấu trúc được hiển thị trong câu hỏi lựa chọn, không tự lấy từ mọi câu văn tự do; người dùng xác nhận qua biểu mẫu.

Chủ đề mới được giữ pending; dữ kiện hiện tại không thay đổi cho tới confirm_switch. continue_incident bỏ đề nghị đổi sự cố. Chủ đề Outlook/VPN/tài khoản ngoài hai nhóm đi IN_SCOPE_NO_SOURCE. Phiên mới tạo sự cố riêng. Session API kiểm quyền sở hữu. Câu ngoài phạm vi không có thẻ ưu tiên hoặc chuyển IT.

Nguồn `data/assistant_runbooks.json` do người vận hành kiểm soát; mặc định **rỗng**, không có phê duyệt giả. Mỗi entry cần id/topic/version/status/reviewer/reviewed_at/source/source_version/section; conditions phải khớp toàn bộ dữ kiện; 1–3 steps có id/instruction/expected/stop/roles. Chỉ `status=approved`, đủ metadata, đúng điều kiện và đúng vai trò mới chạy GUIDE → CHECK_RESULT. Admin ứng dụng không tự có quyền của agent. Không nhận catalogue hoặc role từ câu chat.

Phê duyệt là bước ngoài code: chuyên gia phải đối chiếu nguồn, model/OS, điều kiện dừng, chính sách tổ chức và phiên bản. Việc có schema và test fixture approved không phải bằng chứng đã có phê duyệt thật. Các dấu hiệu nhiều người bị/unknown/lỗi bảng điều khiển thiết bị được bàn giao an toàn. Không can thiệp thiết bị thật trong test.

`handoff` chứa title/description/unknowns; mô tả gồm câu hỏi ban đầu, dữ kiện người dùng xác nhận, thời điểm, unknowns, bước gợi ý, kết quả xác nhận, nguồn và lý do. Tác động/khẩn cấp còn chưa rõ được ghi rõ trong bản nháp để user bổ sung, ưu tiên tạm thời là medium. Preview cho sửa title/description và cảnh báo không nhập mật khẩu/OTP. Cảnh báo không bảo đảm tự phát hiện mọi dữ liệu nhạy cảm.

## Gửi ticket và khôi phục timeout

`POST /tickets` nhận request_key tùy chọn (16–64 chữ/số/gạch nối). Khóa scoped theo requester. Một transaction ghi claim, payload cố định, ticket, audit và outbox; retry cùng payload trả cùng ID; key khác payload trả 409. Key cũ không có snapshot payload bị từ chối 409 thay vì nhận nhầm.

`GET /ticket-requests/{request_key}` chỉ trả ticket của requester hiện tại, 404 nếu chưa xác nhận. UI giữ bản nháp trong lượt chat khi lỗi, nút thử lại tra key trước POST; chỉ 404 mới gửi lại cùng key. Lỗi tra cứu khác không tự POST. Nháp hiện ở bộ nhớ trang, **chưa bền qua reload/trình duyệt đóng**. Receipt mở GET /tickets/{id}, không tìm theo tiêu đề; tiếp tục dùng kiểm quyền ticket hiện có. Không khẳng định IT đã tiếp nhận chỉ từ receipt tạo ticket.

## Dữ liệu và migration

initialize_store thêm bảng assistant_incidents (context JSON theo chat_session), ticket_requests (claim key → ticket), ticket_request_payloads (snapshot payload theo key). CREATE IF NOT EXISTS dùng cho SQLite/PostgreSQL. Không sửa dữ liệu ticket/KB hoặc chuẩn hash benchmark. Các FK cascade dọn dữ liệu khi session/ticket bị xóa. Context được ghi cùng transaction chat exchange. Không chạy migration trên DB cloud trong phiên này. Cần backup và xác minh migration trên PostgreSQL test trước phát hành; cập nhật đồng thời được kiểm soát bằng revision và compare-and-update; cần xác minh thêm trên PostgreSQL.

## Kiểm chứng và gate còn mở

- Test API dùng SQLite riêng với dữ liệu giả; kiểm phủ định/thành công quá khứ, pending topic, quyền session, nguồn đã/chưa duyệt, quyền step, receipt lookup, conflict, retry đồng thời.
- Test JS hành vi dùng DOM giả và API boundary; kiểm preview chưa POST, bản nháp sửa được, timeout lookup không POST trùng, đúng ticket ID và action xác nhận. Không thay thế browser E2E.
- Test PostgreSQL chỉ chạy khi DATABASE_URL trỏ DB test; không dùng DB production. Chưa có môi trường PostgreSQL ở local này.
- Catalogue thật được chuyên gia duyệt, browser E2E, PostgreSQL runtime và 30 ca độc lập vẫn là gate chưa có bằng chứng.
- Lỗi hash dataset LF/CRLF đã biết nằm ngoài phạm vi; không thay hash để làm xanh test.

Nguồn yêu cầu: đặc tả OpsMind v1 ngày 28/10/2026 đã được người dùng duyệt; review local so với 0dd9def. Không coi các ticket bị gate ngoài là hoàn thành nghiệm thu.

### Kiểm soát lượt cũ và khôi phục lịch sử

API yêu cầu expected_revision cho action/fact_answers/step_results. Context revision tăng theo lượt policy; ghi context dùng compare-and-update, xung đột trả 409 thay vì ghi đè. UI gắn controls vào diagnosticTurn/session; thao tác lượt cũ không gửi request. Lịch sử trả diagnostic snapshot (revision, questions, pending, steps, handoff) để tái tạo điều khiển hiện tại; không cần hỏi lại chỉ để khôi phục nút.

step_results nhận từng step ID hiện hành với not_attempted/attempted_success/attempted_failure, có phân biệt attempted_steps và suggested_only_steps. Xác nhận chức năng hoạt động không tự nhận mọi bước đã thực hiện. Metadata trích dẫn phân biệt source_version và phiên bản runbook.

### Dừng an toàn và giới hạn nhận diện

Dấu hiệu mã độc/lộ mật khẩu hoặc cháy/khói được ưu tiên trước nhóm máy in/mạng. Khi xuất hiện giữa một sự cố, UI ẩn bước cũ và không cho tiếp tục/xác nhận hết lỗi trước khi xác nhận sự cố mới để bàn giao. Context cũ không trộn vào ticket mới. Nhận diện bằng từ/cụm từ vẫn có giới hạn ngôn ngữ; không phải bộ phân loại an toàn đã được nghiệm thu.

Mọi câu trả lời retrieval có tài liệu nhưng chưa qua catalogue được trả IN_SCOPE_NO_SOURCE, không phát hướng dẫn legacy. Điều này áp dụng cả các nhóm ngoài hai quy trình đang triển khai; chức năng truy xuất/KB vẫn được kiểm thử riêng. Kết quả từng bước được hydrate khi phục hồi controls.

## Kết quả kiểm chứng cuối — 28/10/2026

- Python full suite: **326 passed, 42 skipped, 1 failed**, 98.91s. Failure duy nhất: `tests/test_rag_dataset.py::test_evaluation_datasets_provenance_and_frozen_hash`.
- Hai CSV evaluation giống byte-for-byte với HEAD baseline; hash CRLF khớp frozen hashes, checkout LF không khớp. Không sửa CSV, expected hash hay bỏ qua assertion.
- JavaScript: **15/15 passed** (`node --test tests/*.js`), gồm kiểm tra hành vi preview/recovery, ticket ID, explicit outcome và giữ step result.
- `ruff check app tests`, `node --check app/static/app.js`, `git diff --check`: đạt. Probe catalogue `runbooks: null`: bàn giao an toàn, không 500.
- Review Spec/Standards tập trung: các finding đã nêu được xử lý, không còn finding vật chất mở trong phạm vi review. Đây không phải nghiệm thu độc lập hay kiểm thử Render.
- Chưa push, merge hoặc deploy. Catalogue thật, PostgreSQL runtime, browser E2E và 30 ca độc lập vẫn chưa hoàn thành.

## Bản vá sau review — 29/10/2026

Hai lỗi có test API tái hiện đỏ trước bản vá: (1) lời người dùng bổ sung không nằm trong incident context nên preview/ticket mất thông tin; (2) trạng thái bàn giao/hết lỗi rơi tiếp vào chọn catalogue, phát lại cùng bước. Prompt đổi chủ đề còn ghi đè trạng thái trước đó.

Bản vá lưu lời bổ sung theo sự cố với nguồn user và thời điểm, ghi rõ chưa xác minh; không tự biến chúng thành facts, chẩn đoán hay mức ưu tiên. Preview tối đa 5.000 ký tự; nếu phải rút gọn, đánh dấu và giữ phần bổ sung gần nhất, toàn bộ notes vẫn ở incident context/hội thoại. Các lượt có action hoặc fact_answers không bị lưu nhầm nhãn điều khiển thành ghi chú tự do. Xác nhận đổi sự cố tạo context riêng, không chuyển notes cũ.

HANDOFF_PREVIEW và RESOLVED giữ trạng thái khi user gửi thêm lời; không tự chọn lại bước. Tiếp tục sau prompt đổi chủ đề khôi phục previous_state (kể cả CHECK_RESULT). Context pending cũ chưa có previous_state dùng CLARIFY để không tự suy ra trạng thái đã mất.

Lệnh tái hiện: `python -m pytest tests/test_api.py -k bug_regression -q`. Trước sửa: 3 failed/2.36s; sau sửa và mở rộng: 5 passed/5.82s. Catalogue approved trong test là fixture tổng hợp, không phải phê duyệt kỹ thuật thật. Không thêm dependency, không chạy migration cloud hay can thiệp thiết bị.

Review tiếp theo phát hiện hai nhánh bổ sung: safety return trước ghi notes và terminal return trước lưu sửa facts. Đã viết thêm 3 test API, xác nhận đỏ (3 failed/2.85s), rồi sửa thứ tự xử lý: ghi notes trước safety stop; xác thực/lưu fact_answers trước terminal guard. Sự cố vẫn giữ safety_stop/HANDOFF_PREVIEW, không chọn lại hướng dẫn. Tổng 8 test hồi quy đạt trong 4.34s. Standards/Spec focused recheck không còn finding vật chất trong phạm vi bản vá.

Full suite ở bản vá đầu (trước 3 test/sửa thứ tự cuối): 331 passed, 42 skipped, 1 failed trong 206.65s; failure duy nhất vẫn là frozen dataset hash LF/CRLF baseline. Lệnh `pytest tests/test_api.py -q --disable-warnings` trên bản vá cuối kết thúc với exit code 0; log chỉ có tiến độ, không có dòng tổng kết nên không ghi thêm số test API. JavaScript 15/15 và ruff app/tests/scripts đạt; không có debug instrumentation.

## Áp dụng retro và lưu nhánh — 29/10/2026

Nhánh GitHub `fix/assistant-spec-2026-10-29` lưu snapshot file-tree của hai commit local 4b80dd6/180ec9d; commit GitHub đầu tiên 5f12186 có tree SHA f11509d673a5e84a85be51d222a3a8475acb0485, giống commit local 180ec9d. GitHub connector tạo commit mới nên SHA commit khác, nội dung file không khác. Bản [đặc tả gốc](ASSISTANT_SPEC_V1.md) được lưu cùng repository để phiên sau không phụ thuộc đường dẫn tạm.

Workflow CI chạy `node --test tests/*.js` để nhận cả test mới. Pytest xuất JUnit cho Python và PostgreSQL; suite name và tên artifact `test-evidence-<github.sha>` gắn với commit checkout. Upload dùng `always()` để giữ báo cáo khi test thất bại; báo cáo PostgreSQL chỉ có khi bước đó đã chạy, không coi file vắng là test đạt. Điều kiện trigger hiện có vẫn là push main/develop hoặc pull request: tạo nhánh backup đơn thuần chưa chứng minh CI đã chạy.

Bốn ca API bổ sung kiểm đổi chủ đề lặp lại rồi reload/tiếp tục ở CHECK_RESULT, HANDOFF_PREVIEW, RESOLVED, cùng tách báo cáo giữa hai phiên mới: 4 passed/3.29s. Đây là mở rộng hồi quy cho hành vi hiện có, không phải phê duyệt chuyên môn hay nghiệm thu độc lập.

Kiểm chứng bản retro cuối (29/10/2026): JUnit suite `local-180ec9d-with-retro-changes` xác nhận 381 test: **338 passed, 42 skipped, 1 failed, 0 errors**, 193.536s. Failure duy nhất là `tests.test_rag_dataset.test_evaluation_datasets_provenance_and_frozen_hash`, cùng mismatch LF/CRLF baseline. Không sửa CSV hoặc expected hash. JavaScript **15/15 passed**, ruff app/tests/scripts và diff check đạt; YAML workflow parse thành công. Full suite có coverage và JUnit; số lượng lấy từ XML hoàn chỉnh vì stdout log bị thiếu phần tổng kết. Review Standards/Spec không còn finding vật chất trong phạm vi retro. PostgreSQL runtime/browser E2E/catalogue chuyên gia/30 ca nghiệm thu độc lập vẫn chưa hoàn thành. CI GitHub chưa chạy trên nhánh backup; kết quả này thuộc môi trường local.

## Lỗi phân loại màn hình sọc thành BitLocker — 29/10/2026

Tái hiện đúng hai lượt trong ảnh: hỏi thời tiết, rồi “Hiện màn hình phụ tôi đang bị sọc, yêu cầu khắc phục”. Với user và admin, API trả IN_SCOPE_NO_SOURCE nhưng còn category_reason/navi_category/escalation_reason từ BitLocker. Nguyên nhân: nhánh policy xóa matches/sources và thay câu trả lời nhưng chỉ thay resolution_scope, giữ phần triage của retrieval đã bị từ chối.

Bản vá tạo lại toàn bộ triage từ incident policy, dùng chung cho response và snapshot; nhãn general/medium là tạm thời, cần IT xác minh, không phải chẩn đoán màn hình. UI admin chỉ nhắc đối chiếu nguồn khi grounded; nếu chưa có hướng dẫn thì yêu cầu IT kiểm tra thêm. Không thêm quy trình sửa màn hình hoặc thay thuật toán retrieval trong bản vá này.

Hai test API dùng dữ liệu KB fixture hiện có, không mock retrieval: trước sửa 2 failed/2.25s; sau sửa 2 passed/1.98s. Chưa xác minh UI thực tế trên Render hoặc triển khai bản vá lên Render.

Hồi quy bản vá: toàn bộ API 99 passed, 0 failed/0 errors theo JUnit (65.720s); JavaScript 15/15 passed; ruff app/tests/scripts và diff check đạt. Không chạy lại full suite ngoài API trong lượt này.

## Issue #12 — giữ policy khi câu hỏi CNTT chứa từ khóa ngoài phạm vi — 02/11/2026

Câu “Máy in Offline không in được tài liệu dự báo thời tiết” bị router đánh dấu OUT_OF_SCOPE theo substring, trong khi retrieval vẫn coi là yêu cầu CNTT. Router bỏ policy sau khi truy xuất nên còn câu trả lời/trích đoạn cũ, mất câu hỏi chẩn đoán. Cùng lỗi xảy ra với mạng, lượt tiếp nối và dấu hiệu cháy/virus có kèm từ khóa thời tiết.

Bản vá dùng `is_out_of_scope()` chung với retrieval để xác nhận cụm ngoài phạm vi có thực sự loại yêu cầu CNTT hay không. Vẫn yêu cầu có cụm ngoài phạm vi rõ ràng trước khi bỏ ngữ cảnh, để câu trả lời ngắn và dữ kiện có cấu trúc tiếp tục thuộc sự cố đang xử lý. Không thay catalogue, quyền theo vai trò hoặc thuật toán truy xuất.

Chín ca hồi quy API dùng SQLite và catalogue rỗng: trước sửa 6 failed/3 passed; sau sửa 9 passed. Ca tái hiện ba câu hỏi ban đầu cũng đạt sau sửa: câu máy in thường và câu máy in kèm thời tiết trả CLARIFY với ba câu hỏi, không sources/matches; câu thuần thời tiết vẫn OUT_OF_SCOPE. Đây là bằng chứng local với dependency khóa theo repository, không xác nhận triển khai Render, duyệt chuyên môn runbook hoặc nghiệm thu độc lập.

Hồi quy toàn bộ trên Windows/Python 3.11.17: **373 passed, 43 skipped, 0 failures/errors**, coverage **89%**, 367.78s. Skip gồm 41 ca PostgreSQL chưa có DATABASE_URL test, một ca cần Docker CLI và một ca cần quyền symlink. JavaScript **15/15**, ruff, compileall, kiểm tra cú pháp JS và diff check đạt. Retrieval giữ Hit@3 28/28 ở dev, 29/30 ở tập hồi quy đóng băng; H03 vẫn sai. Các số retrieval không đo faithfulness hoặc chất lượng câu trả lời. Chưa push/deploy hoặc chạy browser E2E trong lượt sửa này.

### Tái lập bằng chứng Issue #12

Chạy từ root repository bằng Python của venv sạch đã cài `requirements.txt` với `--require-hashes`. Lần kiểm chứng dùng Python 3.11.17 trên Windows, SQLite scratch và catalogue rỗng trong fixture. Các lệnh tương đương dưới đây tái lập nhóm kiểm thử đã ghi; đây không phải số liệu của một lượt chạy mới. Biến `HELPDESK_DB_PATH` trỏ tới DB mới dành riêng cho kiểm thử, không dùng DB thật.

```powershell
$env:DATABASE_URL = ''
$env:DEMO_MODE = 'true'
$env:ENABLE_LLM_GENERATION = 'false'
$env:EMAIL_PROVIDER = 'console'
$env:SMTP_ENABLED = 'false'
$env:HELPDESK_DB_PATH = Join-Path (Get-Location) 'data/issue12-scratch.sqlite3'

python -m pytest tests/test_api.py -k 'incidental_oos_phrase or pure_oos_phrase' -q --tb=short
python -m pytest --cov=app --cov-report=term-missing --cov-report=xml --junitxml=pytest-results.xml -q --tb=short
python -m ruff check app tests scripts
python -m compileall -q app tests scripts
node --check app/static/app.js
node --check app/static/i18n.js
node --test tests/test_*.js
python -m scripts.evaluate_rag
git diff --check
```

Nhóm test mới trên commit gốc `67a525e` (chỉ thêm test, chưa sửa router) cho 6 failed/3 passed; cùng lệnh sau bản sửa `1052aa0` cho 9 passed.

### Bổ sung theo góp ý review: kiểm thử trên cây tích hợp và đối chiếu tiêu chí — 12/11/2026

Cây kiểm thử là nhánh PR sau khi gộp `main` `d610a71` (`main` là tổ tiên trực tiếp của head; không còn commit nào của `main` chưa tích hợp). Khi đối chiếu tiêu chí 3 của Issue #12, phát hiện câu thuần thời tiết vẫn trả `triage.priority`, `priority_label`, `requires_confirmation` và `escalation_reason` “cần kỹ thuật viên IT tiếp nhận”, trái R06/D10 của [đặc tả](ASSISTANT_SPEC_V1.md). Giao diện không hiện nút chuyển IT cho OUT_OF_SCOPE, nhưng hợp đồng API vẫn chứa tín hiệu phân luồng IT. Bản sửa chỉ giữ `category: general` và `resolution_scope: OUT_OF_SCOPE` cho phản hồi ngoài phạm vi; thêm test khẳng định router và retrieval thống nhất trên ba câu của Issue.

Lệnh nhóm hồi quy: `python -m pytest tests/test_api.py -k 'incidental_oos or pure_oos_phrase or scope_decisions_agree' -q`. Trên mã ứng dụng của `main` `d610a71` với test mới: **8 failed/4 passed**; sau sửa: **12 passed**. Full suite trên cây tích hợp (macOS, Python 3.11.18, venv sạch cài `--require-hashes`, SQLite tạm, LLM tắt): **389 passed, 52 skipped**, coverage **90%**; ruff, compileall và `scripts.evaluate_rag` đạt (dev Hit@3 100%, holdout Hit@1/Hit@3 96,7%, MRR@3 0,967; H03 vẫn sai). Skip gồm ca PostgreSQL không có `DATABASE_URL` test và ca cần Docker; lượt local này không có Node nên kiểm tra JavaScript dựa vào CI.

| Tiêu chí Issue #12 | Bằng chứng | Kết quả |
| --- | --- | --- |
| Máy in kèm từ thời tiết giữ CLARIFY, tối đa 3 câu hỏi | `test_incidental_oos_phrase_keeps_diagnostic_gate` | Đạt |
| Catalogue rỗng không lộ sources/matches lúc hỏi làm rõ | cùng test, fixture `empty_diagnostic_catalogue` | Đạt |
| Câu thuần thời tiết OUT_OF_SCOPE, không nội dung truy xuất hoặc điều khiển leo thang IT | `test_pure_oos_phrase_has_no_retrieval_content`, `test_rag_refuses_questions_without_relevant_knowledge` | Đạt sau bổ sung lượt này |
| Router và retrieval thống nhất | `test_router_and_retrieval_scope_decisions_agree` | Đạt |
| Hồi quy API: fail trước, pass sau | 8 failed/4 passed → 12 passed | Đạt |
| Approval, vai trò, revision, safety stop không hồi quy | full suite 389 passed | Đạt local; cần CI xác nhận trên head mới | Full suite đã xuất JUnit và coverage XML; bộ số trên lấy từ log/XML hoàn chỉnh. Bản chạy local dùng thư mục pytest riêng qua `--basetemp` và lưu log ở ngoài checkout; tên thư mục scratch không quyết định hành vi. Không commit DB, log hoặc XML phát sinh vào repository. Các backend và công cụ khác có thể làm thay đổi số skip; phải ghi lại lý do của từng lượt thay vì tái sử dụng số liệu trên.
