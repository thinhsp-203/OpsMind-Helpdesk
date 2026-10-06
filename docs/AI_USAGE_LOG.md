# Nhật ký sử dụng AI

Nhật ký ghi các phần có hỗ trợ AI và việc nhóm cần tự rà soát. Không dùng nội dung này thay cho lịch sử commit/PR hoặc xác nhận của giảng viên.

| Giai đoạn | Yêu cầu đưa cho AI | Kết quả được hỗ trợ | Rà soát và điều chỉnh |
|---|---|---|---|
| Tạo prototype | Dựa trên kế hoạch Helpdesk RAG, tạo ứng dụng demo FastAPI có ticket, JWT, RAG local và UI | Khung API, bộ runbook Markdown, UI và tests | Chạy pytest và smoke test API; thấy bản đầu dùng dữ liệu in-memory và phân quyền ticket chưa đủ chặt |
| Cải thiện prototype | “Hoàn thiện hết lại cho tôi. Hiện chạy rồi đấy nhưng sơ sài.” | Tài liệu bối cảnh/SRS/SDD/thực nghiệm, SQLite store, FSM/RBAC, UI tiếng Việt và test mở rộng | Chỉnh lưu bền vững, phân tách quyền User/IT, trích dẫn tài liệu; cập nhật docs để không tuyên bố số liệu chưa đo |
| Đánh giá và CI | Bổ sung bộ câu hỏi RAG, baseline có thể tái chạy và hoàn thiện CI | CSV 30 câu, script hit@3/refusal/latency, lint Ruff, coverage và Docker build | Đo local đạt hit@3 28/28 và từ chối 2/2 trên tập tự soạn; ghi rõ đây không phải ground truth độc lập hoặc đánh giá faithfulness |
| Theo dõi SUPPLEMENT_GUIDE và bổ sung | Yêu cầu đối chiếu guide, thống nhất song ngữ, dùng PostgreSQL và bổ sung nguồn/runbook thực tế | PostgreSQL adapter + Compose/CI integration test; bộ dịch giao diện VI/EN; hướng dẫn sử dụng/triển khai; 6 runbook có liên kết nguồn Microsoft/Fortinet đã kiểm tra | 41 pytest pass, 1 PostgreSQL integration test skip local vì không có DB/Docker; CI sẽ chạy với PostgreSQL service. Node i18n coverage test pass; chưa có browser E2E. Retrieval baseline sau nội dung mới vẫn 28/28 in-scope và 2/2 refusal, nhưng tập câu hỏi còn draft |
| Nâng cấp LLM Synthesis & Chuẩn hóa tài liệu | Nâng cấp RAG hoàn chỉnh với bước LLM generation tùy chọn có fallback an toàn; dọn dẹp cấu trúc thư mục tài liệu theo chuẩn đồ án | Hàm `synthesize_answer_with_llm` trong `app/rag.py`, cấu hình biến môi trường trong `app/config.py`, 3 unit test tự động mới; di chuyển tài liệu phân tích nội bộ vào `docs/internal/`; cập nhật `.gitignore` | 44/44 pytest pass; cơ chế grounding ràng buộc chặt chẽ tránh ảo giác; tự động fallback về template tĩnh nếu không có API key hoặc lỗi mạng; không làm ảnh hưởng tính ổn định khi chạy offline |

## Lỗi/giới hạn do rà soát trong bản đầu và cách xử lý

1. Ticket/audit chỉ lưu trong RAM nên mất khi tiến trình khởi động lại. **Sửa:** lưu qua backend SQLite/PostgreSQL; kiểm thử tạo và đọc ticket qua API, cùng integration test PostgreSQL trong CI.
2. API trước đây để End-user đổi trạng thái và xem toàn bộ ticket. **Sửa:** giới hạn danh sách/chi tiết theo chủ sở hữu; chỉ Agent/Admin điều phối; có kiểm thử quyền.
3. RAG trước đây trả top kết quả kể cả không liên quan. **Sửa:** BM25 + ngưỡng relevance và trả trạng thái không đủ bằng chứng; bổ sung truy vấn ngoài phạm vi trong test.
4. Giao diện trước đây đưa nội dung ticket không tin cậy vào `innerHTML`. **Sửa:** dựng phần ticket, bình luận và trích đoạn bằng DOM/textContent.
5. Bản kế hoạch có metric mục tiêu nhưng chưa có số liệu thực nghiệm. **Sửa:** tài liệu mới đánh dấu rõ mục tiêu chưa đo và cung cấp biểu mẫu để nhóm thu thập dữ liệu thật.
6. RAG nguyên bản chỉ dừng ở trích đoạn BM25 mà thiếu bước LLM generation tự nhiên theo định nghĩa đầy đủ của RAG. **Sửa:** bổ sung hàm tổng hợp `synthesize_answer_with_llm` hỗ trợ OpenAI/Groq API kèm system prompt ràng buộc chặt vào Runbook; thiết kế fallback 100% về template tĩnh khi không có API key hoặc sự cố mạng; bổ sung 3 test tự động bao quát cả ca thành công và ca lỗi.

Các mục “sửa” ở trên là thay đổi trong prototype; nhóm cần đối chiếu lịch sử source control và kiểm tra lại thủ công trước khi nộp.
