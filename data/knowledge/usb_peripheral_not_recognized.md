# Xử lý lỗi không nhận diện cổng USB, chuột, bàn phím và thiết bị ngoại vi

**Từ khóa:** USB không nhận, không nhận chuột, không nhận bàn phím, cổng USB, USB token, thiết bị ngoại vi, Device Manager, USB not recognized, chập chờn, USB signing token, driver ngoại vi.

## Triệu chứng / Dấu hiệu nhận biết
- Cắm chuột, bàn phím, USB lưu trữ hoặc USB token chữ ký số nhưng đèn thiết bị không sáng hoặc máy tính không nhận diện.
- Windows phát âm thanh ngắt kết nối liên tục hoặc hiện thông báo "USB device not recognized" ở góc phải màn hình.
- Trong Device Manager xuất hiện biểu tượng tam giác vàng chấm than cảnh báo tại mục *Universal Serial Bus controllers*.

## Các bước tự khắc phục nhanh (Self-service)
1. **Cắm sang cổng USB khác:** Thử rút thiết bị ra và cắm sang một cổng USB khác trực tiếp trên thân máy tính (ưu tiên cắm cổng phía sau của máy bàn case, tránh cắm qua hub chia cổng).
2. **Vệ sinh đầu cắm:** Kiểm tra xem đầu cắm USB và khe cắm trên máy tính có bị bám bụi bẩn, dị vật hoặc lỏng chân tiếp xúc hay không.
3. **Thử trên thiết bị khác:** Cắm thử chuột/USB đó sang máy tính đồng nghiệp bên cạnh để xác định lỗi do thiết bị ngoại vi hay do cổng USB của máy mình.
4. **Khởi động lại máy:** Khởi động lại hệ điều hành Windows để hệ thống nạp lại driver điều khiển cổng USB.

## Khi nào cần chuyển thẳng cho IT (Escalation)
- Toàn bộ các cổng USB trên máy tính đều bị mất nguồn và không nhận bất kỳ thiết bị nào (nghi ngờ hỏng chip cầu nam hoặc lỗi bo mạch chủ).
- USB token chữ ký số chuyên dụng không nhận driver middleware dù đã cắm đúng cổng (cần IT cài đặt phần mềm ký số bản quyền).
- Cổng USB bị gãy chân tiếp xúc vật lý hoặc có mùi khét, chạm chập điện.
