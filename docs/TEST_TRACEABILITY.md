# Ma trận truy vết yêu cầu và kiểm thử (Test Traceability Matrix)

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

## 1. Bảng tổng hợp độ phủ kiểm thử (Test Coverage Summary)

| Loại kiểm thử | Công cụ / Framework | Số lượng test cases | Trạng thái thực thi |
|---|---|:---:|:---:|
| **Kiểm thử Đơn vị & Tích hợp Backend** | `pytest` / `FastAPI TestClient` | **67 test cases** (66 passed, 1 skipped PostgreSQL local) | **100% Passed** |
| **Kiểm thử Hàng đợi & Lọc sự cố Frontend** | Node.js unit runner (`test_queue.js`) | **8 assertions** | **100% Passed** |
| **Kiểm thử Chuyển tiếp ngữ cảnh (Handoff)** | Node.js unit runner (`test_handoff.js`) | **6 assertions** | **100% Passed** |
| **Kiểm thử Đa ngôn ngữ (i18n Coverage)** | Node.js unit runner (`test_i18n.js`) | **100% key parity** (Việt - Anh) | **100% Passed** |
| **Đánh giá Độ chính xác RAG Retrieval** | Script tự động [`scripts.evaluate_rag`](file:///E:/OpsMind-Helpdesk/scripts/evaluate_rag.py) | **30 ground-truth queries** | **Hit@3 = 100%** |

---

## 2. Ma trận truy vết chi tiết: SRS (FR / US) → Triển khai → Kiểm thử tự động

| Mã FR | Tên yêu cầu chức năng | User Story (US) | Thành phần triển khai (Code / Route) | Test Case tự động kiểm chứng | Trạng thái nghiệm thu |
|---|---|---|---|---|:---:|
| **FR-01** | Xác thực & Quản trị phiên | US-04 | `app/main.py`: `/auth/login`, `/auth/me`; `app/store.py`: JWT token có `pwd_at`, mã hóa PBKDF2-SHA256 | `test_login_and_token_role`, `test_invalid_login_and_missing_auth_are_rejected`, `test_user_change_password_and_token_invalidation` | **Đạt 100%** |
| **FR-02** | Chống dò quét & Timing Attack | US-04 | `app/main.py`: `_failed_logins` rate limiting (khóa 15m sau 5 lần sai); Dummy PBKDF2 hash chống user enumeration | `test_login_rate_limiting_blocks_after_five_failed_attempts` | **Đạt 100%** |
| **FR-03** | Đổi & Đặt lại mật khẩu | US-11 | `app/main.py`: `/auth/change-password`, `/auth/forgot-password`, `/auth/reset-password`, `/admin/users/{u}/reset-password`; `app/email_sender.py` | Toàn bộ `tests/test_password_reset.py` (7 tests: uniform response, rate limit, SHA256 token, session revocation), `test_admin_reset_user_password_and_force_change_flag` | **Đạt 100%** |
| **FR-04** | Tra cứu sự cố RAG | US-02 | `app/rag.py`: `search_runbooks`, BM25 retriever trên 30 Runbook; `app/main.py`: `POST /rag/ask` | `test_rag_finds_vietnamese_printer_and_vpn_sources`, `test_rag_results_do_not_repeat_the_same_runbook`, `tests/test_rag_dataset.py` | **Đạt 100%** |
| **FR-05** | Cổng từ chối thông minh | US-02 | `app/rag.py`: Ngưỡng điểm tương đồng tối thiểu và cơ chế abstention an toàn; trả lời từ chối lịch sự | `test_rag_refuses_questions_without_relevant_knowledge` | **Đạt 100%** |
| **FR-06** | Phân loại & Đề xuất ưu tiên | US-08 | `app/rag.py`: Luật tác động nghiệp vụ tự động gợi ý Category và Priority kèm lý do giải thích | `test_triage_suggests_urgent_for_broad_impact_but_never_auto_confirms` | **Đạt 100%** |
| **FR-07** | Chuyển tiếp ngữ cảnh (Handoff) | US-08 | `app/static/app.js`: Hàm `handoffToTicket`, tự động điền tiêu đề/mô tả/danh mục/ưu tiên sang form tạo vé | `tests/test_handoff.js` | **Đạt 100%** |
| **FR-08** | Quản lý phiên hỏi đáp RAG | US-10 | `app/main.py`: `GET /rag/sessions`, `POST /rag/feedback`; `app/store.py`: Bảng `chat_sessions`, `chat_messages` | `test_rag_chat_history_and_feedback_are_scoped_to_the_user` | **Đạt 100%** |
| **FR-09** | Tạo yêu cầu hỗ trợ (Ticket) | US-01 | `app/main.py`: `POST /tickets`; tự động tính `sla_deadline` theo độ ưu tiên (2h/8h/24h/48h) và ghi Audit Log | `test_ticket_creation_sets_sla_and_audit_log`, `test_ticket_fields_are_validated` | **Đạt 100%** |
| **FR-10** | Hàng đợi sự cố thông minh | US-01, US-03 | `app/main.py`: `GET /tickets`; `app/static/app.js`: Bộ lọc đa chiều (SLA status, My Tickets, Unassigned) | `test_user_only_sees_own_ticket_and_staff_sees_queue`, `test_analytics_and_ticket_filters`, `tests/test_queue.js` | **Đạt 100%** |
| **FR-11** | Quản lý vòng đời FSM | US-03, US-09 | `app/store.py`: `TRANSITIONS` matrix; `app/main.py`: `PATCH /tickets/{id}`; Kiểm soát 6 trạng thái chuẩn ITIL | `test_ticket_lifecycle_and_invalid_transitions`, `test_requester_can_confirm_resolution_or_reopen_ticket`, `test_requester_reply_reopens_waiting_ticket` | **Đạt 100%** |
| **FR-12** | Phân công & Chuyển giao | US-03 | `app/main.py`: `PUT /tickets/{id}/assignment`, `GET /staff`; Ghi nhận tác nhân và thời gian phân công | `test_agent_assignment_and_comment_are_recorded`, `test_invalid_assignee_is_rejected` | **Đạt 100%** |
| **FR-13** | Trao đổi bình luận 2 chiều | US-05 | `app/main.py`: `POST /tickets/{id}/comments`; Hiển thị tiến trình thời gian; tự động chuyển vé chờ về `in_progress` | `test_agent_assignment_and_comment_are_recorded`, `test_whitespace_only_ticket_comment_and_rag_input_are_rejected` | **Đạt 100%** |
| **FR-14** | Đính kèm tệp tin chẩn đoán | US-10 | `app/main.py`: `POST /tickets/{id}/attachments`, `GET /tickets/{id}/attachments/{id}`; Giới hạn $\le$ 10 MiB, allow-list định dạng | `test_ticket_attachment_upload_download_and_access_control` | **Đạt 100%** |
| **FR-15** | Đóng & Mở lại ticket | US-06, US-09 | `app/main.py`: `PATCH /tickets/{id}`, `DELETE /tickets/{id}`; Chỉ người tạo mới được xác nhận đóng hoặc mở lại vé | `test_owner_can_edit_new_ticket_and_priority_recalculates_sla`, `test_ticket_edit_is_restricted_after_processing_starts`, `test_admin_archives_ticket_without_removing_audit` | **Đạt 100%** |
| **FR-16** | Đánh giá hài lòng CSAT | US-09 | `app/main.py`: `POST /tickets/{id}/rate`; Đánh giá 1–5 sao kèm bình luận, cập nhật tức thì vào chỉ số tổng hợp | `test_ticket_rating_requires_resolved_owned_ticket_and_updates_analytics` | **Đạt 100%** |
| **FR-17** | RAG Assist cho Kỹ thuật viên | US-03 | `app/static/app.js`: Nút tra cứu Runbook từ mô tả ticket và nút chèn trích dẫn vào ô bình luận với 1 click | `test_rag_finds_vietnamese_printer_and_vpn_sources`, kiểm thử cú pháp JS frontend | **Đạt 100%** |
| **FR-18** | Soạn thảo Runbook Markdown | US-07 | `app/main.py`: `POST /knowledge`; `app/static/app.js`: Trình soạn thảo Markdown chia đôi màn hình Live Preview | `test_admin_can_ingest_valid_markdown_and_retriever_refreshes`, `test_knowledge_upload_rejects_invalid_documents` | **Đạt 100%** |
| **FR-19** | Quy trình kiểm duyệt 2 lớp | US-13 | `app/main.py`: `PUT /knowledge/{id}`, `POST /knowledge/{id}/review`; Agent soạn `pending_review`, Admin duyệt `published` | `test_knowledge_lifecycle_and_review_workflow`, `test_non_admin_cannot_ingest_knowledge_and_non_markdown_is_rejected` | **Đạt 100%** |
| **FR-20** | Lịch sử phiên bản & Khôi phục | US-13 | `app/main.py`: `GET /knowledge/{id}/versions`, `POST /knowledge/{id}/restore/{version}`; Lưu snapshot và restore | `test_knowledge_version_history_and_restoration` | **Đạt 100%** |
| **FR-21** | Đóng vòng Ticket $\rightarrow$ Runbook | US-14 | `app/static/app.js`: Nút trích xuất giải pháp từ sự cố đã xử lý thành bản nháp Runbook Markdown mới | `test_knowledge_lifecycle_and_review_workflow` | **Đạt 100%** |
| **FR-22** | Thông báo Telegram & Discord | US-12 | `app/notifications.py`: `notify_telegram`, `notify_discord`; `app/main.py`: `/admin/notifications/status`, `/admin/notifications/test` | Toàn bộ `tests/test_notifications.py` (5 tests: SSRF protection, RFC1918 blocking, token masking, test dispatch) | **Đạt 100%** |
| **FR-23** | Quản lý người dùng & phân quyền | US-04, US-07 | `app/main.py`: `GET/POST /admin/users`, `PATCH /admin/users/{u}`; Bảo vệ tài khoản Admin cuối không bị khóa | `test_admin_can_create_user_without_exposing_password`, `test_admin_can_edit_profile_role_and_lock_accounts`, `test_end_user_cannot_change_ticket_or_view_staff_analytics` | **Đạt 100%** |
| **FR-24** | Báo cáo SLA & Thống kê | US-16 | `app/main.py`: `GET /analytics`, `GET /analytics/agents/me`, `GET /analytics/export`; Báo cáo điều hành và hiệu suất cá nhân | `test_analytics_and_ticket_filters`, `test_agent_personal_analytics_are_scoped_to_assigned_tickets`, `test_admin_can_export_ticket_report_only` | **Đạt 100%** |
| **FR-25** | Nhật ký Audit Log bất biến | US-03, US-06 | `app/main.py`: `GET /tickets/{id}/audit`; `app/store.py`: Bảng `audit_logs`, lưu vết tác nhân/thời gian/thao tác | `test_ticket_creation_sets_sla_and_audit_log`, `test_admin_archives_ticket_without_removing_audit` | **Đạt 100%** |
| **FR-26** | Giao diện song ngữ (Việt - Anh) | — | `app/static/i18n.js`: Từ điển song ngữ toàn diện; `app/static/app.js`: Cơ chế đổi ngôn ngữ lưu LocalStorage | `tests/test_i18n.js` (kiểm tra 100% key đồng nhất giữa tiếng Việt và tiếng Anh) | **Đạt 100%** |
| **FR-27** | Cổng dịch vụ CNTT & Thẻ kịch bản nhanh | US-15 | `app/static/index.html`, `app/static/app.js`: Thanh thẻ kịch bản sự cố (`.scenario-chips-bar`) và 6 ô danh mục dịch vụ JSM | `tests/test_handoff.js`, kiểm thử tải giao diện người dùng | **Đạt 100%** |
| **FR-28** | Quản lý Hồ sơ & Thông tin cá nhân | US-17 | `app/main.py`: `GET /auth/me`, `PATCH /auth/profile`; `app/store.py`: `get_user_activity`; `app/static/index.html`: `#userProfileModal` | `test_user_profile_endpoints` | **Đạt 100%** |

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

# 3. Biên dịch kiểm tra cú pháp Python
py -m compileall -q app tests scripts

# 4. Chạy toàn bộ test suite Python và đo lường Code Coverage
py -m pytest --cov=app --cov-report=term-missing --cov-report=xml

# 5. Đánh giá tự động độ chính xác của giải thuật RAG
py -m scripts.evaluate_rag
```
