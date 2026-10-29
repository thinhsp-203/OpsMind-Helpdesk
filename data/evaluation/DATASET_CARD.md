# Dataset Card: OpsMind Helpdesk RAG Evaluation Sets

**Phiên bản:** `1.0.0-frozen`
**Ngày khóa dữ liệu (Freeze Date):** 21/10/2026
**Trạng thái Audit:** Giải quyết finding **AUD-19** (Holdout & Quality Gate Independence).

---

## 1. Danh mục tập dữ liệu & Mã băm toàn vẹn (Cryptographic Hashes)

| Tệp dữ liệu | Phiên bản | Số câu | In-scope | Out-of-scope | Dung lượng | SHA-256 Checksum |
|---|---|---:|---:|---:|---:|---|
| `rag_questions.csv` | `1.0.0-draft` | 30 | 28 | 2 | 4,614 bytes | `8e1bf0f6a4024e3515ef8f4a8077e3558bd29dcbff426bf3182a5d112781c994` |
| `rag_holdout.csv` | `1.0.0-frozen` | 60 | 30 | 30 | 10,463 bytes | `d272c6cc0540745dc4b0d2590f1eb208d2968e7d55b0cfca2ebce1e4d53abbaf` |

**Đính chính 29/10/2026:** mã băm cũ được tính trên CRLF (Windows). Bảng trên tính trên đúng byte UTF-8/LF đã lưu trong Git; `.gitattributes` cố định LF khi checkout. Không sửa câu hỏi, nhãn, thứ tự hay phiên bản nội dung. Đây là sửa metadata toàn vẹn, không phải tái đóng băng dữ liệu sau khi đánh giá.

Mọi sự thay đổi về nội dung, thứ tự hoặc cấu trúc của các tệp trên sẽ làm thay đổi SHA-256 và lập tức kích hoạt lỗi trượt kiểm thử CI tại `tests/test_rag_dataset.py::test_evaluation_datasets_provenance_and_frozen_hash`.

---

## 2. Phân định vai trò & Ranh giới kỹ thuật (AUD-19 Scope)

### 2.1 Vai trò thực tế của `rag_holdout.csv`
- Tập 60 câu hỏi `rag_holdout.csv` được phân định rõ ràng là **Frozen Fixed Regression Benchmark Gate Set** (Tập kiểm thử hồi quy cố định đã đóng băng).
- **Mục đích:** Bảo vệ hệ thống RAG không bị suy thoái (non-regression) đối với các kịch bản sự cố CNTT đã được định nghĩa trong 30 Runbook doanh nghiệp (Active Directory, BitLocker, FortiClient VPN, Outlook, Print Spooler, Network DHCP, BSOD, Disk 100%, v.v.).
- **Giới hạn quan trọng:** Như được ghi nhận minh bạch trong `docs/AI_USAGE_LOG.md` (mục 8), từ điển RAG (`rag_dictionary.json`), từ dừng và trọng số tiêu đề đã từng được tinh chỉnh để giải quyết sự cạnh tranh BM25 giữa các tài liệu tương tự nhằm đạt Hit@3 tối đa trên tập này. Do đó:
  - Kết quả Hit@3 = 100% trên `rag_holdout.csv` chứng minh **độ tin cậy hồi quy (regression reliability)** của hệ thống tri thức hiện có.
  - Kết quả này **KHÔNG đại diện cho độ tổng quát hóa độc lập (independent generalization)** trên các câu hỏi hoàn toàn mới ngoài phân phối (out-of-distribution) chưa từng thấy.

---

## 3. Cấu trúc trường dữ liệu & Tiêu chí gán nhãn (Annotation Protocol)

Mỗi tệp CSV bao gồm 6 trường bắt buộc:
1. `id`: Mã định danh duy nhất của câu hỏi (`Q01`-`Q30` đối với dev, `H01`-`H60` đối với holdout).
2. `question`: Câu hỏi tự nhiên của người dùng bằng tiếng Việt hoặc tiếng Anh.
3. `topic`: Chủ đề kỹ thuật (VPN, Security, Printer, Email, Network, Pure OOS, Near-domain OOS, v.v.).
4. `expected_source`: Tên tệp Markdown runbook đích kỳ vọng được truy xuất đứng trong top kết quả (đối với in-scope); để trống đối với out-of-scope.
5. `required_evidence`: Danh sách các bằng chứng / từ khóa kỹ thuật cốt lõi (ngăn cách bởi dấu chấm phẩy `;`) bắt buộc phải xuất hiện trong ngữ cảnh truy xuất để câu trả lời có căn cứ xác thực (grounded). Đối với câu out-of-scope, trường này định nghĩa lý do từ chối ngoài phạm vi.
6. `scope`: `in_scope` (thuộc phạm vi IT Helpdesk) hoặc `out_of_scope` (ngoài phạm vi cần từ chối).

