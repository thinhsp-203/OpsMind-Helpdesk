# Đối chiếu prototype với plan và tính thực tiễn

**Ngày rà soát:** 05/10/2026\
**Nguồn đối chiếu:** kế hoạch Helpdesk RAG đầu vào và mã nguồn prototype trong repository này. Tài liệu kế hoạch đầu vào không được lưu trong repository.
**Nguyên tắc:** “Có file/cấu hình” không đồng nghĩa đã có minh chứng chạy, được người dùng xác nhận hoặc được GVHD ký.

## 1. Kết luận nhanh

- Prototype có thể demo một lát cắt end-to-end: hỏi runbook → xem trích dẫn hoặc tạo ticket → IT phân công/cập nhật → lưu audit.
- Chưa có lợi thế cạnh tranh đã được chứng minh. Jira Service Management, GLPI và ServiceNow là các hệ thống trưởng thành; sản phẩm này không nên được giới thiệu là thay thế hay tốt hơn chúng.
- Hướng khác biệt hợp lý để nghiên cứu là **thử nghiệm một workflow Helpdesk nhỏ, tiếng Việt, dựa trên runbook nội bộ có nguồn, cho nhóm SME không muốn bắt đầu bằng cấu hình ITSM rộng**. Đây mới là định vị/giả thuyết cần kiểm chứng, không phải kết quả khảo sát hay lợi thế độc quyền.
- Vì chưa khảo sát, chưa có đối tác thử nghiệm và chưa lấy số liệu quy trình hiện tại, **tính thực tiễn hiện mới ở mức bài toán có tính ứng dụng và prototype proof-of-concept; chưa chứng minh giá trị trong vận hành doanh nghiệp**.

## 2. Kế hoạch so với bằng chứng hiện có

