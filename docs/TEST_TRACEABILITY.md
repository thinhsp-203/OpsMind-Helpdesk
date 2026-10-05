# Ma trận truy vết yêu cầu và kiểm thử

**Phạm vi:** trạng thái của mã nguồn trong repository; không thay thế test nghiệm thu với người dùng/GVHD.\
**Ngày cập nhật:** 05/10/2026

## 1. Truy vết SRS → kiểm thử

| Yêu cầu/story | Cách triển khai | Kiểm thử tự động hiện có | Còn thiếu để nghiệm thu |
|---|---|---|---|
| FR-01 / US-04 — Đăng nhập, phiên và phân quyền | `app/main.py`: `/auth/login`, `/auth/me`, `current_user`; demo note lấy từ `/config` | `test_login_and_token_role`, `test_invalid_login_and_missing_auth_are_rejected`, `test_health_and_web_app_are_available` | Rate limit, đổi/reset mật khẩu, kiểm thử browser login và xác nhận chính sách tài khoản với đơn vị |
| FR-02/03 / US-01 — Tạo và xem ticket | `/tickets`, giới hạn dữ liệu theo requester/role | `test_user_only_sees_own_ticket_and_staff_sees_queue`, `test_ticket_creation_sets_sla_and_audit_log`, `test_analytics_and_ticket_filters` | Kiểm thử E2E trên browser; xác nhận biểu mẫu/nghiệp vụ với End-user |
| FR-04 — FSM | `store.TRANSITIONS`, `PATCH /tickets/{id}`, phản hồi tự đưa ticket chờ về xử lý; requester xác nhận/mở lại khi resolved | `test_ticket_lifecycle_and_invalid_transitions`, `test_requester_can_confirm_resolution_or_reopen_ticket`, `test_requester_reply_reopens_waiting_ticket` | Chốt chuyển trạng thái với quy trình IT thực tế; chưa có auto-close sau 72 giờ |
| FR-05 — Phân công | `GET /staff` cung cấp danh sách Agent/Admin; `PUT /tickets/{id}/assignment` chỉ nhận nhân sự IT | `test_admin_can_create_user_without_exposing_password`, `test_agent_assignment_and_comment_are_recorded`, `test_invalid_assignee_is_rejected` | Kiểm tra ca trực/nhóm xử lý trên quy trình thật |
| FR-06 / US-05 — Trao đổi và audit | Bình luận theo ticket; audit actor/time | `test_agent_assignment_and_comment_are_recorded`, `test_admin_archives_ticket_without_removing_audit` | Quy định retention, export và quyền xem audit sau khi lưu trữ |
| FR-07 — SLA | `PRIORITY_HOURS`; đếm ticket quá hạn | `test_ticket_creation_sets_sla_and_audit_log`, `test_owner_can_edit_new_ticket_and_priority_recalculates_sla`, `test_analytics_and_ticket_filters` | Mô hình giờ làm/ngày nghỉ, timezone nghiệp vụ và SLA đã được stakeholder duyệt |
| FR-08 / US-02 — Truy xuất tri thức, nguồn, từ chối | `app/rag.py`: BM25, mỗi tài liệu tối đa một đoạn, nguồn và ngưỡng relevance | `test_rag_finds_vietnamese_printer_and_vpn_sources`, `test_rag_results_do_not_repeat_the_same_runbook`, `test_rag_refuses_questions_without_relevant_knowledge`, `tests/test_rag_dataset.py` | Ground truth do IT xác nhận; faithfulness/answer relevance; paraphrase và tập ngoài phạm vi lớn hơn |
| FR-15 / US-08 — Auto-triage có xác nhận | Danh mục từ runbook đầu; ưu tiên từ marker luật cố định; form chỉ được điền khi người gửi bấm bàn giao | `test_rag_finds_vietnamese_printer_and_vpn_sources`, `test_triage_suggests_urgent_for_broad_impact_but_never_auto_confirms`, `test_rag_refuses_questions_without_relevant_knowledge` | Đánh giá precision của phân loại/priority trên ticket đã được IT gán nhãn; browser E2E xác nhận người dùng sửa được trước gửi |
| FR-16 — RAG Assist theo ticket | Nút trên từng ticket gửi tiêu đề/mô tả sang truy xuất; Agent/Admin chủ động chèn trích đoạn có nguồn vào ô bình luận; không tự gửi | API retrieval tests; JS syntax check | Browser E2E xác nhận đúng ticket được gắn ngữ cảnh, bản nháp sửa được và không tự gửi; IT đánh giá độ hữu ích của nguồn |
| FR-17 — Lịch sử/feedback RAG | Session/message lưu SQLite, nguồn và feedback; API truy vấn session theo chủ sở hữu | `test_rag_chat_history_and_feedback_are_scoped_to_the_user` | Browser E2E, chính sách retention và thử nghiệm usability |
| FR-18 — Attachment/rating | API lưu PNG/JPG/TXT/LOG ≤10 MiB; kiểm tra quyền trước download; ticket được đánh giá sau resolved | `test_ticket_attachment_upload_download_and_access_control`, `test_ticket_rating_requires_resolved_owned_ticket_and_updates_analytics` | Malware scan, kiểm thử browser, retention/backup được phê duyệt |
| FR-19/20 — Quản trị user/KB | Admin chỉnh hồ sơ/role/active; khóa account chặn login; Markdown có delete/reindex | `test_admin_can_edit_profile_role_and_lock_accounts`, `test_admin_can_reindex_and_delete_knowledge_document` | Email/SSO, audit thay đổi role/account, phê duyệt IT nội dung runbook |
| FR-21 — Dashboard/report | Tổng hợp ticket, SLA, resolution duration, feedback, daily/category, Agent; export CSV chỉ Admin | `test_analytics_and_ticket_filters`, `test_admin_can_export_ticket_report_only` | KPI thật và đối soát báo cáo; chưa tính self-service outcome hoặc export PDF/XLSX |
| FR-09 — Analytics | `/analytics`, loại trừ ticket lưu trữ | `test_analytics_and_ticket_filters`, `test_admin_archives_ticket_without_removing_audit` | Định nghĩa KPI và ý nghĩa chỉ số theo quy trình thật |
| FR-11/12 / US-06 — Sửa và lưu trữ mềm | `PUT /tickets/{id}`, `DELETE /tickets/{id}` | `test_owner_can_edit_new_ticket_and_priority_recalculates_sla`, `test_ticket_edit_is_restricted_after_processing_starts`, `test_admin_archives_ticket_without_removing_audit` | E2E quyền hiển thị nút/empty-state và kiểm soát retention |
| FR-13/14 / US-07 — Quản trị user/KB | `/admin/users`, `POST /knowledge`; validation, PBKDF2, refresh retrieval cache | `test_admin_can_create_user_without_exposing_password`, `test_admin_can_ingest_valid_markdown_and_retriever_refreshes`, `test_non_admin_cannot_ingest_knowledge_and_non_markdown_is_rejected`, `test_knowledge_upload_rejects_invalid_documents` | Kiểm thử UI browser; phê duyệt chuyên gia cho runbook; đổi/reset mật khẩu |
| UX — Tra cứu → bàn giao | UI tự cuộn tới kết quả; nút handoff điền nội dung, category và priority gợi ý; giá trị vẫn sửa được trước khi gửi; vai trò có dashboard khác nhau | Syntax check JavaScript; API triage tests; chưa có browser automation | E2E trên trình duyệt, task timing/usability, so sánh cùng tác vụ trên kênh hiện tại |
| Health / migration | `/health`; migration archive, status, user profile, chat và attachment metadata; non-demo startup guard | `test_health_reports_database_unavailability`, `test_database_migration_adds_archive_timestamp_to_existing_ticket_table`, `test_non_demo_startup_refuses_unchanged_seeded_demo_credentials`, `test_initial_non_demo_startup_creates_only_provisioned_admin` | Test khôi phục backup, lỗi đĩa/permissions và nâng cấp có dữ liệu production |

