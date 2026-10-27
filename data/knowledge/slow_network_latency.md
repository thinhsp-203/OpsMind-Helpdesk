# Kiểm tra và xử lý sự cố mạng chậm, độ trễ cao và rớt gói tin (Packet Loss)

**Từ khóa:** mạng chậm, mạng lag, độ trễ cao, ping cao, nghẽn mạng, rớt gói ping, packet loss, mạng nội bộ, kết nối chậm, giật lag, độ trễ mạng.

## Triệu chứng / Dấu hiệu nhận biết
- Duyệt web rất chậm, tải tài liệu trên mạng nội bộ hoặc Google Drive mất nhiều thời gian, video cuộc họp trên Teams bị giật hình hoặc mất tiếng.
- Ứng dụng quản lý nghiệp vụ và phần mềm kế toán liên tục bị ngắt kết nối giữa chừng với máy chủ.
- Chạy lệnh ping kiểm tra đến máy chủ thấy thời gian phản hồi (latency) rất cao (trên 150ms - 300ms) hoặc xuất hiện nhiều dòng "Request timed out" (rớt gói tin / packet loss).

## Các bước tự khắc phục nhanh (Self-service)
1. **Kiểm tra các ứng dụng đang tải dữ liệu ngầm:**
   - Mở *Task Manager* (`Ctrl + Shift + Esc`), xem cột *Network* để kiểm tra xem có ứng dụng nào đang tải tệp nặng (OneDrive, Torrent, cập nhật phần mềm, tải video) hay không.
   - Tạm dừng các tiến trình đồng bộ dữ liệu nặng trong giờ làm việc cao điểm.
2. **Kiểm tra ping tới Gateway mạng nội bộ:**
   - Mở Command Prompt (`cmd`), gõ lệnh ping địa chỉ Default Gateway của phòng (ví dụ: `ping 192.168.1.1 -n 10`).
   - Nếu ping mạng nội bộ dưới 5ms nhưng ping ra mạng ngoài bị chậm, nguyên nhân do đường truyền Internet của nhà mạng (ISP).
3. **Chuyển sang cắm mạng dây LAN thay vì Wi-Fi:** Nếu đang dùng Wi-Fi ở vị trí xa cục phát hoặc có nhiều vật cản, hãy thử cắm dây mạng LAN trực tiếp vào máy để có đường truyền ổn định nhất.
4. **Khởi động lại máy tính:** Tắt các ứng dụng chạy ngầm và khởi động lại máy để làm mới stack kết nối mạng TCP/IP.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Toàn bộ công ty hoặc toàn bộ phòng ban đều bị chậm mạng đồng thời (nghi ngờ nghẽn băng thông đường truyền chính hoặc sự cố từ nhà cung cấp dịch vụ Internet ISP).
- Tỷ lệ rớt gói tin ping (packet loss) vượt quá 10% trong mạng dây nội bộ (nghi ngờ lỗi cổng switch mạng hoặc vòng lặp mạng loop mạng).
- Cần IT kiểm tra và điều chỉnh phân bổ băng thông (QoS) trên tường lửa trung tâm.
