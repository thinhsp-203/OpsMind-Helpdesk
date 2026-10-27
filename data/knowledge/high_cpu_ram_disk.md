# Khắc phục sự cố máy tính chạy chậm, CPU, RAM và Disk 100% trên Windows

**Từ khóa:** quạt kêu to, máy nóng, đơ máy, treo máy, chậm máy, CPU 100%, RAM đầy, full disk, disk 100%, Task Manager, hiệu năng, tài nguyên, Windows, user self-service actions, it tier 2 administration actions.

## Triệu chứng / Dấu hiệu nhận biết
- Máy tính phản hồi rất chậm, ứng dụng bị đơ (Not Responding), chuột giật lag khi di chuyển.
- Quạt tản nhiệt của máy tính hoặc laptop kêu to liên tục, thân máy tỏa nhiệt nóng bất thường.
- Mở Task Manager (nhấn `Ctrl + Shift + Esc`) thấy một trong các chỉ số CPU 100%, Memory (RAM) trên 90% hoặc Disk 100%.

## Các bước tự khắc phục nhanh (Self-service)
*User self-service actions (Các thao tác người dùng tự kiểm tra):*
1. **Kiểm tra ứng dụng chiếm tài nguyên trong Task Manager:** Mở *Task Manager*, nhấn vào cột *CPU* hoặc *Memory* để sắp xếp ứng dụng đang tiêu thụ tài nguyên nhiều nhất từ cao xuống thấp.
2. **Đóng các ứng dụng nặng không sử dụng:** Tắt bớt các tab trình duyệt web không cần thiết (đặc biệt là các tab video, đồ họa), thoát hẳn các ứng dụng nặng đang chạy ngầm.
3. **Khởi động lại máy tính:** Khởi động lại hệ điều hành để giải phóng bộ nhớ RAM đệm và kết thúc các tiến trình nền bị rò rỉ bộ nhớ.
4. **Quét virus nhanh bằng Windows Security:** Mở *Windows Security -> Virus & threat protection -> Quick scan* để kiểm tra mã độc cơ bản.

## Khi nào cần chuyển thẳng cho IT (Escalation)
*IT Tier 2 administration actions (Trường hợp cần kỹ thuật viên IT can thiệp):*
- Tiến trình lạ của hệ thống (System, Service Host, Antimalware Service Executable) liên tục chiếm 100% CPU hoặc Disk không giảm sau 30 phút.
- Máy tính có hiện tượng nghi ngờ nhiễm mã độc, đào tiền ảo hoặc phần mềm độc hại phức tạp.
- Ổ cứng HDD/SSD có dấu hiệu bad sector, lỗi phần cứng cần kiểm tra SMART hoặc thay thế nâng cấp SSD/RAM.
- Cần quyền Administrator để cấu hình phân tích hiệu năng chuyên sâu; người dùng tuyệt đối không tự can thiệp vô hiệu hóa các dịch vụ bảo mật hay tắt service hệ thống.
