# Báo cáo bối cảnh đề tài

**Đề tài:** Xây dựng hệ thống Helpdesk hỗ trợ xử lý sự cố CNTT bằng truy xuất tri thức (RAG)\
**Phiên bản:** 1.1 — đối chiếu thị trường và thực tiễn theo prototype hiện có\
**Trạng thái:** Phân tích đề tài; chưa có xác nhận nhu cầu từ doanh nghiệp/người dùng thực tế.

## 1. Bối cảnh và vấn đề

Trong bộ phận IT nội bộ, các yêu cầu như VPN/Wi-Fi, máy in, cập nhật Windows, Outlook, chứng thư số, MFA và quyền thư mục có thể lặp lại. Khi hướng dẫn xử lý không được chuẩn hóa hoặc khó tìm, người dùng có thể phải chờ IT cho bước xử lý ban đầu, còn kỹ thuật viên phải thu thập lại thông tin và tra cứu thủ công.

Đây là **bài toán hợp lý để khảo sát**, chưa phải kết luận rằng một doanh nghiệp cụ thể đang gặp các vấn đề sau. Cần kiểm chứng bằng phỏng vấn/khảo sát và số liệu helpdesk:

- Thời gian chờ hỗ trợ và thời gian IT dành cho yêu cầu lặp lại.
- Ticket thiếu thông tin ban đầu dẫn đến nhiều vòng hỏi đáp.
- Runbook khó tìm, lỗi thời hoặc phụ thuộc vào kinh nghiệm cá nhân.
- Thiếu khả năng theo dõi trạng thái, người xử lý, hạn SLA và lịch sử trong một luồng.

**Tính thực tiễn nằm ở luồng công việc cụ thể**: người dùng mô tả sự cố → tìm hướng dẫn nội bộ có nguồn → tự thử bước an toàn hoặc mở ticket → Agent tiếp nhận, phân công, phản hồi và cập nhật trạng thái. Giá trị cần đo là giảm thời gian tìm hướng dẫn/trao đổi lặp lại và cải thiện khả năng theo dõi yêu cầu, không phải “có chatbot AI” tự thân.

Prototype hiện tại chứng minh được luồng demo cục bộ, chưa chứng minh được hiệu quả vận hành tại doanh nghiệp. Không thay thế hệ thống ITSM, giám sát hạ tầng, phê duyệt quyền truy cập hay phán đoán của IT.

## 2. Đối tượng và nhu cầu

| Đối tượng | Nhu cầu chính | Kết quả mong đợi |
|---|---|---|
| Nhân viên (End-user) | Tìm hướng dẫn dễ hiểu; tạo và theo dõi yêu cầu | Tự xử lý lỗi phổ biến hoặc gửi ticket có đủ thông tin |
| IT Support (Agent) | Nhìn hàng đợi, ưu tiên và nhận ticket; tra cứu runbook | Xử lý thống nhất, cập nhật trạng thái và trao đổi tại một nơi |
| Quản trị (Admin) | Quản lý quyền, tri thức và theo dõi số liệu vận hành | Kiểm soát quyền truy cập, SLA và hoạt động hỗ trợ |

## 3. Giải pháp và điều khác biệt có thể bảo vệ

Ứng dụng có cổng nhân viên và bảng điều phối IT. Người dùng hỏi bằng tiếng Việt/Anh; mô-đun BM25 truy xuất đoạn từ runbook Markdown cục bộ, hiển thị tên tệp và nội dung trích dẫn. Khi điểm truy xuất thấp, hệ thống từ chối đoán và đề xuất tạo ticket. Khi người dùng chọn bàn giao, prototype gợi ý danh mục từ tài liệu đứng đầu và priority từ một bộ từ khóa tác động, nêu lý do rồi để người gửi xác nhận/chỉnh sửa. Hệ thống **không gọi LLM/embedding, không tự sinh quy trình, không tự gửi ticket**; vì vậy nên gọi chính xác là baseline truy xuất tri thức kèm rule-based triage, không quảng bá như một agent sinh đáp án hay auto-triage ML.