### Phân rã Out-of-Scope (30 câu holdout):
- **Pure OOS (15 câu):** Hoàn toàn không liên quan đến CNTT (thời tiết, nấu ăn, du lịch, âm nhạc, đồ gia dụng). Hệ thống phải từ chối 100%.
- **Near-domain OOS (15 câu):** Các sự cố thiết bị tiêu dùng cá nhân hoặc dịch vụ dân dụng dễ gây nhầm lẫn (máy giặt Electrolux, tivi Sony, game online, truyền hình cáp). Hệ thống phải nhận diện ranh giới doanh nghiệp và từ chối.

---

## 4. Tách biệt chỉ số CI Gate & Tiêu chuẩn chấm điểm bằng chứng (Answer Rubric)

Theo yêu cầu kiểm toán AUD-19, hệ thống phân tách rạch ròi hai tầng đo lường:

### Tầng 1: Retrieval CI Gate (scripts/evaluate_rag.py & pytest)
- **Hit@1 Rate:** >= 60%
- **Hit@3 Rate:** >= 85%
- **MRR@3:** >= 0.70
- **False-Positive Refusal Rate:** <= 5%
- **Out-of-Scope Refusal Rate:** Pure OOS >= 90%, Near-domain OOS >= 80%

Đây là ngưỡng hồi quy; kết quả đo phụ thuộc phiên bản mã và kho tri thức. Output chạy lại ngày 29/10/2026 lưu tại `docs/verification/2026-10-29/rag-evaluation.txt`, không thay số đo mới vào các bản ghi lịch sử.

### Tầng 2: Chẩn đoán từ vựng trong ngữ cảnh (không phải Answer Rubric)
- Chỉ tính khi toàn bộ cụm bằng chứng xuất hiện liên tiếp theo ranh giới từ trong **nội dung đoạn truy xuất**, không tính tiêu đề, không tính một từ trùng đơn lẻ.
- Chuẩn hóa Unicode NFC, chữ hoa/thường và dấu câu; giữ nguyên dấu tiếng Việt. Bằng chứng rỗng không được tính điểm hoàn hảo.
- `evidence_hit_rate` / `evidence_coverage_avg` là chỉ số từ vựng phục vụ chẩn đoán, **không phải Faithfulness/Answer Relevance**. Không dùng ngưỡng của bộ chấm một-từ cũ làm cổng chất lượng cho cách chấm mới.
- Phép khớp cụm từ vẫn không hiểu phủ định, điều kiện, quyền thực hiện hoặc diễn đạt tương đương. Cần chấm câu trả lời riêng bởi người có chuyên môn trước khi công bố chất lượng ngữ nghĩa.
- **Refusal Justification Rate:** >= 90%; chỉ kiểm tra lời từ chối có giải thích ngoài phạm vi, không chứng minh toàn bộ câu trả lời đúng.
- Số 95,6% coverage và 100% evidence hit trong báo cáo cũ được tạo bằng cách chấm lỏng; không dùng làm kết quả hiện tại hay so sánh trước/sau. Kết quả mới và môi trường chạy lưu riêng.

---

## 5. Quy thức thu thập tập kiểm thử độc lập tương lai (Blinded Test Protocol)

Để đo lường độ tổng quát hóa độc lập và chất lượng câu trả lời (Faithfulness/Answer Relevance) trong giai đoạn tiếp theo:
1. **Nguồn dữ liệu:** Trích xuất ngẫu nhiên 100 ticket thực tế mới phát sinh từ người dùng cuối, ẩn danh hóa toàn bộ thông tin định danh cá nhân (PII).
2. **Gán nhãn độc lập:** 02 kỹ sư CNTT độc lập gán nhãn `expected_source` và `required_evidence`.
3. **Độ đồng thuận (Inter-Annotator Agreement):** Chỉ giữ các câu hỏi có chỉ số đồng thuận Cohen's Kappa >= 0.80.
4. **Đóng băng trước khi chạy (Pre-evaluation Freeze):** Tập dữ liệu độc lập phải được băm SHA-256 và lưu trữ tách biệt; tuyệt đối không dùng để điều chỉnh từ điển hoặc prompt trước khi đo lường kết quả baseline.
