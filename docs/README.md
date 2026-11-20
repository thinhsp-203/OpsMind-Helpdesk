# Mục lục tài liệu OpsMind

Chọn tài liệu theo nhu cầu bên dưới. Báo cáo và minh chứng có ngày là bản ghi của từng thời điểm; không dùng trạng thái trong bản lịch sử thay cho trạng thái hiện tại trên [GitHub Issues](https://github.com/thinhsp-203/OpsMind-Helpdesk/issues) và [Pull requests](https://github.com/thinhsp-203/OpsMind-Helpdesk/pulls).

## 1. Đặc tả và thiết kế

- [Bối cảnh đề tài](BAO_CAO_BOI_CANH.md): Bài toán, phạm vi và đối tượng sử dụng.
- [Yêu cầu phần mềm — SRS](SRS.md): Chức năng, tiêu chí chấp nhận và yêu cầu phi chức năng.
- [Thiết kế hệ thống — SDD](SDD.md): Kiến trúc, dữ liệu và API.
- [Đặc tả trợ lý — phiên bản 1](ASSISTANT_SPEC_V1.md): Phạm vi, dữ kiện, hành động, quyền và thiết kế đánh giá độc lập.
- [RAG baseline](RAG_BASELINE.md): Phương pháp và kết quả truy xuất trong phạm vi tài liệu.
- [Mẫu chốt sản phẩm và metric G1](G1_METRIC_CHARTER_TEMPLATE.md): Mẫu thảo luận; không xem là bản đã ký/phê duyệt.

## 2. Hướng dẫn sử dụng và vận hành

- [Hướng dẫn sử dụng](USER_GUIDE.md): Thao tác theo vai trò Nhân viên, IT và Admin.
- [Hướng dẫn triển khai](DEPLOYMENT.md): Môi trường, cấu hình và vận hành.
- [Luồng demo](DEMO-WORKFLOW.md): Kịch bản trình diễn hệ thống.
- [Hướng dẫn đóng góp](../CONTRIBUTING.md): Quy chuẩn repository và lệnh kiểm tra.
- [Quy ước domain cho agent](agents/domain.md) và [quy trình GitHub Issues](agents/issue-tracker.md).

## 3. Báo cáo và theo dõi công việc

- [Tiếp thu góp ý báo cáo tuần 6 — 20/11/2026](reports/WEEK6_RESUBMISSION_2026-11-20.md): Phụ lục nộp lại; các trạng thái trong bản đối chiếu cần đọc cùng ngày cập nhật.
- [Báo cáo tiến độ — 14/10/2026](BAO_CAO_TIEN_DO_TUAN.md): Bản lịch sử, không phải báo cáo tuần 6.
- [Nhật ký sử dụng AI](AI_USAGE_LOG.md): Công việc, nguồn hỗ trợ và giới hạn được ghi nhận.
- [Nhật ký lỗi và nợ kỹ thuật](DEFECT_TECH_DEBT_LOG.md): Đọc cùng trạng thái Issues hiện tại.
- [Các vấn đề UI trợ lý](UI_ASSISTANT_ISSUES.md): Hồ sơ rà soát giao diện.
- [Chẩn đoán trợ lý](ASSISTANT_DIAGNOSTICS.md): Nguyên nhân và bằng chứng kiểm tra trong các lượt được ghi nhận.
- [Chẩn đoán chi phí kết nối DB — 14/11/2026](DIAGNOSE_DB_LATENCY_2026-11-14.md): Phân biệt đo mô phỏng local với số đo trên Render.

## 4. Kiểm thử và minh chứng

- [Ma trận truy vết kiểm thử](TEST_TRACEABILITY.md): Liên hệ yêu cầu với kiểm thử và giới hạn bằng chứng.
- [Kế hoạch thực nghiệm](KE_HOACH_THUC_NGHIEM.md): Thiết kế đánh giá RAG và khảo sát; kế hoạch không thay kết quả đã chạy.
- [Minh chứng Render — 12/11/2026](verification/2026-11-12/README.md): Hướng dẫn đọc log/ảnh, provenance và công cụ tự đối chiếu. XML local nằm riêng, không gộp vào số ca Render.
- [Minh chứng kỹ thuật — 29/10/2026](verification/2026-10-29/): Log và thông tin phiên bản của lượt lịch sử này.
- [Rà soát và sửa lỗi — 29/10/2026](REVIEW_FIXES_2026-10-29.md).
- [Bản sửa xóa tài khoản — 03/11/2026](ACCOUNT_DELETE_FIX_2026-11-03.md).
- [Bản sửa P2 — 03/11/2026](SYSTEM_P2_FIX_2026-11-03.md).

## 5. Tài liệu nội bộ và lịch sử

- [Đối chiếu kế hoạch với thực tiễn](internal/DOI_CHIEU_PLAN_THUC_TIEN.md).
- [Đối chiếu chức năng và giao diện](internal/DOI_CHIEU_FEATURES_AND_UI.md).
- [Đối chiếu hướng dẫn bổ sung](internal/DOI_CHIEU_SUPPLEMENT_GUIDE.md).
- [SDD trước ngày 31/10/2026](history/SDD_before_2026-10-31.md): Bản thiết kế lịch sử.
- [Các ticket nháp của đặc tả trợ lý](../.scratch/assistant-spec/issues/): Giữ để truy vết; công việc mới được theo dõi trên GitHub Issues.

[Về README repository](../README.md)
