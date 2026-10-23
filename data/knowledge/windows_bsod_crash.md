# Chẩn đoán và xử lý lỗi màn hình xanh chết chóc (BSOD) trên Windows

**Từ khóa:** màn hình xanh, BSOD, blue screen, máy tính bị sập, khởi động lại, crash, dump file, Stop Code, DRIVER_IRQL, MEMORY_MANAGEMENT, minidump, phần cứng, Windows.

## Triệu chứng / Dấu hiệu nhận biết
- Màn hình máy tính đột ngột chuyển sang màu xanh dương với thông báo "Your PC ran into a problem and needs to restart".
- Đi kèm mã dừng lỗi (Stop Code) như: `CRITICAL_PROCESS_DIED`, `SYSTEM_SERVICE_EXCEPTION`, `PAGE_FAULT_IN_NONPAGED_AREA`, `DRIVER_IRQL_NOT_LESS_OR_EQUAL`.
- Máy tính tự động đếm phần trăm thu thập thông tin rồi khởi động lại đột ngột, làm mất tài liệu đang làm việc.

## Các bước tự khắc phục nhanh (Self-service)
1. **Ghi lại mã lỗi Stop Code:** Dùng điện thoại chụp lại màn hình xanh, đặc biệt là dòng chữ hoa Stop Code (ví dụ: `MEMORY_MANAGEMENT`) và tên file bị lỗi (nếu có, ví dụ `.sys`).
2. **Rút bớt thiết bị ngoại vi mới cắm:** Nếu lỗi xảy ra ngay sau khi cắm USB mới, máy in, ổ cứng rời hoặc chuột/bàn phím lạ, hãy rút thiết bị ra và khởi động lại.
3. **Khởi động lại máy tính:** Để máy khởi động lại tự nhiên vào Windows. Nếu máy vào được màn hình đăng nhập bình thường, lưu ngay lại các file dữ liệu quan trọng đang lưu trên ổ C/Desktop.
4. **Kiểm tra bản cập nhật gần nhất:** Nếu lỗi xuất hiện ngay sau khi cài một phần mềm lạ, hãy gỡ bỏ phần mềm đó khỏi máy.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Máy tính bị lỗi màn hình xanh liên tục theo vòng lặp, không thể vào được màn hình đăng nhập Windows.
- Lỗi xuất hiện thường xuyên nhiều lần trong ngày, làm gián đoạn công việc.
- Cần kỹ thuật viên IT đọc file minidump (`C:\Windows\Minidump`) bằng công cụ chuyên dụng để phân tích chính xác driver hoặc linh kiện phần cứng (RAM, ổ cứng, bo mạch chủ) bị hỏng.