| Mục trong plan | Bằng chứng trong prototype/repository | Trạng thái đúng hiện tại | Việc cần làm để đạt minh chứng |
|---|---|---|---|
| Tuần 1.1 — bối cảnh, giải pháp, so sánh 3 hệ thống | `BAO_CAO_BOI_CANH.md` có problem statement, phạm vi và so sánh; JSM/GLPI xem trang công khai, trang ServiceNow gặp 403 | **Đã có bản phân tích nháp; chưa có khảo sát thực địa hoặc benchmark sản phẩm** | GVHD rà soát; xác nhận quy trình cụ thể với một đơn vị; nhóm tự mở và ghi phiên bản/gói ServiceNow chính thức |
| Tuần 1.2 — khảo sát ≥3–5 phản hồi | Mới có 10 câu hỏi gợi ý trong báo cáo | **Chưa khảo sát, chưa có response** | Phát form/phỏng vấn, xin đồng ý, lưu số lượng, đối tượng, ngày và tổng hợp ẩn danh |
| Tuần 1.3 — repo, branch, board, PR/review | Mã prototype ban đầu được phát triển ngoài Git; hiện được chuyển vào repository này để công bố. Chưa có board hoặc lịch sử PR/review | **Chưa có minh chứng quản lý nhóm theo plan** | Duy trì issue/board, phân công, PR có review và lưu log |
| G1 — chốt sản phẩm và metric trước mốc 50% | Có file `G1_METRIC_CHARTER_TEMPLATE.md` để điền | **Mẫu chưa ký; không được xem là đã qua G1** | Họp GVHD, chốt định nghĩa/môi trường/mẫu, ký và lưu ngày trước hạn |
| Tuần 2 — SRS và 30–50 tài liệu KB | SRS có 10 story/AC; hiện có **9** runbook Markdown và Admin nạp thêm tài liệu qua UI/API | **Đặc tả và luồng quản trị cơ bản có; KB thiếu mục tiêu 30–50 và chưa được chuyên gia duyệt** | Bổ sung nội dung có nguồn; kiểm duyệt runbook và ground truth |
| Tuần 3 — SDD/ERD/sơ đồ | `SDD.md` có context, component, sequence, FSM, deployment, ERD, từ điển dữ liệu và API | **Có bản sơ đồ khớp prototype; cần rà chi tiết với GVHD** | Kiểm tra mọi tên bảng/endpoint/luồng đúng mã sau mỗi thay đổi |
| Tuần 4 — CRUD, RBAC, SLA, audit | Create/read/update, lưu trữ mềm Admin, phân công, comment, SLA giờ lịch, audit; có attachment giới hạn và kiểm soát quyền; không có hard delete/đổi mật khẩu | **Luồng ticket và quản trị hẹp demo được; chưa phải ITSM hoàn chỉnh** | Chốt phạm vi với GVHD; quy trình nghiệp vụ thật cần xác nhận |
| Tuần 5 — RAG và ký cam kết | BM25 local, trích đoạn/tên file và abstain; CSV 30 câu nháp, baseline hit@3 28/28 và abstain 2/2 | **Baseline kỹ thuật nội bộ; ground truth chưa được chuyên gia độc lập duyệt; G1 chưa ký** | Người IT xác nhận bộ câu hỏi/đáp án; đánh giá retrieval và câu trả lời riêng; lưu output/phiên bản |
| Tuần 6 — Frontend | Web UI phân biệt màn Nhân viên/Agent/Admin; tra cứu tự cuộn tới kết quả và chuyển tiếp nội dung sang ticket; Admin nạp KB/quản lý user | **Có UI demo; chưa có usability test** | Kiểm tra mobile/desktop và kịch bản với người dùng thật; xác nhận tiện ích so với kênh chat bằng tác vụ đối chứng |
| Tuần 7 — CI/CD/staging | CI YAML có Ruff (bao gồm nhóm rule bảo mật), pytest/coverage, retrieval baseline và Docker build; chưa có deploy workflow | **Cấu hình pipeline đã có; GitHub Actions chưa được chứng minh đã chạy; chưa deploy staging** | Push vào repo, lưu workflow run thật; deploy staging an toàn và lưu URL/log |
| Tuần 8 — test, RAG evaluation | 41 tests; backend Python coverage local **91%**; retrieval evaluation tự chạy trên tập draft | **Test tự động có; faithfulness/answer relevance/Ragas chưa đo** | Reviewer kiểm tra ground truth; thực nghiệm RAG có cấu hình và người chấm; nêu phạm vi coverage |
| Tuần 9 — 10 người, SUS ≥80, vòng cải tiến | Chưa có dữ liệu người tham gia hoặc SUS | **Chưa làm** | Tổ chức task test ≥10 người theo plan nếu khả thi, thu SUS/hoàn thành task, cải tiến rồi đo lại |
| Tuần 10 — luận văn, plagiarism, bảo vệ | Đã có tài liệu nền; chưa có luận văn hoàn chỉnh, Turnitin/DoIT hay minh chứng hội đồng | **Chưa làm** | Hoàn thành sau khi có kết quả thật; trích nguồn, kiểm tra đạo văn theo quy định trường |

## 3. So sánh cạnh tranh: điều gì có thể và không thể nói

### Không nên nói

- “RAG Helpdesk tốt hơn Jira/GLPI/ServiceNow”, “chính xác hơn” hoặc “rẻ hơn” — chưa có benchmark cùng dữ liệu/tác vụ/tổng chi phí.
- “AI giải quyết được 60% sự cố” — hiện chưa có user study, session outcome label hoặc xác nhận ticket deflection.
- “Đảm bảo riêng tư/production-ready” — chạy local và không gọi API LLM giúp giảm phụ thuộc ra ngoài trong demo, nhưng còn dữ liệu mẫu, SQLite và chưa có hardening/backup/SSO; tài khoản mẫu chỉ dùng khi bật demo mode.
- “Đã đạt faithfulness 0.85, 50 RPS, uptime 99%, SUS 80” — các metric này chưa đo.

### Có thể nói, kèm giới hạn

