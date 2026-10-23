# Hướng dẫn xử lý sự cố kết nối Wi-Fi nội bộ và Wi-Fi khách

**Từ khóa:** Wi-Fi, wifi, wireless connectivity, internal company apps are unavailable, multiple devices, corporate DNS, Wi-Fi connects but internal company apps are unavailable, Several users in one office lost wireless connectivity, mạng không dây, sóng wifi, kết nối wifi, Wi-Fi nội bộ, Wi-Fi khách, không kết nối được, mật khẩu wifi, ngắt kết nối, SSID, DHCP lease, adapter, access point, network team.

## Triệu chứng / Dấu hiệu nhận biết
- Wi-Fi connects but internal company apps are unavailable (kết nối Wi-Fi nhưng ứng dụng nội bộ công ty không mở được do cần VPN hoặc Corporate DNS).
- Several users in one office lost wireless connectivity (nhiều người dùng trong một văn phòng bị mất kết nối mạng không dây multiple devices).
- Máy tính hoặc laptop không kết nối được vào mạng Wi-Fi nội bộ của công ty (Corporate Wi-Fi) hoặc mạng Wi-Fi khách (Guest Wi-Fi).
- Bấm vào tên Wi-Fi nhưng hệ thống quay tròn rất lâu rồi báo lỗi: "Can't connect to this network" hoặc kết nối được nhưng hiện dòng chữ "No internet, secured".
- Máy tính không nhận diện được danh sách mạng Wi-Fi xung quanh (mục Wi-Fi biến mất hoàn toàn trong Windows).

## Các bước tự khắc phục nhanh (Self-service)
1. **Quên mạng Wi-Fi và kết nối lại (Forget Network):**
   - Vào *Settings -> Network & internet -> Wi-Fi -> Manage known networks*.
   - Tìm tên sóng Wi-Fi công ty (SSID) đang bị lỗi, bấm nút *Forget* để xóa cấu hình và mật khẩu cũ đã lưu.
   - Bấm vào biểu tượng mạng ở Taskbar, chọn lại tên Wi-Fi đó và nhập lại mật khẩu wifi chính xác để kết nối lại.
2. **Bật tắt lại card mạng Wi-Fi (Adapter):** Bật chế độ máy bay (Airplane mode) khoảng 5 giây rồi tắt đi, hoặc gạt công tắc Wi-Fi trong Windows sang Off rồi bật lại sang On.
3. **Kiểm tra địa chỉ IP (DHCP Lease):** Mở cửa sổ Command Prompt (`cmd`), gõ lệnh `ipconfig /renew` để yêu cầu bộ phát Wi-Fi (Access Point) cấp lại địa chỉ IP mới.
4. **Chọn đúng mạng:**
   - Dùng mạng **Wi-Fi nội bộ** khi cần truy cập máy chủ tệp NAS, phần mềm kế toán, máy in văn phòng.
   - Dùng mạng **Wi-Fi khách** cho các thiết bị cá nhân hoặc khách hàng đến làm việc (mạng khách không truy cập được vào máy chủ nội bộ).

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Khi several users in one office lost wireless connectivity trên multiple devices, chuyển đội mạng (network team) kiểm tra access point.
- Khi Wi-Fi connects but internal company apps are unavailable, chuyển IT kiểm tra Corporate DNS và định tuyến VPN.
- Nhiều thiết bị trong cùng một phòng ban hoặc cả tầng văn phòng đồng loạt bị mất sóng Wi-Fi hoặc không được cấp IP (nghi ngờ lỗi thiết bị phát Access Point hoặc lỗi máy chủ DHCP của công ty).
- Card Wi-Fi trên laptop bị lỗi phần cứng hoặc mất driver điều khiển sau khi cài lại Windows.
- Chuyển yêu cầu cho nhóm kỹ thuật mạng (Network Team) để kiểm tra bộ điều khiển Controller và băng thông mạng tổng.
