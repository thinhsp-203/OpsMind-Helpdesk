# Ma trận truy vết yêu cầu và kiểm thử (Test Traceability Matrix)

### Bổ sung regression AUD-22 (21/10/2026, local)

- Khắc phục nguy cơ lộ thông tin bảo mật (Secret Leak) trong `scripts/verify_neon.py`: chuẩn hóa `sanitize_database_url`, thay thế việc in chuỗi `database_url` thô ở cuối script bằng chuỗi đã che giấu mật khẩu (`:***@`).
- Phân định rõ ràng giữa Safe Read-Only Check (mặc định, chỉ dùng `SELECT` kiểm tra handshake, version và bảng CSDL) và Write/Mutation Check (chỉ kích hoạt khi có cờ tường minh `--write` hoặc `--crud-test`).
- Loại bỏ việc gán `os.environ["DATABASE_URL"]` và import `app.store` ở cấp module, ngăn chặn hành vi tự động thực thi DDL/seeding khi import script.
- Bổ sung bộ kiểm thử `tests/test_aud22_neon_secret_leak.py` (4 ca test pass 100%).

### Bổ sung regression AUD-21 (21/10/2026, local)

- Đính chính toàn bộ ma trận truy vết yêu cầu: loại bỏ các hàm không tồn tại (thay thế bằng `retrieve_relevant_context` trong `app/rag.py`, `buildHandoffDescription` và `addTicketHandoff` trong `app/static/app.js`).
- Cập nhật đúng các file router thực tế (`app/routers/{auth, tickets, knowledge, rag, admin, analytics}.py`) thay vì trỏ nhầm về `app/main.py`.
- Phân định rõ ràng trạng thái nghiệm thu: `API Verified (Pytest Automated)` vs `API Verified / UI Smoke (Chờ Browser E2E CI theo TD-03)`, loại bỏ việc tuyên bố cào bằng "Đạt 100%".
- Mở lại TD-09 (benchmark TestClient 35 RPS RAG < 50 RPS), TD-04 (thiếu centralized audit log cho user changes), TD-05 (frozen benchmark gate vs independent blinded holdout).
- Cập nhật `test_html_escaping_in_email_dispatch` trong `tests/test_api.py` kiểm tra trực tiếp mã sản phẩm `app.email_sender` (`_send_via_resend`, `_send_via_brevo`) thay vì chỉ kiểm tra `html.escape` của stdlib.
- Đồng bộ `docs/DEPLOYMENT.md` với mã nguồn `app/config.py`: xác nhận mặc định an toàn `DEMO_MODE=false`.
- Bổ sung bộ kiểm thử truy vết và chất lượng bằng chứng `tests/test_aud21_traceability_and_evidence.py` (4 ca test pass 100%).

**Dự án:** OpsMind Helpdesk — Hệ thống Quản trị Sự cố CNTT & Trợ lý Tra cứu Tri thức RAG  
**Phạm vi:** Trạng thái mã nguồn thực tế trong repository  
**Phiên bản:** 2.0  
**Ngày cập nhật:** 14/10/2026  

### Bổ sung regression AUD-08 (21/10/2026, local)

- `tests/test_api.py::test_knowledge_changes_reach_an_independent_warm_reader`: sáu trường hợp edit/archive/reject/restore/delete/publish qua API process cha; process con đã warm tiếp tục sống và không nhận lệnh clear cache, đọc đúng kết quả sau commit.
- `test_warm_retrieval_cache_fails_closed_on_store_error`: API đã warm nhưng lỗi truy vấn KB vẫn trả 503, không lộ lỗi giả, không ghi thêm chat; phục hồi không clear cache thủ công.
- Cả 7 ca FAIL trước sửa. Sau sửa nhóm RAG/KB 29 passed, 1 symlink skipped; riêng 7 ca vẫn PASS sau khi chuyển process fixture vào `tests/conftest.py` để chia sẻ với PostgreSQL.
- `tests/test_postgres.py::test_postgres_kb_changes_reach_independent_warm_reader`: thêm sáu trường hợp store mutation và process đọc độc lập dùng PostgreSQL cho CI; local chưa có DB nên skip. Không suy kết quả SQLite thành PostgreSQL PASS.
- RAG evaluator dev/holdout đạt các gate, holdout Hit@1 23/30, Hit@3 30/30, MRR@3 0.878. Không phải phép đo tải hoặc answer quality. Không khẳng định request đã đọc trước commit bị thu hồi.

### Bổ sung regression AUD-07 (21/10/2026, local)

