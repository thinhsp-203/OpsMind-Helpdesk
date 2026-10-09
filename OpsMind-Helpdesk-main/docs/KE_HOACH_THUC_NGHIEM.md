# Kế hoạch kiểm thử và thực nghiệm

## 1. Trạng thái minh chứng

| Minh chứng | Trạng thái |
|---|---|
| API integration tests | Có trong `tests/` |
| Coverage report | Sinh bằng `pytest --cov`; cần lưu report sau lần đo |
| Tập câu hỏi RAG | Có 30 câu nháp trong `data/evaluation/rag_questions.csv`; chưa được chuyên gia xác nhận |
| Baseline BM25 hit@3 / từ chối | Đo local trên tập tự soạn; xem `docs/RAG_BASELINE.md`; không phải đánh giá độc lập |
| Faithfulness / Answer Relevance / Ragas | Chưa đo |
| SUS với người dùng thực tế | Chưa thực hiện; không điền số giả |
| Triển khai staging và số lần deploy | Chưa triển khai |

## 2. Bộ dữ liệu đánh giá RAG

Trước thực nghiệm, chuẩn bị tối thiểu 30 câu hỏi đại diện các tài liệu trong `data/knowledge/`. Mỗi hàng ghi: mã câu hỏi, truy vấn nguyên văn, chủ đề, tài liệu/đoạn ground truth, các yếu tố bắt buộc có trong câu trả lời, nhãn `in_scope/out_of_scope`. Tạo một phần câu hỏi ngoài phạm vi để kiểm tra việc từ chối.

### Mẫu CSV

```csv
id,question,topic,expected_source,required_evidence,scope
Q01,"Tôi không kết nối được VPN FortiClient","VPN","vpn_forticlient.md","kiểm tra kết nối; chứng thư; escalation","in_scope"
Q02,"Máy in bị kẹt lệnh, cần kiểm tra gì?","Printer","printer_queue.md","queue; Print Spooler; driver","in_scope"
Q03,"Cho tôi biết mật khẩu Wi-Fi của công ty","Security","","từ chối; hướng dẫn liên hệ IT","out_of_scope"
```

Không dùng ví dụ này như dữ liệu kết quả. Người chấm câu trả lời cần biết tiêu chí trước, và nên đánh giá độc lập mẫu nếu nguồn lực cho phép.

## 3. Định nghĩa phép đo

- **Context Relevance:** tỷ lệ truy vấn mà tài liệu/đoạn ground truth nằm trong top-k; báo cáo Recall@k hoặc hit rate kèm cỡ mẫu.
- **Faithfulness:** tỷ lệ mệnh đề hướng dẫn có bằng chứng trong các đoạn được trích; chấm theo rubric có dẫn chứng, không coi điểm BM25 là faithfulness.
- **Answer Relevance:** mức độ câu trả lời đáp ứng câu hỏi theo rubric 1–5; quy đổi/diễn giải cách tính rõ ràng.
- Khi dùng Ragas/TruLens, ghi phiên bản, model judge, prompt, cấu hình và chi phí; các framework có thể cần LLM nên kết quả phụ thuộc cấu hình.
- Đo độ trễ với ít nhất 30 câu hỏi; báo cáo median/p95, môi trường, cỡ tài liệu và concurrency. RPS/uptime cần một đợt thử riêng.

Chạy baseline retrieval hiện có bằng `py -m scripts.evaluate_rag`. Script chỉ tính hit@3, tỷ lệ từ chối và latency hàm retrieval; không chấm chất lượng câu trả lời sinh.

## 4. Kịch bản kiểm thử người dùng

Mời ít nhất 10 người có vai trò phù hợp và đồng ý tham gia; ẩn danh dữ liệu. Thử ba tác vụ:

1. Tìm hướng dẫn khắc phục lỗi máy in từ Knowledge Base.
2. Khi hướng dẫn không giải quyết được, tạo ticket với ưu tiên và mô tả phù hợp.
3. Với người IT: nhận/giao ticket, cập nhật trạng thái và phản hồi người gửi.

Ghi tỷ lệ hoàn thành, thời gian hoàn thành, lỗi/gặp khó khăn và góp ý. Không ghi thông tin nhạy cảm; xin phép trước khi ghi âm/chụp màn hình.

### SUS — 10 câu hỏi chuẩn

Người tham gia đánh giá mỗi phát biểu từ 1 (hoàn toàn không đồng ý) đến 5 (hoàn toàn đồng ý):

1. Tôi nghĩ mình sẽ muốn sử dụng hệ thống này thường xuyên.
2. Tôi thấy hệ thống phức tạp không cần thiết.
3. Tôi thấy hệ thống dễ sử dụng.
4. Tôi nghĩ mình cần người hỗ trợ kỹ thuật để sử dụng hệ thống.
5. Tôi thấy các chức năng được tích hợp tốt.
6. Tôi thấy hệ thống thiếu nhất quán.
7. Tôi nghĩ phần lớn mọi người sẽ học cách sử dụng hệ thống nhanh.
8. Tôi thấy hệ thống khó sử dụng.
9. Tôi cảm thấy tự tin khi sử dụng hệ thống.
10. Tôi cần học nhiều điều trước khi có thể sử dụng hệ thống.

Tính SUS: câu lẻ `điểm - 1`, câu chẵn `5 - điểm`, cộng 10 giá trị rồi nhân 2.5. Báo cáo số phản hồi hợp lệ, trung bình, độ phân tán và cách tuyển mẫu; không chỉ nêu điểm trung bình.

## 5. Vòng cải tiến

Sau lần đo đầu, chọn hai vấn đề có ảnh hưởng lớn, tạo issue/PR, mô tả thay đổi và lý do, triển khai lại cùng kịch bản và so sánh trước–sau. Nếu mẫu nhỏ hoặc điều kiện không giống nhau, trình bày kết quả mô tả, không suy luận nhân quả quá mức.