Ticket lưu người yêu cầu, loại, ưu tiên, trạng thái, hạn SLA, người xử lý, trao đổi và audit log; người dùng chỉ xem ticket của mình. End-user có thể sửa ticket khi còn mới; Agent/Admin trước khi đóng; Admin có thể lưu trữ mềm và giữ audit. Admin cũng tạo tài khoản và nạp runbook Markdown qua UI/API. Đây là giá trị tích hợp so với một chatbot FAQ rời: nếu tài liệu không giải quyết được, yêu cầu có thể chuyển tiếp trong cùng quy trình hỗ trợ.

### Tình huống sử dụng và tiện ích so với nhắn Zalo

| Tình huống | Nhắn Zalo/nhóm chat | Luồng prototype | Tiện ích có thể kiểm chứng trong demo |
|---|---|---|---|
| Nhân viên gặp lỗi VPN | Gõ lại mô tả; hướng dẫn cũ nằm rải trong lịch sử chat | Mô tả lỗi → tra runbook → xem tên nguồn/đoạn trích | Có thể tìm đúng tài liệu mà không cuộn/tìm thủ công; độ hữu ích phụ thuộc độ phủ và độ mới của runbook |
| Hướng dẫn không giải quyết được | Nhắn tiếp hoặc chuyển sang kênh khác; ngữ cảnh có thể phải kể lại | Nút chuyển kết quả thành yêu cầu điền sẵn, gợi ý danh mục/ưu tiên và lý do → nhân viên xác nhận/chỉnh → chủ động gửi ticket có mã | Không gõ lại nội dung; yêu cầu tồn tại trong hàng đợi và có người phụ trách/trạng thái |
| IT nhận nhiều yêu cầu | Dựa vào tin nhắn chưa đọc, ghim hoặc bảng tính riêng | Một hàng đợi có lọc, mức ưu tiên, SLA, phân công, trao đổi và audit | Dễ nhìn việc chưa nhận/quá hạn và lịch sử; cần quy trình/ca trực thực tế để đo có giảm bỏ sót hay không |
| Người gửi muốn hỏi tiến độ | Nhắn hỏi lại trong chat | Mở ticket của mình, xem trạng thái, người xử lý, hạn dự kiến và phản hồi | Tự tra tiến độ thay vì hỏi IT; prototype chưa gửi push/email notification |

**Không nên bỏ Zalo/kênh khẩn cấp:** hệ thống chỉ hữu ích cho yêu cầu có thể ghi nhận và theo dõi. Sự cố diện rộng, nguy cơ an toàn/bảo mật hoặc yêu cầu khẩn cấp phải theo hotline/quy trình incident của đơn vị; ITSM thật cũng có thể tích hợp kênh chat. Prototype hiện là thêm một kênh ticket, chưa tích hợp Zalo, chưa đồng bộ hệ thống nhân sự/SSO và chưa có thông báo tự động.

Trong giao diện đã điều chỉnh, Nhân viên thấy luồng tra cứu trước → chuyển nội dung sang ticket → theo dõi mã/trạng thái; Agent thấy hàng đợi và danh bạ người xử lý; Admin có thêm quản trị user/tri thức/analytics. Đây là phân vai trong prototype, không phải mô hình vận hành đã được doanh nghiệp duyệt.

**Ba điểm có thể chứng minh từ prototype, không phải ưu thế tuyệt đối:**

