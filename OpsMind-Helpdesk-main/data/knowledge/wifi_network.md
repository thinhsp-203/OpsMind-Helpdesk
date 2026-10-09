# Wi-Fi and LAN Connectivity

## Common issues
- Device cannot join the Wi-Fi network.
- Laptop loses connectivity after waking from sleep.
- Internet works but internal services are unavailable.

## Recommended steps
1. Confirm the device is connecting to the correct SSID.
2. Check Airplane mode and the Windows connection status.
3. For a user-managed network only, forget and reconnect if the user has approved credentials. Do not remove a company-managed profile without IT.
4. Check whether another device can join the same network. Record the location, time, and whether other users are affected.

## Resolution
- For a home network, restarting the user's router may help; do not power-cycle shared office network equipment.
- Ask IT to check IP/DNS configuration, access-point health, and network policy when the device connects but internal services remain unavailable.
- Driver reinstall or network reset can interrupt connectivity; leave these steps to IT on managed devices.

## Escalation
Escalate to the network team if the problem affects multiple offices, several devices, or if the core switch shows high packet loss.

## Hướng dẫn nhanh (Tiếng Việt)
1. Xác nhận đang kết nối đúng Wi-Fi/SSID nội bộ.
2. Ngắt kết nối rồi kết nối lại bằng thông tin doanh nghiệp; không chia sẻ mật khẩu Wi-Fi công ty qua ticket công khai.
3. Nếu Wi-Fi kết nối nhưng không vào được ứng dụng nội bộ, xác nhận VPN và DNS nội bộ theo hướng dẫn IT.
4. Nếu nhiều thiết bị cùng mất mạng, ghi nhận vị trí và thời điểm rồi chuyển IT Network.

## Source and scope
- Microsoft Support, [Fix Wi-Fi connection issues in Windows](https://support.microsoft.com/en-us/windows/experience/connectivity-networking/fix-wi-fi-connection-issues-in-windows), accessed 2026-10-05. Covers connection checks, Airplane mode, forgetting/reconnecting, router restart, testing another device, and advanced Windows network steps. Corporate SSID, DNS, access point, and policy changes remain organization-specific and must be handled by IT.
