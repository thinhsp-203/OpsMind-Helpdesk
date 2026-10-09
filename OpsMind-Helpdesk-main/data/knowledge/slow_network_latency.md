# High Network Latency and Packet Loss Troubleshooting

## Symptoms
- High ping times (> 150ms) to internal servers or gateways.
- Video calls (Teams/Zoom) lag, drop audio, or disconnect frequently.
- File transfer speeds to shared network drives are unusually slow (< 1 MB/s).

## Checks
1. Check continuous ping to local gateway: ping -t <gateway_ip>. Packet loss should be 0%.
2. Run 	racert 8.8.8.8 to identify which network hop introduces high latency.
3. Check Task Manager > Performance > Ethernet/Wi-Fi for background upload/download traffic.
4. Verify if peer-to-peer applications, cloud sync (OneDrive/Google Drive), or Windows Updates are consuming bandwidth.

## Resolution
- Pause heavy background synchronization services (OneDrive, Dropbox, torrent clients).
- Update network interface card (NIC) drivers via Device Manager.
- Disable Energy Efficient Ethernet (Green Ethernet) in NIC advanced properties.
- For Wi-Fi connections, switch from 2.4 GHz to 5 GHz frequency band for lower interference.
- If using an Ethernet switch hub at the desk, bypass the hub and connect directly to the wall port.

## Escalation
If packet loss occurs at the core switch or internet firewall gateway, escalate to Network Operations Center (NOC) with traceroute logs.

## Hướng dẫn nhanh (Tiếng Việt)
1. Mở Command Prompt gõ ping 8.8.8.8 -t để kiểm tra độ trễ và tỷ lệ rớt gói (packet loss).
2. Mở Task Manager (Ctrl+Shift+Esc), kiểm tra xem có ứng dụng nào (OneDrive, Windows Update) đang chiếm dụng 100% băng thông mạng không.
3. Nếu dùng Wi-Fi, ưu tiên kết nối vào băng tần 5GHz thay vì 2.4GHz để giảm nhiễu.
4. Thử cắm trực tiếp dây mạng vào ổ mạng tường thay vì cắm qua các switch chia nhỏ tại bàn làm việc.

## Source and scope
- Cisco Networking Documentation, [Troubleshooting High Latency and Packet Loss](https://www.cisco.com/c/en/us/support/docs/ip/routing-information-protocol-rip/13769-4.html), accessed 2026-10-06.