- `tests/test_password_reset.py::test_atomic_reset_rolls_back_token_and_password_on_failure`: hai trigger SQLite giả lập lỗi ghi password và lỗi thu hồi link còn lại; token, hash/epoch/force flag cùng rollback, link dùng lại được sau khi bỏ lỗi.
- `test_concurrent_reset_operations_have_one_winner`: hai connection/luồng cùng reset, cùng consume hoặc reset trong lúc cấp link; chạy ở cả DELETE và WAL. Chỉ một reset/consume thành công với một token, hash cuối cùng thuộc yêu cầu thắng; link cấp đồng thời vẫn dùng được theo thứ tự serialize.
- Trước sửa cả 8 ca FAIL, quan sát được hai yêu cầu cùng thành công với một token và token bị consume dù ghi password lỗi. Sau sửa nhóm password-reset/store 52 passed.
- `tests/test_postgres.py` thêm ba ca concurrency và một ca trigger rollback tương ứng để CI kiểm nhánh khóa hàng PostgreSQL; chưa chạy local vì thiếu dịch vụ DB. Không dùng kết quả SQLite để khẳng định PostgreSQL đã PASS.
- Không phải load test hoặc kiểm chứng mọi interleaving/mọi process; AUD-15 JWT và race địa chỉ nhận email ngoài transaction vẫn cần xử lý riêng.

### Bổ sung regression AUD-06 (21/10/2026, local)

- `test_old_reset_link_is_revoked_after_password_change` trong `tests/test_password_reset.py`: ba đường đổi mật khẩu (self/API Admin/store), JWT cũ bị từ chối, link reset cũ trả 400, token tài khoản khác còn hợp lệ, token mới dùng được một lần.
- `test_old_reset_link_is_revoked_after_security_profile_change`: đổi email qua profile/Admin và khóa rồi mở khóa tài khoản không làm link cũ có hiệu lực trở lại.
- `test_reset_link_remains_valid_after_non_security_profile_update`: không thu hồi nhầm khi đổi tên, cùng email khác hoa/thường hoặc active không đổi.
- `test_legacy_unused_reset_link_before_password_epoch_is_rejected`: token chưa used còn trong DB nhưng được tạo trước mốc đổi mật khẩu bị từ chối; token mới sau mốc đó vẫn dùng được. Regression bổ sung FAIL trước khi thêm kiểm tra mốc thời gian.
- `test_security_update_rolls_back_when_reset_link_revocation_fails`: SQLite trigger giả lập lỗi thu hồi; ba trường hợp password/email/disable rollback toàn bộ thay đổi tài khoản.
- `tests/test_postgres.py::test_postgres_reset_links_are_revoked_on_security_updates`: thêm gate cho PostgreSQL trong CI, chưa chạy local do không có dịch vụ DB.
- Trước sửa: 9 regression thất bại, 3 ca giữ hành vi hợp lệ pass; regression token lịch sử bổ sung cũng FAIL trước khi thêm guard mốc thời gian. Sau sửa cuối: nhóm password-reset/store 44 passed. Không coi các test này là chứng minh chống race của AUD-07 hoặc thu hồi JWT sau disable/enable của AUD-15.

### Bổ sung regression AUD-05 (21/10/2026, local)

- `tests/test_api.py::test_rag_does_not_resurrect_files_after_last_document_is_archived`: archive qua API đến tài liệu published cuối cùng, RAG đang có index không đọc lại filesystem; KB user rỗng, chi tiết archived trả 404; publish lại thì phục vụ đúng nội dung DB mới.
- `tests/test_api.py::test_rag_database_failure_returns_503_and_recovers_without_cache_clear`: lỗi đọc kho tri thức được kiểm soát bằng HTTP 503, không lộ chi tiết lỗi DB, không lưu chat exchange, phục hồi lần gọi sau mà không clear cache thủ công.
- Hai regression FAIL trước sửa và PASS sau sửa trên SQLite tổng hợp. Nhóm RAG/KB 22 passed, 1 symlink skipped. Lệnh: `python -m pytest tests/test_api.py -k "resurrect_files or database_failure_returns or knowledge or rag" -q`.
- Đây là kiểm chứng local cho AUD-05; số liệu/tuyên bố tổng hợp lịch sử ở các phần bên dưới không thay thế bằng chứng CI/deploy hiện tại. Cache nhiều worker và PostgreSQL vẫn cần kiểm chứng riêng.

---