## 2. Lệnh kiểm tra lặp lại

```powershell
py -m ruff check app tests scripts
node --check app/static/app.js
py -m compileall -q app tests scripts
py -m pytest --cov=app --cov-report=term-missing --cov-report=xml
py -m scripts.evaluate_rag
```

Coverage đo trên Python backend trong lần chạy cụ thể; không bao gồm chất lượng nội dung, UI browser hay hiệu quả sử dụng. Ruff chạy tập rule cơ bản và rule `S` của Bandit-style lint; hai truy vấn SQL động được miễn `S608` vì identifier chỉ đến từ allow-list/nội bộ, còn input vẫn parameterized. Cấu hình miễn trừ cần được xem lại nếu thay đổi cách tạo câu SQL.

## 3. Bằng chứng chưa có

- Không có browser E2E, load test, staging/deployment run, uptime monitoring hoặc usability test trong repository. Attachment chưa tích hợp antivirus scan.
- Tập 30 câu hỏi RAG là draft tự biên soạn, chưa được chuyên gia độc lập duyệt; kết quả retrieval không đo độ đúng câu trả lời.
- Chưa có tổ chức/người dùng nghiệp vụ xác nhận acceptance criteria, runbook, giờ SLA hay KPI.
- Kết quả chạy local không tự động trở thành minh chứng CI; cần lưu URL/run ID/artifact sau khi workflow chạy trên GitHub.
