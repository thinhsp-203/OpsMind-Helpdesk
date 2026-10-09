# Network Printer Offline Status and SNMP Port Fix

## Symptoms
- Network printer displays status 'Offline' in Windows Settings and Devices and Printers, even though physical printer is powered on and display screen shows Ready.
- Print jobs enter queue with status 'Error - Printing' or 'Paused'.
- Ping to printer IP address succeeds, but Windows refuses to send print spool.

## Checks
1. Verify printer IP address: print network configuration sheet directly from printer LCD screen.
2. Open Command Prompt and test reachability: `ping <printer_ip>`.
3. Open web browser and navigate to `http://<printer_ip>` to verify the printer Embedded Web Server (EWS) is accessible.
4. In Windows, open Print Queue window > click Printer menu > check if 'Use Printer Offline' has a checkmark next to it.

## Resolution
- Uncheck 'Use Printer Offline': In Print Queue > click 'Printer' menu > ensure 'Use Printer Offline' is unchecked.
- Disable SNMP Status on the Standard TCP/IP port (Common cause of false offline status):
  1. Go to Control Panel > Devices and Printers > Right-click Printer > Printer properties.
  2. Select 'Ports' tab > highlight the printer port > click 'Configure Port...'.
  3. Uncheck the checkbox 'SNMP Status Enabled' > click OK.
  4. Restart Print Spooler service (`net stop spooler` then `net start spooler`).
- If printer IP changed due to DHCP lease drift, update the port IP to the new static IP address.

## Escalation
If printer Embedded Web Server is unreachable, escalate to Hardware Maintenance team to check printer network switch port and network card.

## Hướng dẫn nhanh (Tiếng Việt)
1. Mở cửa sổ hàng đợi máy in, vào menu 'Printer' kiểm tra xem mục 'Use Printer Offline' có đang bị tích chọn nhầm không (nếu có thì bỏ tích).
2. Vào Printer Properties > tab Ports > bấm 'Configure Port' > Bỏ tích chọn ô 'SNMP Status Enabled' rồi bấm OK.
3. Khởi động lại dịch vụ Print Spooler: Mở cmd gõ `net stop spooler` rồi `net start spooler`.
4. In thử trang cấu hình mạng từ màn hình máy in để đối chiếu xem địa chỉ IP máy in có bị nhảy sang số khác không.

## Source and scope
- Microsoft Learn, [Printer status is offline after installing an update or configuring SNMP](https://learn.microsoft.com/en-us/troubleshoot/windows-client/printing/printer-status-offline), accessed 2026-10-06.