- AUD-19: Bộ dữ liệu RAG evaluation (`rag_questions.csv` và `rag_holdout.csv`) được khóa mã băm SHA-256 cố định, có `DATASET_CARD.md` phân định rõ vai trò là Frozen Regression Benchmark Gate Set. Bổ sung 3 ca test tự động chấm điểm Answer & Evidence Rubric (`test_evaluation_datasets_provenance_and_frozen_hash`, `test_holdout_evidence_rubric_coverage`, `test_out_of_scope_refusal_rubric`), tách biệt rạch ròi giữa CI Retrieval Gate và Answer Quality Rubric.

- AUD-18: Chuẩn hóa 6 runbook sự cố kỹ thuật, loại bỏ các hướng dẫn rủi ro (tắt antivirus, purge server, tắt SysMain), bổ sung điều kiện tiên quyết và phân định rạch ròi giữa thao tác người dùng (User Self-Service) và quyền quản trị (IT Administration). Sửa lỗi cú pháp lệnh `nslookup` và `netsh`. Bổ sung bộ kiểm thử an toàn runbook `tests/test_aud18_runbook_safety.py` (4 ca test pass 100%).

- AUD-20: Chuẩn hóa chỉ số `helpful_feedback_rate` trong `app/store.py`, minh bạch kích thước mẫu ($N$), số câu hỏi chưa đánh giá (`unrated_queries`) và tỷ lệ phản hồi (`feedback_response_rate`); cập nhật thẻ giao diện Dashboard từ "Tự phục vụ qua AI" sang "Đánh giá hữu ích RAG" hiển thị kèm mẫu số; bổ sung bộ kiểm thử `tests/test_aud20_analytics_metrics.py` (4 ca test pass 100%).

## 1. Bảng tổng hợp độ phủ kiểm thử (Test Coverage Summary)

