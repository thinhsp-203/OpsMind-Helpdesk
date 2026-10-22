# DHCP IP Address Conflict and DNS Troubleshooting

**Từ khóa:** DNS, DHCP, xung đột IP, trùng IP, lỗi phân giải tên miền, không vào được mạng, ipconfig, flushdns, renew IP, network conflict.

## Symptoms
- Device reports 'No Internet, secured' or 'Unidentified network'.
- Windows error popup: 'There is an IP address conflict with another system on the network' (Event ID 4199).
- Device assigned an APIPA address starting with 169.254.x.x.

## Checks
1. Run `ipconfig /all` in Command Prompt to verify IPv4 Address, Subnet Mask, Default Gateway, and DHCP Server.
2. If IP starts with 169.254.x.x, the client is unable to reach the corporate DHCP server.
3. Ping default gateway to check local network reachability (`ping <gateway_ip>`).
4. Test DNS resolution using `nslookup company.internal` or `nslookup google.com`.

## Resolution
- User Self-Service Actions (Safe & Recommended):
  1. Reconnect network cable or toggle Wi-Fi adapter off and on.
  2. Open Command Prompt and release/renew dynamic IP lease:
     ```cmd
     ipconfig /release
     ipconfig /renew
     ipconfig /flushdns
     ```
  3. Restart computer to re-initialize network stack services.
- IT Network Engineering Actions (Requires Elevated Rights):
  1. Reset network stack and Winsock catalog if network adapters are corrupted (run as Administrator):
     ```cmd
     netsh int ip reset
     netsh winsock reset
     ```
  2. Verify DHCP server scope capacity and resolve IP conflicts or rogue DHCP devices on the VLAN.

## Escalation
If multiple workstations in the same VLAN/subnet report IP conflicts, escalate immediately to Network Engineering to check DHCP scope exhaustion or rogue DHCP servers.

## Hướng dẫn nhanh (Tiếng Việt)
1. Mở Command Prompt (cmd), gõ `ipconfig /flushdns` rồi gõ `ipconfig /renew` để xin cấp lại địa chỉ IP từ máy chủ DHCP.
2. Kiểm tra phân giải tên miền bằng lệnh `nslookup company.internal` hoặc `nslookup google.com`.
3. Nếu máy báo địa chỉ IP dạng 169.254.x.x (APIPA), kiểm tra lại dây cáp mạng hoặc khởi động lại modem/switch khu vực.
4. Trường hợp cả phòng làm việc cùng mất mạng hoặc xung đột IP hàng loạt, báo ngay IT Network kiểm tra dải cấp phát DHCP; người dùng không tự ý đặt lại IP tĩnh.

## Source and scope
- Microsoft Learn, [Troubleshoot DHCP client issues](https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/troubleshoot-dhcp-client-issue), accessed 2026-10-06. Covers standard APIPA resolution and adapter resets.
