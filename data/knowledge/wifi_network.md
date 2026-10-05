# Wi-Fi and LAN Connectivity

## Common issues
- Device cannot join the Wi-Fi network.
- Laptop loses connectivity after waking from sleep.
- Internet works but internal services are unavailable.

## Recommended steps
1. Confirm the device is connecting to the correct SSID.
2. Forget the current network and reconnect with the enterprise credentials.
3. Check whether the adapter has a valid IP address and DNS configuration.
4. Run the network diagnostics tool and confirm there is no MAC filtering issue.

## Resolution
- If IP is missing or in the wrong range, renew the DHCP lease or restart the adapter.
- For internal application issues, confirm the user has VPN access and that the company DNS is reachable.
- If multiple users report the same issue, check the access point or switch logs for outage information.

## Escalation
Escalate to the network team if the problem affects multiple offices, several devices, or if the core switch shows high packet loss.

## Hướng dẫn nhanh (Tiếng Việt)
1. Xác nhận đang kết nối đúng Wi-Fi/SSID nội bộ.
2. Ngắt kết nối rồi kết nối lại bằng thông tin doanh nghiệp; không chia sẻ mật khẩu Wi-Fi công ty qua ticket công khai.
3. Nếu Wi-Fi kết nối nhưng không vào được ứng dụng nội bộ, xác nhận VPN và DNS nội bộ theo hướng dẫn IT.
4. Nếu nhiều thiết bị cùng mất mạng, ghi nhận vị trí và thời điểm rồi chuyển IT Network.
