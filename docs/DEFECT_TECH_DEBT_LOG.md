# Sổ lỗi và nợ kỹ thuật

**Trạng thái:** danh sách làm việc nội bộ cho prototype; các mục chưa liên kết issue tracker/PR. Không dùng tài liệu này thay cho lịch sử defect chính thức của nhóm.

## 1. Lỗi được phát hiện và xử lý trong đợt hoàn thiện

| ID | Mức ảnh hưởng | Hiện tượng / tái hiện | Sửa đổi | Kiểm chứng |
|---|---|---|---|---|
| HD-01 | Cao | Fixture API test gọi reset DB theo cấu hình ứng dụng, có thể xóa dữ liệu demo khi chạy test | Fixture trỏ SQLite sang `tmp_path` riêng cho từng test | Toàn bộ API tests dùng DB cách ly |
| HD-02 | Cao | Chuyển sang `DEMO_MODE=false` trên DB còn credential demo có thể giữ nguyên user/password mẫu | Startup từ chối DB còn credential mặc định; hỗ trợ bootstrap Admin trên DB rỗng | `tests/test_store.py` |
| HD-03 | Trung bình | Admin không có UI để tạo tài khoản/nạp tri thức; RAG phải dựa trên file có sẵn | Thêm UI/API quản trị user và upload Markdown giới hạn/kiểm tra; làm mới cache retrieval | API tests cho quyền, validation, duplicate, cache refresh |
| HD-04 | Trung bình | Ticket thiếu thao tác sửa và lưu trữ có audit | Thêm edit có ràng buộc trạng thái; archive mềm chỉ Admin; giữ audit | API tests edit/state/ACL/archive/analytics |
| HD-05 | Thấp | Health check trước đây chỉ phản ánh route chạy, không thử kết nối database | `/health` trả 503 khi SQLite/PostgreSQL không sẵn sàng | `test_health_reports_database_unavailability` |
| HD-06 | Thấp | Tên file Markdown Unicode không tạo slug có thể gây lỗi nội bộ | Trả lỗi validation 422 thay vì lỗi 500 | `test_knowledge_upload_rejects_invalid_documents` |
| HD-07 | Trung bình | Trang đăng nhập hiển thị thông tin demo cả khi cấu hình non-demo | Ẩn thông tin demo theo cấu hình công khai; bỏ điền sẵn user/password | API test kiểm tra `/config` và nội dung HTML; chưa có browser E2E |
| HD-08 | Trung bình | Gửi ticket thành công rồi JavaScript đọc `event.currentTarget` sau `await`, gây `Cannot read properties of null (reading 'reset')` | Lưu form element trước khi gửi request; dùng tham chiếu đã lưu để reset | Regression được rà theo luồng submit; browser E2E vẫn cần bổ sung |
| HD-09 | Thấp | Một runbook có thể chiếm nhiều vị trí top-k và lặp nguồn, làm câu trả lời dài/rối | Giữ tối đa một passage tốt nhất cho mỗi source; giao diện thu gọn nguồn phụ | `test_rag_results_do_not_repeat_the_same_runbook`, bộ đánh giá 30 câu |
| HD-10 | Trung bình | Từ nối tiếng Việt như “đang/cần/kết nối/việc” lấn từ khóa chủ đề trong một câu hỏi VPN tự nhiên | Bổ sung stop words thông dụng; dùng title-term boost để tăng trọng số chủ đề tài liệu | `test_rag_results_do_not_repeat_the_same_runbook` xác nhận VPN đứng đầu; đánh giá draft 30 câu |
| HD-11 | Cao | Ticket thiếu lịch sử chat, tệp, xác nhận của người gửi và rating; Admin/Agent thiếu màn hình cá nhân/báo cáo theo đặc tả | Thêm chat session/feedback, attachment có kiểm soát quyền và giới hạn, FSM chờ/chuyển cấp, xác nhận/rating, quản lý user/KB và thống kê/export CSV | API regression tests; chưa có browser E2E |

## 2. Nợ kỹ thuật/rủi ro còn mở

| ID | Ưu tiên | Rủi ro / giới hạn | Điều kiện đóng |
|---|---|---|---|
| TD-01 | P1 | Chưa có staging/deploy, HTTPS termination, rate limit, backup/restore hoặc giám sát uptime | Triển khai môi trường thử nghiệm an toàn, có runbook khôi phục và minh chứng |
| TD-02 | P1 | Chưa có người dùng thật, phỏng vấn, SUS, xác nhận pain point hay ground truth IT | Có đồng ý tham gia, dữ liệu ẩn danh, protocol và kết quả thật được GVHD duyệt |
| TD-03 | P1 | Chưa có browser E2E và khả năng tiếp cận UI chỉ được kiểm bằng code/test API | Chọn runner trình duyệt, thêm smoke tests các vai trò và luồng chính |
| TD-04 | P1 | Chưa có reset mật khẩu, role/account-change audit, token refresh/revocation; khóa hoặc đổi quyền được API áp dụng ở request tiếp theo nhưng chưa có UX phiên hết hạn | Thiết kế vòng đời tài khoản/token, audit thay đổi và kiểm thử UX/session invalidation |
| TD-05 | P2 | RAG là BM25 lexical baseline; bộ synonym/tập 30 câu nhỏ, dễ thiên lệch từ khóa | Chuyên gia duyệt KB/ground truth; đánh giá paraphrase, typo, out-of-scope và câu trả lời có rubric |
| TD-06 | P2 | SLA theo giờ lịch; đổi ưu tiên tính lại hạn từ lúc sửa, chưa có lịch làm việc/holiday | Chốt business rule với stakeholder và bổ sung lịch làm việc nếu cần |
| TD-07 | P2 | PostgreSQL Compose và SQLite local đã hỗ trợ lưu bền vững, nhưng chưa có migration dữ liệu, backup/restore, KB versioning/rollback hay quy trình review nội dung | Định nghĩa quản trị nội dung, migration/backup/version và quyền phê duyệt trước pilot |
| TD-08 | P2 | CI chỉ cấu hình lint/test/retrieval/Docker build; chưa có workflow deploy hoặc run thành công được xác nhận | Repository/runner thật có pipeline run, artifact và staging approval |
| TD-09 | P3 | Chưa có test tải 50 RPS; con số trong NFR vẫn là mục tiêu chưa đo | Benchmark với cấu hình/phương pháp được duyệt và báo cáo error rate/latency |
| TD-10 | P2 | CI có static source lint nhóm `S`, chưa có dependency/image vulnerability audit | Bổ sung scanner, xử lý findings và giữ report theo run CI |
| TD-11 | P1 | Attachment chỉ allow-list và giới hạn dung lượng; chưa quét virus, quota tổng, retention hay sao lưu tệp | Chọn malware scanner, chính sách dữ liệu/retention và kiểm thử khôi phục trước pilot dữ liệu thật |
