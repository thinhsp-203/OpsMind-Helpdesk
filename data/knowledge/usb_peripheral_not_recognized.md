# USB Peripheral and Smart Card Token Recognition Fix

## Symptoms
- Windows notification: 'USB device not recognized. The last USB device you connected to this computer malfunctioned'.
- Digital signature USB Token, mouse, or keyboard fails to respond or shows yellow exclamation mark in Device Manager.
- Device Manager displays: 'Unknown USB Device (Device Descriptor Request Failed)'.

## Checks
1. Try plugging the USB peripheral into a different USB port, preferably directly into the PC chassis rather than through an unpowered USB hub.
2. Test the USB peripheral on a secondary computer to verify whether the hardware token/device itself is damaged.
3. Open Device Manager (Win+X > Device Manager) and expand 'Universal Serial Bus controllers' and 'Smart card readers'.
4. Check for physical damage, lint, or bent pins inside the USB plug or port.

## Resolution
- Disconnect power supply / charger from laptop/PC for 30 seconds to drain motherboard residual capacitor charge, then reconnect.
- Reinstall USB controller drivers:
  1. In Device Manager, right-click the item with yellow exclamation mark > Uninstall device.
  2. Click Action menu > 'Scan for hardware changes'.
- Disable USB Selective Suspend Power Management:
  1. Control Panel > Power Options > Change plan settings > Change advanced power settings.
  2. Expand 'USB settings' > 'USB selective suspend setting' > set to 'Disabled'.
- For digital signature USB tokens (VNPT, Viettel, FPT, SafeNet): reinstall the official Token Manager middleware utility from software portal.

## Escalation
If physical USB ports on the laptop motherboard fail to recognize any devices, initiate a hardware warranty inspection with IT Asset Management.

## Hướng dẫn nhanh (Tiếng Việt)
1. Thử cắm USB/Token sang cổng cắm khác trực tiếp trên thân máy, tránh cắm qua cổng chia USB (hub) rời.
2. Mở Device Manager, tìm mục có dấu chấm than màu vàng, chuột phải chọn Uninstall device rồi chọn Scan for hardware changes.
3. Vào Power Options tắt chế độ 'USB selective suspend' để tránh Windows tự ngắt nguồn cổng USB khi tiết kiệm pin.
4. Đối với USB Token chữ ký số, tải và cài đặt lại phần mềm quản lý Token chính hãng (như SafeNet, VNPT-CA, Viettel-CA).

## Source and scope
- Microsoft Support, [Error: USB device not recognized in Windows](https://support.microsoft.com/en-us/windows/usb-device-not-recognized-in-windows-87612f9b-6f0e-436f-8769-122e391b1580), accessed 2026-10-06.
