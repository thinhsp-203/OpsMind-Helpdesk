# Kết quả baseline truy xuất RAG

**Ngày chạy:** 05/10/2026\
**Công cụ:** `py -m scripts.evaluate_rag`\
**Mã nguồn:** BM25 baseline trong `app/rag.py`; 9 tài liệu Markdown hiện có; title-term boost, kết quả top-k chỉ giữ một đoạn tốt nhất cho mỗi tài liệu để tránh lặp nguồn\
**Tập câu hỏi:** `data/evaluation/rag_questions.csv` (30 câu do nhóm/AI hỗ trợ soạn; cần người hướng dẫn/chuyên gia rà soát độc lập).

## Kết quả lần chạy local

| Chỉ số | Kết quả |
|---|---:|
| Context hit@3 trên câu in-scope | 28/28 (100%) |
| Từ chối truy xuất trên câu out-of-scope | 2/2 |
| Latency retrieval median | 1.00 ms |
| Latency retrieval p95 | 1.75 ms |

## Diễn giải và giới hạn

- Kết quả 28/28 là hit rate trên tập nhỏ tự soạn, từ khóa/ground truth hiện biết trước; **không phải đánh giá độc lập, không chứng minh tổng quát hóa và không chứng minh câu trả lời faithful**.
- Hai câu out-of-scope quá ít để ước lượng tỷ lệ từ chối đáng tin cậy.
- Lần chạy cập nhật 05/10/2026 trên Windows/Python 3.14.7: latency đo trực tiếp hàm retrieval trong tiến trình local; số đo biến thiên theo lần chạy và chưa ổn định. Không tính HTTP, render, tải tài liệu đầu tiên, concurrency hay thời gian người dùng; không dùng để cam kết p95 API hoặc 50 RPS.
- Giao diện người dùng trình bày nguồn tốt nhất trước và thu gọn nguồn phụ, không hiển thị điểm BM25 cho nhân viên; điểm vẫn có trong API phục vụ kiểm thử/đánh giá nội bộ.
- Với truy vấn tự nhiên “Team đang cần kết nối VPN để làm việc tại nhà”, bộ test xác nhận runbook VPN đứng đầu sau khi loại từ nối và tăng trọng số tiêu đề; đây là kiểm tra truy vấn đơn, không thay cho đánh giá độc lập trên mẫu đa dạng.
- Triage category/priority là rule-based suggestion chạy sau truy xuất; chưa được chấm precision/recall trên ticket có nhãn IT và không nằm trong chỉ số hit@3/refusal.
- Chưa đo Faithfulness, Answer Relevance, Ragas/TruLens, SUS, hiệu quả task hoặc mức độ tự giải quyết ticket.
- Trước khi đưa vào luận văn: xác nhận ground truth với người có chuyên môn, bổ sung câu hỏi paraphrase/typo và out-of-scope, chạy lại trên môi trường đã chốt; lưu commit, cấu hình và output gốc.
