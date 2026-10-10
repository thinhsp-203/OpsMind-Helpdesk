# Kết quả đánh giá truy xuất RAG

**Ngày chạy:** 10/10/2026\
**Công cụ:** `python -m scripts.evaluate_rag`\
**Mã nguồn:** BM25 trong `app/rag.py` trên 30 runbook Markdown; tăng trọng số tiêu đề; mỗi tài liệu chỉ giữ một đoạn tốt nhất trong top-k.\
**Tập câu hỏi:** `data/evaluation/rag_questions.csv`, 96 câu chia 3 phần (cột `split`):

| Split | Số câu | Vai trò |
|---|---:|---|
| `seed` | 30 (28 trong phạm vi, 2 ngoài phạm vi) | Bộ câu gốc, soạn cùng lúc với runbook nên dùng từ vựng giống tài liệu |
| `dev` | 36 (24 / 12) | Câu diễn đạt kiểu người dùng thật (không dấu, viết tắt, tiếng lóng IT); **dùng để tinh chỉnh** |
| `holdout` | 30 (20 / 10) | Soạn **trước** khi tinh chỉnh và **không dùng để tinh chỉnh**; đây là số liệu nên báo cáo |

Một câu có thể có nhiều tài liệu đúng (phân tách bằng `;` trong `expected_source`).

## Các thay đổi trong bộ truy xuất (10/10/2026)

1. **Từ điển song ngữ Việt–Anh (`PHRASES`)**: phần lớn runbook viết bằng tiếng Anh nên câu hỏi tiếng Việt trước đây gần như không khớp từ khóa. Cụm từ tiếng Việt (đã bỏ dấu) được ánh xạ sang thuật ngữ tiếng Anh, ưu tiên cụm dài nhất (ví dụ "màn hình xanh" → bsod/blue/screen, "không in được" → printer/print).
2. **Chuẩn hóa "Wi-Fi"**: trước đây "Wi-Fi" bị tách thành "wi" + "fi" nên truy vấn "wifi" không bao giờ khớp runbook Wi-Fi.
3. **Rút gọn hậu tố tiếng Anh nhẹ**: fail/failed/fails, update/updates/updating được đưa về cùng một dạng.
4. **Mở rộng danh sách hư từ tiếng Việt** (khi, này, thì, rất…): các âm tiết này xuất hiện trong runbook tiếng Việt và từng khiến câu ngoài phạm vi khớp nhầm.
5. **Cơ chế từ chối câu ngoài phạm vi**: điểm BM25 không so sánh được giữa các truy vấn, nên ngưỡng cố định `MIN_RELEVANCE = 0.12` gần như không từ chối được câu nào. Nay câu hỏi chỉ được trả lời khi chứa ít nhất một **thuật ngữ IT** (từ điển song ngữ + từ tiếng Anh trong tiêu đề runbook + từ viết tắt trong tiêu đề tiếng Việt) và đoạn được chọn cũng chứa thuật ngữ đó. Runbook do Admin nạp mới sẽ tự động mở rộng danh sách này.

## Kết quả trước và sau khi sửa

| Split | Chỉ số | Trước | Sau |
|---|---|---:|---:|
| seed | hit@3 | 28/28 (100%) | 28/28 (100%) |
| seed | hit@1 / MRR@3 | 67,9% / 0,815 | 78,6% / 0,875 |
| seed | Từ chối ngoài phạm vi | 2/2 | 2/2 |
| dev | hit@3 | 14/24 (58,3%) | 24/24 (100%) |
| dev | Từ chối ngoài phạm vi | 0/12 (0%) | 12/12 (100%) |
| **holdout** | **hit@3** | 18/20 (90%) | **20/20 (100%)** |
| **holdout** | **hit@1 / MRR@3** | 75% / 0,825 | **90% / 0,950** |
| **holdout** | **Từ chối ngoài phạm vi** | 1/10 (10%) | **8/10 (80%)** |
| Tổng 96 câu | hit@3 | 60/72 (83,3%) | 72/72 (100%) |
| Tổng 96 câu | Từ chối ngoài phạm vi | 3/24 (12,5%) | 22/24 (91,7%) |

Latency truy xuất (đo trong tiến trình, không gồm HTTP): median ≈ 2,6 ms, p95 ≈ 6,4 ms; số đo biến thiên theo máy và lần chạy.

## Lỗi còn lại trên holdout (giữ nguyên, không tinh chỉnh theo)

- **H28** "Viết email chúc mừng sinh nhật sếp": chứa thuật ngữ IT "email" nên không bị từ chối. Đây là giới hạn của phương pháp dựa trên từ khóa: không hiểu ý định câu hỏi.
- **H30** "Đặt xe đưa đón khách hàng": "hàng" trùng với "hang" (treo máy) trong từ điển sau khi bỏ dấu. Đây là nhược điểm của việc bỏ dấu tiếng Việt.

## Diễn giải và giới hạn

- Từ điển song ngữ được xây dựng thủ công khi xem các lỗi của tập `dev`; vì vậy số liệu `dev` mang tính lạc quan. Số liệu nên trích dẫn là `holdout`.
- Tập holdout vẫn nhỏ (20 + 10 câu) và do nhóm tự soạn; cần người hướng dẫn hoặc chuyên gia IT rà soát độc lập và bổ sung câu hỏi thật từ người dùng.
- Phương pháp vẫn là truy xuất từ vựng (lexical). Hướng phát triển: tìm kiếm lai BM25 + embedding đa ngữ để xử lý từ đồng nghĩa và ý định câu hỏi mà không cần từ điển thủ công.
- Chỉ số hit@k và từ chối chỉ đo bước truy xuất; chưa đo Faithfulness, Answer Relevance (Ragas/TruLens), SUS hay tỷ lệ tự giải quyết ticket.
- Triage category/priority là gợi ý dựa trên luật, chạy sau truy xuất; chưa được chấm precision/recall.
