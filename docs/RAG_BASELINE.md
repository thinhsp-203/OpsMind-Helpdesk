# Kết quả baseline truy xuất RAG

**Ngày chạy:** 05/10/2026\
**Công cụ:** `py -m scripts.evaluate_rag`\
**Mã nguồn:** BM25 baseline trong `app/rag.py`; 9 tài liệu Markdown tại thời điểm chạy này (hiện có 30); title-term boost, kết quả top-k chỉ giữ một đoạn tốt nhất cho mỗi tài liệu để tránh lặp nguồn\
**Tập câu hỏi:** `data/evaluation/rag_questions.csv` (30 câu do nhóm/AI hỗ trợ soạn; cần người hướng dẫn/chuyên gia rà soát độc lập).

## Kết quả lần chạy local

| Chỉ số | Kết quả |
|---|---:|
| Context hit@3 trên câu in-scope | 28/28 (100%) |
| Từ chối truy xuất trên câu out-of-scope | 2/2 |
| Latency retrieval median | 0.75 ms |
| Latency retrieval p95 | 0.80 ms |

## Diễn giải và giới hạn

- Kết quả 28/28 là hit rate trên tập nhỏ tự soạn, từ khóa/ground truth hiện biết trước; **không phải đánh giá độc lập, không chứng minh tổng quát hóa và không chứng minh câu trả lời faithful**.
- Hai câu out-of-scope quá ít để ước lượng tỷ lệ từ chối đáng tin cậy.
- Lần chạy cập nhật 05/10/2026 sau khi thêm liên kết nguồn cho 6 runbook trên Windows/Python 3.14.7: latency đo trực tiếp hàm retrieval trong tiến trình local (median 0.75 ms, p95 0.80 ms); số đo biến thiên theo lần chạy và chưa ổn định. Không tính HTTP, render, tải tài liệu đầu tiên, concurrency hay thời gian người dùng; không dùng để cam kết p95 API hoặc 50 RPS.
- Giao diện người dùng trình bày nguồn tốt nhất trước và thu gọn nguồn phụ, không hiển thị điểm BM25 cho nhân viên; điểm vẫn có trong API phục vụ kiểm thử/đánh giá nội bộ.
- Với truy vấn tự nhiên “Team đang cần kết nối VPN để làm việc tại nhà”, bộ test xác nhận runbook VPN đứng đầu sau khi loại từ nối và tăng trọng số tiêu đề; đây là kiểm tra truy vấn đơn, không thay cho đánh giá độc lập trên mẫu đa dạng.
- Triage category/priority là rule-based suggestion chạy sau truy xuất; chưa được chấm precision/recall trên ticket có nhãn IT và không nằm trong chỉ số hit@3/refusal.
- Chưa đo Faithfulness, Answer Relevance, Ragas/TruLens, SUS, hiệu quả task hoặc mức độ tự giải quyết ticket.
- Trước khi đưa vào luận văn: xác nhận ground truth với người có chuyên môn, bổ sung câu hỏi paraphrase/typo và out-of-scope, chạy lại trên môi trường đã chốt; lưu commit, cấu hình và output gốc.

## Cập nhật AUD-19: Phân định Regression Gate & Khóa mã băm SHA-256 (21/10/2026)

- **Dataset Hashes (Khóa cố định):**
  - `rag_questions.csv` (`1.0.0-draft`): `9a0fc80667527170c7dad3476a26374a5183a7b8374795b6ec35d1482ae5ad4d` (30 câu)
  - `rag_holdout.csv` (`1.0.0-frozen`): `aaaf9673ed6d886ff5faa46f2a0bbcff92629cb024acd0cefb9e763706fad872` (60 câu)
- **Phân định phạm vi:** Tập 60 câu `rag_holdout.csv` là **Frozen Fixed Regression Benchmark Gate Set** nhằm bảo vệ hệ thống không thoái lui tri thức trên 30 runbook hiện có. Đây không phải tập blinded evaluation độc lập.
- **Tách bạch chỉ số Retrieval Gate và Answer/Evidence Rubric:**
  - *Retrieval CI Gate:* Dev Hit@3 = 100.0%, Holdout Hit@1 = 76.7%, Holdout Hit@3 = 100.0%, Holdout MRR@3 = 0.878, Pure OOS Refusal = 100.0%, Near-domain OOS Refusal = 100.0%.
  - **Số liệu lịch sử, không còn dùng làm chất lượng câu trả lời (đính chính 29/10/2026):** Holdout Evidence Hit@3 = 100.0% (30/30 câu in-scope trích xuất được bằng chứng), In-scope Average Evidence Coverage = 95.6%, Out-of-scope Refusal Justification = 100.0% (30/30 câu out-of-scope đưa ra giải thích từ chối rõ ràng).

## Đính chính công cụ đánh giá — 29/10/2026

Các mã băm tại mục AUD-19 phía trên là metadata CRLF cũ; mã băm chuẩn UTF-8/LF hiện tại nằm trong `data/evaluation/DATASET_CARD.md` và `scripts/evaluation_support.py`. Nội dung CSV không thay đổi.