1. **Bối cảnh riêng của đơn vị:** Admin nạp runbook nội bộ, truy xuất có nguồn và câu hỏi được xử lý cục bộ, không gửi tới dịch vụ LLM ngoài. Điều này giúp giữ câu trả lời trong phạm vi tài liệu đã cấp; chưa phải bảo đảm bảo mật/riêng tư production, và chất lượng phụ thuộc vào nội dung đã kiểm duyệt.
2. **Từ tra cứu sang bước làm và bàn giao:** xem hướng dẫn trích dẫn; nếu chưa giải quyết được, nội dung được chuyển sẵn vào ticket. Runbook là checklist biên soạn sẵn, không phải AI tự tạo PowerShell/fix registry hay tự thực thi lệnh.
3. **Triage gắn vào quy trình:** danh mục dựa trên runbook khớp nhất, mức ưu tiên gợi ý bằng marker tác động, kèm lý do; nhân viên xác nhận/chỉnh trước khi gửi, Agent có hàng đợi và lịch sử. Đây là rule-based helper chứ không phải AI classifier đã benchmark.

Tiện ích so với Zalo cần được chứng minh bằng phép thử tác vụ: cùng một sự cố, tìm đúng hướng dẫn, chuyển cho IT và tra tiến độ; ghi thời gian, số lần nhập lại, số câu hỏi bổ sung và tỷ lệ phân loại đúng trên cả hai cách. Hiện mới chứng minh được các thao tác trong prototype, chưa có số liệu cho thấy nó nhanh hơn hay giảm MTTR/bỏ sót.

Không có cơ sở để tuyên bố sản phẩm mới hơn, đầy đủ hơn, rẻ hơn hoặc chính xác hơn Jira Service Management, GLPI hay ServiceNow. Các hệ thống đó đã trưởng thành hơn nhiều; đề tài là prototype học thuật để nghiên cứu một lát cắt nhỏ.

**Giới hạn thuật ngữ AI:** bản demo hiện thực hiện lexical retrieval (BM25) và hiển thị đoạn nguồn; chưa có bước LLM sinh câu trả lời dựa trên context. Vì vậy điểm có thể bảo vệ hiện tại là truy xuất có dẫn nguồn/abstention, không phải năng lực sinh RAG hay hiệu quả AI vượt sản phẩm khác.

## 4. So sánh với các hệ thống tham khảo

So sánh dưới đây chỉ đối chiếu **phạm vi/định hướng được xác minh từ trang chính thức có thể truy cập** với phần demo đã triển khai. Không so sánh giá, SLA thương mại, độ chính xác AI, bảo mật, hiệu năng hoặc tổng chi phí sở hữu vì chưa có cấu hình/benchmark chung. Tính năng của sản phẩm thương mại phụ thuộc phiên bản/gói và có thể thay đổi.

| Tiêu chí | Jira Service Management | GLPI | ServiceNow ITSM | Prototype Helpdesk RAG |
|---|---|---|---|---|
| Định hướng xác nhận được | Dịch vụ quản lý service cho startup đến enterprise; nhà cung cấp nêu các gói Free/Standard/Premium/Enterprise và tùy chọn Data Center tự quản lý | Bộ giải pháp IT/asset; trang chính thức mô tả quản lý inventory máy tính, thông tin thiết bị, vị trí và người dùng liên quan | Được đưa vào plan làm đối chứng ITSM doanh nghiệp; trang chính thức bị chặn 403 trong lần rà soát này, nên chưa xác nhận chi tiết tính năng từ nguồn gốc | Mẫu học thuật hẹp: ticket + SLA cơ bản + truy xuất runbook Markdown |
| Tri thức/AI | Trang sản phẩm hiện nêu tính năng AI cho alert grouping/incident response; không suy rộng thành kết luận về mọi tính năng KB/gói | Có chức năng quản lý tài sản; cần thử phiên bản/plugin cụ thể để kết luận về workflow tri thức liên quan | Chưa xác nhận phiên bản/gói và feature AI/knowledge trong lần tra cứu này | BM25 local, đoạn trích dẫn, ngưỡng từ chối; không có LLM; Admin có thể nạp Markdown giới hạn |
| Vận hành/helpdesk | Sản phẩm thương mại có nhiều gói/tùy chọn triển khai; cần đánh giá theo gói và môi trường cụ thể | Khả năng quản lý tài sản được xác nhận; triển khai và cấu hình thực tế cần thử trên phiên bản được chọn | Cần kiểm chứng từ tài liệu chính thức/tenant demo trước khi lập luận chi tiết | PostgreSQL trong Compose hoặc SQLite khi chạy local; tài khoản mẫu chỉ khi bật demo mode; Admin tạo user/nạp KB; chưa có SSO/backup/HA |
| Điểm phù hợp của prototype | Có thể nghiên cứu cách rút gọn một luồng cho bài tập hoặc thử nghiệm nhanh; không chứng minh thay thế JSM | Có thể nghiên cứu KB/luồng hẹp bên cạnh công cụ ITSM hiện có; GLPI có phạm vi asset mà prototype chưa có | Không cạnh tranh về độ rộng/độ trưởng thành; dùng làm hệ tham chiếu doanh nghiệp | Có thể phù hợp *nếu khảo sát xác nhận* nhóm nhỏ cần bản thử tiếng Việt, dữ liệu runbook nội bộ gọn và muốn kiểm soát mã nguồn |
| Bằng chứng so sánh hiện có | Đọc trang tính năng/giới thiệu công khai; chưa cài và benchmark | Đọc trang tính năng chính thức; chưa cài và benchmark | Link tham chiếu trong plan; truy cập nguồn bị 403 | Bộ test/coverage local và baseline retrieval tự soạn 30 câu; chưa khảo sát triển khai |