| Loại kiểm thử | Công cụ / Framework | Số lượng test cases | Trạng thái thực thi |
|---|---|:---:|:---:|
| **Kiểm thử Đơn vị & Tích hợp Backend** | `pytest` / `FastAPI TestClient` | **220 passed, 30 skipped** (PostgreSQL, Docker CLI, symlink) | **Combined Coverage 87.26%** |
| **Kiểm thử Hàng đợi & Lọc sự cố Frontend** | Node.js unit runner (`test_queue.js`) | **8 assertions** | **100% Passed** |
| **Kiểm thử Chuyển tiếp ngữ cảnh (Handoff)** | Node.js unit runner (`test_handoff.js`) | **6 assertions** | **100% Passed** |
| **Kiểm thử Khởi động giao diện (Boot Smoke)** | Node.js unit runner (`test_frontend_boot.js`) | **Syntax & Script boot** | **100% Passed** |
| **Kiểm thử Chính sách phân công (Assignment)** | Node.js unit runner (`test_assignment_policy.js`) | **Read-only state lock** | **100% Passed** |
| **Kiểm thử Phiên làm việc (Session/Logout)** | Node.js unit runner (`test_logout.js`) | **Client token purge** | **100% Passed** |
| **Kiểm thử Phiếu khẩn cấp (Emergency Receipt)** | Node.js unit runner (`test_emergency.js`) | **Payload & Ticket ID** | **100% Passed** |
| **Kiểm thử Đa ngôn ngữ (i18n Coverage)** | Node.js unit runner (`test_i18n.js`) | **100% key parity** (Việt - Anh) | **100% Passed** |
| **Đánh giá Độ chính xác RAG Retrieval** | Script tự động [`scripts.evaluate_rag`](file:///E:/OpsMind-Helpdesk/scripts/evaluate_rag.py) | **30 ground-truth queries** | **Hit@3 = 100%, Evidence Hit = 96.4%** |
| **Đánh giá Benchmark RAG Holdout** | Script tự động [`scripts.evaluate_rag`](file:///E:/OpsMind-Helpdesk/scripts/evaluate_rag.py) | **60 frozen benchmark queries** | **Hit@3 = 100%, Evidence Hit = 100%, OOS = 100%** |

---

## 2. Ma trận truy vết chi tiết: SRS (FR / US) → Triển khai → Kiểm thử tự động

| Mã FR | Tên yêu cầu chức năng | User Story (US) | Thành phần triển khai (Code / Route) | Test Case tự động kiểm chứng | Trạng thái nghiệm thu |
|---|---|---|---|---|:---:|
| **FR-01** | Xác thực & Quản trị phiên | US-04 | `app/routers/auth.py`: `/auth/login`, `/auth/me`; `app/store.py`: JWT token có `session_epoch`, mã hóa PBKDF2-SHA256 | `test_login_and_token_role`, `test_invalid_login_and_missing_auth_are_rejected`, `tests/test_session_lifecycle.py` | **API Verified (Pytest Automated)** |
| **FR-02** | Chống dò quét & Timing Attack | US-04 | `app/routers/auth.py`: `_failed_logins` rate limiting (khóa 15m sau 5 lần sai); Dummy PBKDF2 hash chống user enumeration | `test_login_rate_limiting_blocks_after_five_failed_attempts` | **API Verified (Pytest Automated)** |
| **FR-03** | Đổi & Đặt lại mật khẩu | US-11 | `app/routers/auth.py`: `/auth/change-password`, `/auth/forgot-password`, `/auth/reset-password`; `app/routers/admin.py`: `/admin/users/{u}/reset-password`; `app/email_sender.py` | Toàn bộ `tests/test_password_reset.py` (7 tests: uniform response, rate limit, SHA256 token, session revocation), `test_admin_reset_user_password_and_force_change_flag` | **API Verified (Pytest Automated)** |
| **FR-04** | Tra cứu sự cố RAG | US-02 | `app/rag.py`: `retrieve_relevant_context`, BM25 retriever trên 30 Runbook; `app/routers/rag.py`: `POST /rag/ask` | `test_rag_finds_vietnamese_printer_and_vpn_sources`, `test_rag_results_do_not_repeat_the_same_runbook`, `tests/test_rag_dataset.py` | **Benchmark Verified (Frozen Holdout Hit@3 100%)** |
| **FR-05** | Cổng từ chối thông minh | US-02 | `app/rag.py`: `is_out_of_scope`, cơ chế abstention an toàn; trả lời từ chối lịch sự | `test_rag_refuses_questions_without_relevant_knowledge`, `test_out_of_scope_refusal_rubric` | **Benchmark Verified (OOS Refusal 100%)** |
| **FR-06** | Phân loại & Đề xuất ưu tiên | US-08 | `app/rag.py`: `suggest_ticket_triage`, luật tác động nghiệp vụ tự động gợi ý Category và Priority kèm lý do giải thích | `test_triage_suggests_urgent_for_broad_impact_but_never_auto_confirms` | **API Verified (Pytest Automated)** |
| **FR-07** | Chuyển tiếp ngữ cảnh (Handoff) | US-08 | `app/static/app.js`: Hàm `buildHandoffDescription`, `addTicketHandoff`, tự động điền tiêu đề/mô tả/danh mục/ưu tiên sang form tạo vé | `tests/test_handoff.js` | **UI Tested (test_handoff.js runner)** |
| **FR-08** | Quản lý phiên hỏi đáp RAG | US-10 | `app/routers/rag.py`: `GET /rag/sessions`, `POST /rag/feedback`; `app/store.py`: Bảng `chat_sessions`, `chat_messages` | `test_rag_chat_history_and_feedback_are_scoped_to_the_user` | **API Verified (Pytest Automated)** |
| **FR-09** | Tạo yêu cầu hỗ trợ (Ticket) | US-01 | `app/routers/tickets.py`: `POST /tickets`; tự động tính `sla_deadline` theo độ ưu tiên (2h/8h/24h/48h) và ghi Audit Log | `test_ticket_creation_sets_sla_and_audit_log`, `test_ticket_fields_are_validated` | **API Verified (Pytest Automated)** |
| **FR-10** | Hàng đợi sự cố thông minh | US-01, US-03 | `app/routers/tickets.py`: `GET /tickets`; `app/static/app.js`: Bộ lọc đa chiều (SLA status, My Tickets, Unassigned) | `test_user_only_sees_own_ticket_and_staff_sees_queue`, `test_analytics_and_ticket_filters`, `tests/test_queue.js` | **API Verified / UI Filter Tested (test_queue.js)** |
| **FR-11** | Quản lý vòng đời FSM | US-03, US-09 | `app/store.py`: `TRANSITIONS` matrix; `app/routers/tickets.py`: `PATCH /tickets/{id}`; Kiểm soát 6 trạng thái chuẩn ITIL | `test_ticket_lifecycle_and_invalid_transitions`, `test_requester_can_confirm_resolution_or_reopen_ticket`, `test_requester_reply_reopens_waiting_ticket` | **API & Store Verified (ITIL FSM Matrix)** |
| **FR-12** | Phân công & Chuyển giao | US-03 | `app/routers/tickets.py`: `PUT /tickets/{id}/assignment`, `GET /staff`; Ghi nhận tác nhân và thời gian phân công | `test_agent_assignment_and_comment_are_recorded`, `test_invalid_assignee_is_rejected`, `tests/test_assignment_policy.py`, `tests/test_assignment_policy.js` | **API & Store Verified (Freeze Completed AUD-14)** |
| **FR-13** | Trao đổi bình luận 2 chiều | US-05 | `app/routers/tickets.py`: `POST /tickets/{id}/comments`; Hiển thị tiến trình thời gian; tự động chuyển vé chờ về `in_progress` | `test_agent_assignment_and_comment_are_recorded`, `test_whitespace_only_ticket_comment_and_rag_input_are_rejected` | **API & Store Verified (Pytest Automated)** |
| **FR-14** | Đính kèm tệp tin chẩn đoán | US-10 | `app/routers/tickets.py`: `POST /tickets/{id}/attachments`, `GET /tickets/{id}/attachments/{id}`; Giới hạn $\le$ 10 MiB, allow-list định dạng | `test_ticket_attachment_upload_download_and_access_control` | **API Verified / Storage Staging Pending (AUD-09)** |
| **FR-15** | Đóng & Mở lại ticket | US-06, US-09 | `app/routers/tickets.py`: `PATCH /tickets/{id}`, `DELETE /tickets/{id}`; Chỉ người tạo mới được xác nhận đóng hoặc mở lại vé | `test_owner_can_edit_new_ticket_and_priority_recalculates_sla`, `test_ticket_edit_is_restricted_after_processing_starts`, `test_admin_archives_ticket_without_removing_audit` | **API & Store Verified (Pytest Automated)** |
| **FR-16** | Đánh giá hài lòng CSAT | US-09 | `app/routers/tickets.py`: `POST /tickets/{id}/rate`; Đánh giá 1–5 sao kèm bình luận, cập nhật tức thì vào chỉ số tổng hợp | `test_ticket_rating_requires_resolved_owned_ticket_and_updates_analytics` | **API & Store Verified (Pytest Automated)** |
| **FR-17** | RAG Assist cho Kỹ thuật viên | US-03 | `app/static/app.js`: Nút tra cứu Runbook từ mô tả ticket và nút chèn trích dẫn vào ô bình luận với 1 click | `test_rag_finds_vietnamese_printer_and_vpn_sources`, kiểm thử cú pháp JS frontend | **UI Smoke Tested (Node syntax & modules)** |
| **FR-18** | Soạn thảo Runbook Markdown | US-07 | `app/routers/knowledge.py`: `POST /knowledge`; `app/static/app.js`: Trình soạn thảo Markdown chia đôi màn hình Live Preview | `test_admin_can_ingest_valid_markdown_and_retriever_refreshes`, `test_knowledge_upload_rejects_invalid_documents` | **API Verified / UI Markdown Live Preview Smoke** |
| **FR-19** | Quy trình kiểm duyệt 2 lớp | US-13 | `app/routers/knowledge.py`: `PUT /knowledge/{id}`, `POST /knowledge/{id}/review`; Agent soạn `pending_review`, Admin duyệt `published` | `test_knowledge_lifecycle_and_review_workflow`, `test_non_admin_cannot_ingest_knowledge_and_non_markdown_is_rejected` | **API & Store Verified (Review Workflow)** |
| **FR-20** | Lịch sử phiên bản & Khôi phục | US-13 | `app/routers/knowledge.py`: `GET /knowledge/{id}/versions`, `POST /knowledge/{id}/restore/{version}`; Lưu snapshot và restore | `test_knowledge_version_history_and_restoration` | **API & Store Verified (Version Restore)** |
| **FR-21** | Đóng vòng Ticket $
ightarrow$ Runbook | US-14 | `app/static/app.js`: Nút trích xuất giải pháp từ sự cố đã xử lý thành bản nháp Runbook Markdown mới | `test_knowledge_lifecycle_and_review_workflow` | **UI Smoke Tested (Draft extraction)** |
| **FR-22** | Thông báo Telegram & Discord | US-12 | `app/notifications.py`: `notify_telegram`, `notify_discord`; `app/notification_outbox.py`; `app/routers/admin.py`: `/admin/notifications/status`, `/admin/notifications/test` | Toàn bộ `tests/test_notifications.py` (5 tests), `tests/test_notification_outbox.py` (16 tests) | **Transactional Outbox Verified (AUD-13)** |
| **FR-23** | Quản lý người dùng & phân quyền | US-04, US-07 | `app/routers/admin.py`: `GET/POST /admin/users`, `PATCH /admin/users/{u}`; Bảo vệ tài khoản Admin cuối không bị khóa | `test_admin_can_create_user_without_exposing_password`, `test_admin_can_edit_profile_role_and_lock_accounts`, `test_end_user_cannot_change_ticket_or_view_staff_analytics` | **API Verified (Role & Active protection)** |
| **FR-24** | Báo cáo SLA & Thống kê | US-16 | `app/routers/analytics.py`: `GET /analytics`, `GET /analytics/agents/me`, `GET /analytics/export`; Báo cáo điều hành và hiệu suất cá nhân | `test_analytics_and_ticket_filters`, `test_agent_personal_analytics_are_scoped_to_assigned_tickets`, `test_admin_can_export_ticket_report_only`, `tests/test_aud20_analytics_metrics.py` | **API Verified (Helpful Rate AUD-20)** |
| **FR-25** | Nhật ký Audit Log bất biến | US-03, US-06 | `app/routers/tickets.py`: `GET /tickets/{id}/audit`; `app/store.py`: Bảng `audit_logs`, lưu vết tác nhân/thời gian/thao tác | `test_ticket_creation_sets_sla_and_audit_log`, `test_admin_archives_ticket_without_removing_audit` | **API & Store Verified (Immutable Audit Log)** |
| **FR-26** | Giao diện song ngữ (Việt - Anh) | — | `app/static/i18n.js`: Từ điển song ngữ toàn diện; `app/static/app.js`: Cơ chế đổi ngôn ngữ lưu LocalStorage | `tests/test_i18n.js` (kiểm tra 100% key đồng nhất giữa tiếng Việt và tiếng Anh) | **UI Tested (test_i18n.js 100% key parity)** |
| **FR-27** | Cổng dịch vụ CNTT & Thẻ kịch bản nhanh | US-15 | `app/static/index.html`, `app/static/app.js`: Thanh thẻ kịch bản sự cố (`.scenario-chips-bar`) và 6 ô danh mục dịch vụ JSM | `tests/test_handoff.js`, kiểm thử tải giao diện người dùng | **UI Tested (Scenario Chips & Service Desk UI)** |
| **FR-28** | Quản lý Hồ sơ & Thông tin cá nhân | US-17 | `app/routers/auth.py`: `GET /auth/me`, `PATCH /auth/profile`; `app/store.py`: `get_user_activity`; `app/static/index.html`: `#userProfileModal` | `test_user_profile_endpoints` | **API Verified / Modal UI Smoke** |

---

## 3. Lệnh thực thi kiểm thử định kỳ

Để đảm bảo chất lượng liên tục (CI) và tính toàn vẹn của mã nguồn, các lệnh sau được chạy tự động trên GitHub Actions:

```powershell
# 1. Kiểm tra định dạng và rà soát lỗi bảo mật bằng Ruff (tương đương Bandit)
py -m ruff check app tests scripts

# 2. Kiểm tra tính hợp lệ của mã JavaScript và từ điển đa ngôn ngữ
node --check app/static/app.js
node --check app/static/i18n.js
node tests/test_i18n.js
node tests/test_queue.js
node tests/test_handoff.js
node tests/test_frontend_boot.js
node tests/test_emergency.js
node tests/test_assignment_policy.js
node tests/test_logout.js

# 3. Biên dịch kiểm tra cú pháp Python
py -m compileall -q app tests scripts

# 4. Chạy toàn bộ test suite Python và đo lường Code Coverage
py -m pytest --cov=app --cov-report=term-missing --cov-report=xml

# 5. Đánh giá tự động độ chính xác của giải thuật RAG
py -m scripts.evaluate_rag
```


### AUD-09 — persistent attachment deployment

Kiểm local: YAML parse, storage/SQLite path nằm dưới disk, một instance và gói trả phí; API upload/download/access-control hiện có. Gate cloud chưa chạy: validate Blueprint trên Render, UID 10001 ghi volume, di chuyển file/checksum + DB, restart/redeploy cùng disk và restore cách ly. Không thay kết quả cloud bằng test filesystem local.


### AUD-10 — không chặn event loop

`tests/test_event_loop.py`: 7 ca HTTP thật với một Uvicorn process riêng;
chờ marker xác nhận tác vụ đồng bộ đã bắt đầu, `/health` phải trả trước release.
Trước sửa, ca RAG timeout (FAIL); sau sửa cả 7 ca PASS, mỗi ca 8 health probes.
Kiểm đầy đủ nghiệp vụ/phân quyền bằng suite hiện có; test không mock auth hay
store trả về thành công giả. Hook chỉ giữ chờ rồi gọi implementation thật.
Không chứng minh throughput, provider thật, PostgreSQL, Linux hay cloud.


### AUD-11 — KB DB authority và lỗi persistence

`tests/test_knowledge_persistence.py`: lỗi DB import -> 503 không file/row;
trigger lỗi ghi version -> rollback tài liệu; slug trùng và upload đồng thời
-> một document/version; thư mục immutable vẫn upload được; author/reviewer
và is_builtin giữ nguyên qua process mới + initialize; file lẻ không được
list/get/reindex/delete; chặn builtin collision trước xóa DB; delete lỗi giữ
dữ liệu; delete thành công không unlink/resurrect file legacy. Trước sửa 12
ca đầu có 11 FAIL, 1 PASS; thêm ca delete-success sau đó.

Tests API cũ dùng DB record thay kỳ vọng upload/delete filesystem; path/symlink
regression vẫn bảo đảm lookup không đọc file ngoài DB. AUD-10 HTTP regression
đổi nhãn knowledge_file thành knowledge_import; vẫn giữ chờ rồi chạy import
thật. Hai test PostgreSQL thêm trong test_postgres kiểm unique/version và
trigger rollback; local skip khi không có DATABASE_URL, không coi đã đạt.


### AUD-12 — emergency receipt

`node tests/test_emergency.js` chạy handler thực từ app.js: response contract,
payload P1, receipt không xác nhận delivery, thiếu/sai ID, API timeout, lỗi
refresh sau thành công, concurrent/repeated submit, không tự đóng modal và
loại nhãn integration chưa chứng minh. Baseline FAIL ở result.ticket.id;
bản sửa PASS. CI thêm runner này; i18n/queue/handoff/frontend boot vẫn PASS.
Chrome + frontend thật + FastAPI TestClient/SQLite qua stdio route interception
đã tạo ticket P1 bằng tiếng Việt/Anh, so ID response với receipt, kiểm nút
disabled/modal còn mở, không page error. Không là socket HTTP/cloud/provider test.
Nhóm API ticket/notification hiện có 7 passed, 61 deselected; không chạy lại
toàn bộ pytest do không sửa backend. Suite AUD-11 là kết quả lịch sử riêng.


### AUD-13 — event, delivery state, retry và recovery

Baseline: regression escalation GET durable delivery trả 404 (FAIL). Sau sửa:
tests/test_notification_outbox.py có 16 ca API/store/worker, kiểm create +
escalate hai kênh/event, no-op/repeated transition, rollback enqueue, concurrent
escalation, retry 3 lần/backoff/stable event ID, không resend kênh accepted,
exception secret không lưu, target rotation, manual retry/audit/quyền admin,
cursor không mất row cùng timestamp, stale ack fence, lease hết budget, recovery
qua process mới, lifespan drain, wake lỗi không biến create thành thất bại.
Nhóm outbox + notifications 21 passed. Ba ca PG mới: exclusive claim/schema
idempotence, concurrent escalation/rollback, serialized manual retry; local skip.

Chrome frontend thật + FastAPI TestClient/SQLite qua stdio, Telegram mocked
accepted: user/agent/admin login/restore/RAG/editor/admin hub PASS; history DB
hiện provider accepted và staff acknowledgement unknown. Không gọi provider
thật; không là HTTP socket E2E/cloud. Năm Node runners và Ruff/diff PASS.
Full suite/kết quả coverage được lưu báo cáo phiên. AUD-16 email chưa thuộc
durable outbox này; AUD-23 race nghiệp vụ khác vẫn mở.


### AUD-14 — completed assignment and attribution

tests/test_assignment_policy.py: resolved/closed x agent/admin API 409, so toàn
bộ ticket/audit và KPI trước-sau; store gọi trực tiếp cũng chặn; bốn trạng thái
chưa hoàn tất vẫn giao được; reopen/assign/resolve tính owner mới; archived/missing
404; requester 403 và cùng assignee vẫn 409. Mock lookup mất sau visibility
được map 404. Concurrency pause ngay sau read assignment bằng Event và proxy
connection, writer resolution phải chờ transaction; sau release owner trước
resolution giữ nguyên và assignment sau resolution bị chặn. Timeout .2s dùng
kiểm lock khi đã đồng bộ phase, không là benchmark latency.

Baseline 13 ca: 7 failed, 6 passed; sau sửa 13 passed, thêm hai ca API vào full
suite. tests/test_assignment_policy.js baseline FAIL ở resolved, sau sửa PASS:
select/button read-only và callback không gọi API sau hoàn tất, active vẫn gọi.
CI thêm runner, cache v8/i18n tooltip. Ba PG case (hai trạng thái và read/write
serialization dùng helper chung) local skip, chưa coi PG runtime đã kiểm.


### AUD-15 — session revocation

tests/test_session_lifecycle.py: logout copies/all epoch tokens, account cycles,
no-op/profile, missing/invalid/non-ASCII claim, expiry/signature/required claims,
password/admin reset + forced logout, stale CAS, account rollback, DB failure,
own-account-only/auth required, legacy SQLite schema migration/idempotence,
new-user nonce, new-process recovery và concurrent CAS. Baseline 16 failed,
2 passed trong 18 ca đầu; sau sửa 18 passed, thêm 6 ca vào nhóm cuối.
Nhóm session + password reset 62 passed, warning TestClient/httpx hiện có.

tests/test_logout.js kiểm captured bearer, local clear, server ack/401/false,
503/malformed/abort, duplicate click, response cũ không xóa login mới và /me
401 không dựng lại signed-in view. CI thêm runner; i18n/boot và các regression
UI khác PASS. Chrome kiểm logout thường, account active/role cycles và logout
trong forced-password modal, copied token 401, localStorage/password clear,
không page error. FastAPI TestClient/SQLite bridge stdio, không là socket HTTP
E2E/cloud. Bốn PG case local skip, không coi PG runtime đã kiểm.

### AUD-23 — CSAT/FSM/versioning concurrency

`tests/test_aud23_concurrency.py`: hai connections có pause sau read và writer
cạnh tranh; CSAT một accepted/một conflict và một audit; comment không undo
resolution; competing expected_status chỉ một winner; status stale API 409
(explicit expected_status và legacy route snapshot); priority edit xét lại
completed dưới khóa; closed/comment race; partial KB updates giữ field;
review/restore giữ version snapshot đúng; unique constraint; rollback khi
audit/version insert lỗi; migration idempotent và duplicate legacy không repair.
8 ca đầu FAIL trên working tree trước phiên (AUD01–22), rồi PASS sau bản sửa.
`tests/test_status_concurrency.js` thực thi handler UI trong VM, kiểm payload
expected_status và surfacing 409, được thêm vào CI; không là browser E2E.
`tests/test_postgres.py::test_postgres_aud23_concurrent_business_writes` có 7
scenario dùng cùng helper hai connection thật; chưa chạy local vì thiếu PG.
Acceptance local SQLite, API và Node có bằng chứng; PG/CI/staging vẫn pending.

### AUD-24 — Password roundtrip

`tests/test_aud24_password_roundtrip.py`: 16 ca API (create/change/reset/admin-reset
× ASCII spaces/Unicode whitespace/Unicode NFC/Unicode NFD), xác minh PBKDF2 và
login nguyên chuỗi thành công, trimmed hoặc canonical form khác bị từ chối;
old_password có khoảng trắng vẫn được dùng nguyên trạng khi change. Reset token
có padding được trim và chỉ dùng một lần. Bốn ca schema kiểm biên độ dài
11/12/200/201 trên chuỗi có spaces. Baseline 7 FAIL, 13 PASS; sau sửa kiểm cùng
test_password_reset và test_session_lifecycle. Dữ liệu/secret đều synthetic,
SQLite sandbox; không gửi email thật hoặc sửa credential production.

### AUD-16 bổ sung — Đóng thiếu sót acceptance email

Baseline review 3 tầng có 4/4 acceptance probes FAIL, không được xem enum-only fix
là đóng toàn AUD16. tests/test_email_delivery.py có 26 ca API/store/lifecycle:
welcome không reusable password + one-use; SMTP disabled false; 6 provider non-demo
thiếu cấu hình từ chối startup; failure retry qua lifespan restart; bounded retry/
crash leases/fencing; account/email/role/config/expiry cancellation; không raw token
DB/API; account+job rollback, link-revocation rollback; supersede; accepted không
resend; process mới dựng cùng token qua HMAC; TLS/base URL; SMTP refusal và error
sanitization. Các contract queue API chưa tồn tại là một phần baseline mới.

Test welcome cũ từng yêu cầu password trong body, nay đảo assertion để thực thi
acceptance đúng (không password, phải có one-use link); không bỏ checks force-change/
login hiện có. Hai SMTP mock trả {} theo contract send_message để kiểm refused dict.
tests/test_postgres.py thêm 4 scenario claim fencing/accepted/supersede/account rollback;
skip nếu thiếu sandbox PG, không là bằng chứng PG PASS. Bốn probe độc lập trong
work/probe_aud16_completion.py giữ logic review gốc, ghi evidence mới không overwrite
snapshot review trước. Browser 3 vai trò và Node kiểm regression frontend/i18n.