Bộ chấm cũ chấp nhận một từ trùng trong cụm bằng chứng, kể cả trong tiêu đề. Bản sửa chỉ chấp nhận nguyên cụm trong nội dung và công bố là chẩn đoán từ vựng. Không dùng coverage cũ để khẳng định Faithfulness, so sánh cải thiện hay đặt ngưỡng chất lượng cho bộ chấm mới. Các ngưỡng truy xuất và từ chối vẫn được giữ nguyên. Xem `docs/REVIEW_FIXES_2026-10-29.md` cho kết quả chạy lại và giới hạn.

## Ablation tiền xử lý và ngưỡng tài liệu tham khảo — 07/11/2026

**Lệnh:** `py -m scripts.ablation_rag`\
**Môi trường:** macOS 26 (arm64), Python 3.11.18, SQLite tạm; 30 runbook đã xuất bản, 115 đoạn.\
**Kiểm tra trước khi in số:** cấu hình E tái tạo đúng thứ hạng của `app/rag.py` trên toàn bộ câu in-scope.

Mỗi cấu hình thêm một bước vào cấu hình trước, cùng công thức BM25 (k1 = 1,2; b = 0,75). Cổng ngoài phạm vi bị tắt để mọi cấu hình xếp hạng cùng một tập câu in-scope. Tập "holdout không dấu" là chính các câu holdout được bỏ dấu tự động; nhãn giữ nguyên, không tạo dữ liệu mới.

| Cấu hình | Dev (n=28) Hit@1 / Hit@3 / MRR@3 | Holdout (n=30) | Holdout không dấu (n=30) |
|---|---|---|---|
| A. BM25 thô (giữ dấu) | 78,6% / 92,9% / 0,851 | 96,7% / 100% / 0,983 | 73,3% / 93,3% / 0,833 |
| B. A + bỏ dấu | 78,6% / 92,9% / 0,851 | 96,7% / 100% / 0,983 | 96,7% / 100% / 0,983 |
| C. B + từ dừng | 82,1% / 92,9% / 0,875 | 100% / 100% / 1,000 | 100% / 100% / 1,000 |
| D. C + đồng nghĩa & từ ghép | 82,1% / 100% / 0,905 | 96,7% / 96,7% / 0,967 | 96,7% / 96,7% / 0,967 |
| E. D + trọng số tiêu đề (hệ thống) | 82,1% / 100% / 0,911 | 96,7% / 96,7% / 0,967 | 96,7% / 96,7% / 0,967 |

Diễn giải:

- Bỏ dấu không thay đổi kết quả khi câu hỏi gõ có dấu, nhưng nâng Hit@1 từ 73,3% lên 96,7% khi người dùng gõ không dấu.
- Từ đồng nghĩa và từ ghép giúp tập dev (Hit@3 92,9% → 100%) nhưng làm holdout giảm một câu (H03). Từ điển đã được tinh chỉnh trên chính các tập này, nên mức tăng ở C–E là cận trên lạc quan, không phải khả năng tổng quát hóa.
- BM25 thô đã đạt Hit@3 100% trên holdout: tập này quá dễ để phân biệt các cấu hình. Cần một tập câu hỏi mới do người khác soạn, chưa dùng để chỉnh từ điển.

### Ngưỡng độ phủ cho tài liệu tham khảo trong chat

Trợ lý chỉ gợi ý runbook đã xuất bản (trường `kb_references`) khi độ phủ truy vấn ≥ 0,5. Độ phủ là tỷ lệ trọng số IDF của các từ trong câu hỏi xuất hiện trong runbook. Điểm BM25 thô không tách được kết quả đúng/sai: "màn hình phụ bị sọc" xếp BitLocker đứng đầu với điểm 11,4, nhưng độ phủ chỉ 0,37. Quy tắc đóng an toàn: nếu kết quả đứng đầu không đạt ngưỡng thì không hiện tham khảo nào, kể cả khi kết quả xếp dưới đạt. Ví dụ "Quên mã BitLocker recovery key": BitLocker đứng đầu với độ phủ 0,48, nên AD lockout và Wi-Fi (xếp dưới) cũng không được hiện; câu hỏi chuyển sang bàn giao IT.

| Ngưỡng | Hiện | Đúng | Precision | Recall |
|---:|---:|---:|---:|---:|
| 0,0 | 58 | 52 | 89,7% | 100% |
| 0,4 | 54 | 50 | 92,6% | 96,2% |
| **0,5** | **51** | **49** | **96,1%** | **94,2%** |
| 0,6 | 49 | 48 | 98,0% | 92,3% |
| 0,7 | 44 | 43 | 97,7% | 82,7% |

Đo trên top-1 của 58 câu in-scope (dev + holdout). Ngưỡng được chọn trên chính tập này, nên precision thực tế với câu hỏi mới có thể thấp hơn. Bảng chỉ đo việc runbook có đúng chủ đề hay không, không đo hướng dẫn có giải quyết được sự cố.