**Kết luận so sánh:** khác biệt có thể trình bày là *định vị học thuật ngách và cách triển khai gọn*, không phải tính năng độc quyền hay vượt trội. Để chứng minh phù hợp SME, cần chọn một đơn vị/quy trình cụ thể, so sánh trên cùng tập tác vụ và đo chi phí cài đặt/vận hành, thời gian tìm tri thức, tỷ lệ tự xử lý, thời gian xử lý ticket, bảo mật và mức hài lòng.

Nguồn đã rà soát ngày 05/10/2026:

- Atlassian, [Jira Service Management — product overview](https://www.atlassian.com/software/jira/service-management): mô tả thị trường từ startup đến enterprise và các gói/tùy chọn Data Center. Trang [Features](https://www.atlassian.com/software/jira/service-management/features) hiện cũng nêu AI hỗ trợ nhóm cảnh báo/incident response. Chỉ dẫn phạm vi đúng nội dung trang đã đọc, không suy đoán giá hoặc feature theo gói.
- GLPI Project, [Features](https://glpi-project.org/features/): trang tiếng Anh xác nhận chức năng inventory cho máy tính và quản lý các trường thiết bị/người dùng. Chưa triển khai GLPI để so sánh thao tác.
- ServiceNow, [IT Service Management](https://www.servicenow.com/products/itsm.html): yêu cầu đối chiếu trong plan; không đọc được trong lần kiểm tra do HTTP 403. Nhóm cần mở trang/tài liệu chính thức từ mạng của mình và ghi phiên bản/gói trước khi trích dẫn feature cụ thể.

## 5. Giá trị thực tiễn, metric và câu hỏi đánh giá

### Giả thuyết giá trị

| Giả thuyết | Chỉ số thực tiễn cần thu | Tình trạng hiện tại |
|---|---|---|
| Runbook có nguồn giúp người dùng tìm bước xử lý nhanh hơn | Thời gian đến khi tìm đúng hướng dẫn; hit@k trên câu hỏi đã được chuyên gia gán nguồn | Baseline local hit@3 28/28 trên 28 câu nháp tự soạn; chưa có xác nhận chuyên gia hay đo với người dùng |
| Gợi ý tự phục vụ xử lý được một phần lỗi lặp lại | Tỷ lệ phiên hỏi kết thúc không tạo ticket, kèm xác nhận người dùng đã giải quyết | Chưa có người dùng thật và chưa ghi nhận kết quả phiên; chưa đo |
| Form/ticket có cấu trúc giúp IT giảm trao đổi bổ sung | Số lượt hỏi lại/ticket; thời gian từ tạo đến phản hồi/giải quyết; trường thông tin đủ ngay lần đầu | Prototype có trường tiêu đề/mô tả/loại/ưu tiên; chưa kết nối quy trình IT của đơn vị |
| Theo dõi trạng thái/SLA giúp minh bạch và ưu tiên việc | Tỷ lệ ticket trong SLA, số quá hạn và thời gian xử lý theo ưu tiên | Đã tính deadline giờ lịch và số ticket quá hạn; chưa có dữ liệu vận hành/ca trực thực tế |
| Giao diện giúp người dùng hoàn thành nhiệm vụ | Task completion, thời gian, SUS và góp ý trước/sau cải tiến | Chưa tổ chức usability test |

Baseline 28/28 hit@3 chỉ có nghĩa là 28 ground-truth nguồn trong CSV tự soạn xuất hiện trong top 3 trên KB hiện tại. Nó **không chứng minh độ chính xác thực tế, faithfulness, giảm ticket hay lợi ích doanh nghiệp**. Chi tiết giới hạn tại [RAG_BASELINE.md](RAG_BASELINE.md).

### Câu hỏi thực nghiệm

- Người dùng có tìm được hướng dẫn và hoàn tất các tác vụ cơ bản không?
- RAG có trả đúng tài liệu/đoạn trên một tập câu hỏi do IT/SME xác nhận, gồm câu diễn đạt khác và câu ngoài phạm vi không?
- So với quy trình hiện tại của một đơn vị, thời gian tìm hướng dẫn và số lượt trao đổi ticket có thay đổi không?
- Người dùng có đánh giá giao diện dễ học, dễ sử dụng không?
- Agent có thể tiếp nhận và xử lý ticket trong quy trình thật mà không mất thông tin hoặc tạo thêm thao tác không cần thiết?

Kế hoạch ban đầu đề xuất các mục tiêu như self-service ≥60%, latency ≤3 giây, faithfulness ≥0.85, SUS ≥80, 10 người dùng. Đây là **mục tiêu cần GVHD chốt**, không phải kết quả hiện tại; có thể phải sửa cách đo/self-service và xác định rõ mẫu, môi trường, thời gian trước khi ký. Mẫu charter chưa ký tại [G1_METRIC_CHARTER_TEMPLATE.md](G1_METRIC_CHARTER_TEMPLATE.md).

## 6. Phạm vi

**Trong phạm vi prototype:** đăng nhập ba vai trò, Admin tạo tài khoản và nạp runbook Markdown, ticket create/read/update, lưu trữ mềm Admin, phân công Agent, bình luận, FSM, SLA theo giờ lịch, audit log, lọc ticket, analytics cơ bản, truy xuất Markdown và web UI.

**Ngoài phạm vi/giới hạn hiện tại:** tích hợp SSO/email/AD, malware scanning và retention cho attachment, lịch làm việc/ngày nghỉ trong SLA, vector database, LLM sinh câu trả lời, quản lý nhiều tenant, HA/backup/monitoring production, migration SQLite→PostgreSQL, triển khai staging công khai và đánh giá người dùng thực tế. Attachment hiện giới hạn PNG/JPG/TXT/LOG đến 10 MiB và được phục vụ qua API có kiểm tra quyền. KB hiện có 9 runbook, thấp hơn mục tiêu 30–50 tài liệu trong plan. Tài khoản demo chỉ dành cho học tập và trình diễn; cấu hình PostgreSQL Compose chưa được harden cho production.

## 7. Phương pháp khảo sát nhu cầu

Thực hiện khảo sát ngắn với nhân viên văn phòng và IT Support. Không thu mật khẩu, dữ liệu cá nhân nhạy cảm hoặc tên doanh nghiệp nếu chưa được đồng ý. Ghi ngày thu thập, số người tham gia, vai trò tổng quát và cách chọn mẫu; không sửa số liệu để khớp mục tiêu.

### Bộ câu hỏi gợi ý (10 câu)

1. Trong 3 tháng gần nhất, bạn gặp sự cố CNTT công việc bao nhiêu lần?
2. Ba loại sự cố thường gặp nhất của bạn là gì?
3. Bạn hiện báo sự cố qua kênh nào?
4. Bạn thường chờ bao lâu để nhận phản hồi đầu tiên?
5. Mức độ hài lòng với cách hỗ trợ hiện tại (1–5)?
6. Bạn có tự tìm được hướng dẫn xử lý trước khi liên hệ IT không?
7. Khi gửi yêu cầu, thông tin nào bạn thường không biết cần cung cấp?
8. Với IT Support: loại yêu cầu lặp lại nào chiếm nhiều thời gian nhất?
9. Với IT Support: thông tin nào thường thiếu khiến việc xử lý chậm?
10. Bạn mong muốn cải thiện điều gì nhất ở quy trình hỗ trợ?

## 8. Đánh giá mức độ thực tiễn hiện tại

**Có tính ứng dụng ở mức proof-of-concept:** các luồng ticket và runbook bám vào nhóm sự cố văn phòng; prototype chạy được, lưu ticket qua PostgreSQL trong Compose hoặc SQLite local và minh họa được truy vấn có nguồn → tạo ticket → IT cập nhật.

**Chưa đủ bằng chứng để kết luận hữu ích trong doanh nghiệp:** chưa có đối tác/người dùng nghiệp vụ xác nhận pain point, chưa có khảo sát nhu cầu, chưa triển khai vào quy trình thật, chưa đo tỷ lệ tự xử lý/ticket deflection, MTTR, task completion hay SUS. Baseline retrieval được tạo và chạy trong nhóm; không phải thử nghiệm người dùng.

**Điều kiện tối thiểu để gọi kết quả “có tính thực tiễn”:**

1. Chọn một đơn vị/nhóm IT cụ thể, mô tả quy trình hiện tại và lấy sự đồng ý sử dụng dữ liệu.
2. Phỏng vấn/khảo sát đúng hai nhóm nhân viên và IT; báo cáo số mẫu thật, cách chọn mẫu và vấn đề được xác nhận.
3. Xin phép và chuẩn hóa runbook thực tế (ẩn thông tin nhạy cảm), đưa đủ tài liệu thuộc phạm vi đã cam kết; người có chuyên môn duyệt nội dung và ground truth.
4. Thử nghiệm có kịch bản, tối thiểu 10 người như plan nếu khả thi; đo task completion/time/SUS và xác nhận việc tự xử lý, không suy ra deflection chỉ từ “hỏi RAG nhưng không tạo ticket”.
5. Chọn baseline so sánh (quy trình/kênh hiện tại hoặc tìm kiếm KB thường), dùng cùng câu hỏi/tác vụ và báo cáo chênh lệch cùng giới hạn.
6. Chốt sản phẩm + metric bằng văn bản với GVHD trước mốc G1; giữ log, dữ liệu ẩn danh, phiên bản phần mềm và kết quả gốc.

**Rủi ro:** BM25 có thể bỏ sót cách gọi địa phương; runbook sai/lỗi thời gây hướng dẫn không an toàn; SLA giờ lịch khác ca làm; dữ liệu demo không đại diện; tài khoản/secret demo không an toàn cho production; quy mô KB nhỏ có thể làm kết quả retrieval lạc quan.

## 9. Tài liệu tham khảo ban đầu

- Atlassian, Jira Service Management, https://www.atlassian.com/software/jira/service-management
- Atlassian, Jira Service Management Features, https://www.atlassian.com/software/jira/service-management/features
- GLPI Project, Features, https://glpi-project.org/features/
- ServiceNow, IT Service Management, https://www.servicenow.com/products/itsm.html
- FastAPI Documentation, https://fastapi.tiangolo.com/
- Robertson, S. & Robertson, J., *Mastering the Requirements Process*, Addison-Wesley.
- Lewis, P. et al. (2020), “Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks”, NeurIPS.
- Brooke, J. (1996), “SUS: A ‘Quick and Dirty’ Usability Scale”.