- Prototype minh họa runbook truy xuất cục bộ, nguồn hiển thị được và cơ chế từ chối khi không thấy đoạn phù hợp; đây là lựa chọn **dễ kiểm tra/giải thích cho đồ án**, không phải ưu thế duy nhất trên thị trường.
- Một workflow ticket và tra cứu tri thức trong cùng web app có thể hữu ích cho nhóm nhỏ thử nghiệm; cần xác nhận với người làm IT xem nó giảm bước hay chỉ thêm một công cụ.
- Nội dung lỗi văn phòng bằng tiếng Việt có thể là điểm phù hợp bối cảnh nếu nhân viên/IT trong đơn vị mục tiêu ưu tiên tiếng Việt. Chưa có bằng chứng rằng JSM/GLPI/ServiceNow không đáp ứng ngôn ngữ hoặc quy trình này.

## 4. Bằng chứng cần thu để trả lời “có thực tiễn không?”

### Trước khi tuyên bố nhu cầu tồn tại

1. Chọn một tổ chức/nhóm mục tiêu cụ thể và mô tả kênh Helpdesk đang dùng.
2. Phỏng vấn cả nhân viên và IT Support, theo 10 câu trong báo cáo bối cảnh; ghi nhận số người thật, vai trò tổng quát, thời điểm, sự đồng ý và hạn chế chọn mẫu.
3. Xin số liệu ẩn danh tối thiểu từ quy trình hiện tại nếu được phép: nhóm ticket thường gặp, thời gian phản hồi/giải quyết, số lượt hỏi lại, kênh báo lỗi. Nếu không được cấp, ghi rõ chỉ dùng phỏng vấn, không giả lập như số liệu doanh nghiệp.

### Trong pilot

- Dùng runbook đã được IT đơn vị phê duyệt; không nạp mật khẩu, cấu hình bí mật, thông tin khách hàng hay dữ liệu cá nhân.
- Giao cùng các tác vụ cho người dùng trên quy trình hiện tại và prototype (hoặc cách so sánh được GVHD duyệt); đo thời gian tìm hướng dẫn, hoàn thành tác vụ và số lần cần hỗ trợ.
- Định nghĩa **self-service resolution** là phiên mà người dùng xác nhận hoàn thành tác vụ không cần ticket/can thiệp IT trong cửa sổ thời gian đã chốt. Không dùng “không tạo ticket” đơn thuần làm bằng chứng giải quyết.
- Định nghĩa **ticket response/resolution time**, phân tách giờ làm và giờ ngoài giờ nếu SLA thực tế có lịch làm việc.
- Thực hiện usability task và SUS theo plan; báo cáo cỡ mẫu, điểm từng phản hồi ẩn danh/tổng hợp và thay đổi sau cải tiến.

## 5. Nguồn thị trường đã kiểm tra

- Atlassian, [Jira Service Management](https://www.atlassian.com/software/jira/service-management) và [Features](https://www.atlassian.com/software/jira/service-management/features), truy cập 05/10/2026. Trang Features được đọc trong phiên này: định vị từ startup đến enterprise, các gói Free/Standard/Premium/Enterprise, Data Center và nội dung AI cho alert grouping/incident response. Không suy rộng tính năng cụ thể ngoài nội dung trang.
- GLPI Project, [Features](https://glpi-project.org/features/), truy cập 05/10/2026. Trang tiếng Anh xác nhận inventory máy tính và các thông tin thiết bị/địa điểm/người dùng; chưa cài GLPI để test luồng.
- ServiceNow, [IT Service Management](https://www.servicenow.com/products/itsm.html), truy cập thử 05/10/2026. Trang trả HTTP 403 từ môi trường rà soát này; thông tin chi tiết về feature/gói chưa được xác minh trực tiếp.

Khi nộp luận văn, kiểm tra lại trang theo ngày truy cập thực tế, lưu tài liệu/ảnh chụp nguồn phù hợp với quy định trích dẫn của trường và không coi bảng này là đánh giá độc lập sản phẩm.
