# Ethernet Disconnected and Cable Unplugged Error

## Symptoms
- Windows taskbar displays globe icon or red X with 'Network cable unplugged'.
- Ethernet adapter alternates rapidly between 'Identifying...' and 'Network cable unplugged'.
- Link LED lights on the computer RJ45 port or wall jack are unlit.

## Checks
1. Inspect the physical RJ45 cable connector: ensure the plastic latch is intact and clicked into place.
2. Check link LEDs on the computer NIC: Green/Amber light indicates physical link layer connectivity.
3. Test with a known good Cat5e/Cat6 patch cable.
4. Try plugging into an alternate network wall jack if available.

## Resolution
- Reseat both ends of the Ethernet cable (at the PC and at the wall/docking station).
- In Device Manager > Network Adapters > Right-click NIC > Disable device, wait 10 seconds, then Enable device.
- In NIC Advanced Properties, change 'Speed & Duplex' from 'Auto Negotiation' to '1.0 Gbps Full Duplex' or '100 Mbps Full Duplex' to test link stability.
- Power cycle any USB-C docking station or adapter being used.

## Escalation
If cable and wall jack are verified functional but no link LED appears, log a hardware ticket for IT Helpdesk to inspect the wall port patch panel in the server room.

## Hướng dẫn nhanh (Tiếng Việt)
1. Kiểm tra hai đầu cắm dây mạng RJ45 ở máy tính và ổ cắm tường; đảm bảo lẫy nhựa đã gài chắc chắn.
2. Quan sát đèn tín hiệu ở cổng cắm mạng máy tính (phải có đèn sáng xanh hoặc vàng nhấp nháy).
3. Thử rút ra cắm lại hoặc thay bằng dây cáp mạng khác đang hoạt động tốt.
4. Mở Device Manager, tắt (Disable) rồi bật lại (Enable) card mạng Ethernet.

## Source and scope
- Microsoft Support, [Fix Ethernet connection issues in Windows](https://support.microsoft.com/en-us/windows/fix-ethernet-connection-issues-in-windows-2311254b-42d4-4070-738e-7914a2414e02), accessed 2026-10-06.
