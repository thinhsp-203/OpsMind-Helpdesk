# Network Printer Driver Installation via Standard TCP/IP Port

## Symptoms
- User receives new PC or moves to a new department and needs access to shared floor printer.
- Windows auto-discovery fails to find network printer, or installs generic driver without duplex/color options.
- Error 0x0000011b or 0x00000709 when connecting to a Windows shared printer.

## Checks
1. Obtain the floor printer model (e.g., HP LaserJet Enterprise, Canon imageRUNNER, Ricoh Aficio) and designated IP address from IT floor directory.
2. Verify target PC can ping the printer IP address.
3. Verify appropriate PCL6 or PostScript driver installer is downloaded from corporate software repository (`\\fileserver\drivers`).

## Resolution
- Install printer directly using Standard TCP/IP port to bypass print server RPC restrictions:
  1. Open Settings > Bluetooth & devices > Printers & scanners > click 'Add device' > 'The printer that I want isn\'t listed'.
  2. Select 'Add a printer using an IP address or hostname' > click Next.
  3. Device type: 'TCP/IP Device' > enter the printer IP address > uncheck 'Query the printer and automatically select driver'.
  4. Click 'Have Disk...' and browse to downloaded corporate PCL6/Universal driver folder.
  5. Enter a clear printer name (e.g., `Floor-2-HP-LaserJet-Color`).
  6. Select 'Do not share this printer' > Print a test page to verify.

## Escalation
If users lack local Administrator rights to install print drivers, request IT Helpdesk deployment via Group Policy (GPO) or Intune.

## Hướng dẫn nhanh (Tiếng Việt)
1. Tra cứu địa chỉ IP của máy in tầng (thường dán nhãn trên thân máy in hoặc hỏi IT văn phòng).
2. Vào Settings > Printers & scanners > chọn Add printer manually > 'Add a printer using an IP address or hostname'.
3. Nhập IP máy in, chọn driver chuẩn PCL6 từ thư mục phần mềm công ty.
4. Đặt tên máy in theo quy chuẩn (ví dụ: `MayIn-Tang3-Canon`) và in thử 1 trang test page để kiểm tra.

## Source and scope
- Microsoft Learn, [Add a printer by using an IP address in Windows](https://support.microsoft.com/en-us/windows/install-a-printer-in-windows-147863eb-e2ec-436e-b7a4-0b157705d042), accessed 2026-10-06.
