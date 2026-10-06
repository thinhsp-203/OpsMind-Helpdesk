# DHCP IP Address Conflict and DNS Troubleshooting

## Symptoms
- Device reports 'No Internet, secured' or 'Unidentified network'.
- Windows error popup: 'There is an IP address conflict with another system on the network' (Event ID 4199).
- Device assigned an APIPA address starting with 169.254.x.x.

## Checks
1. Run ipconfig /all in Command Prompt to verify IPv4 Address, Subnet Mask, Default Gateway, and DHCP Server.
2. If IP starts with 169.254.x.x, the client is unable to reach the corporate DHCP server.
3. Ping default gateway to check local network reachability (ping <gateway_ip>).
4. Test DNS resolution using 
slookup company.internal or 
slookup google.com.

## Resolution
- Release and renew dynamic IP lease via Command Prompt:
  `cmd
  ipconfig /release
  ipconfig /renew
  ipconfig /flushdns
  `
- Reset network stack and Winsock catalog if network adapters are corrupted:
  `cmd
  netsh int ip reset
  netsh winsock reset
  `
- If a static IP was assigned manually, verify with IT Network team before changing adapter settings back to 'Obtain an IP address automatically'.
- Restart computer to re-initialize network adapter services.

## Escalation
If multiple workstations in the same VLAN/subnet report IP conflicts, escalate immediately to Network Engineering to check DHCP scope exhaustion or rogue DHCP servers.

## Hướng dẫn nhanh (Tiếng Việt)
1. Mở Command Prompt (cmd) với quyền Administrator.
2. Gõ ipconfig /flushdns rồi gõ ipconfig /renew để xin cấp lại địa chỉ IP từ máy chủ DHCP.
3. Nếu máy báo địa chỉ IP dạng 169.254.x.x, kiểm tra lại dây cáp mạng hoặc khởi động lại modem/switch khu vực.
4. Trường hợp cả phòng làm việc cùng mất mạng hoặc xung đột IP hàng loạt, báo ngay IT Network kiểm tra dải DHCP.

## Source and scope
- Microsoft Learn, [Troubleshoot DHCP client issues](https://learn.microsoft.com/en-us/troubleshoot/windows-server/networking/troubleshoot-dhcp-client-issue), accessed 2026-10-06. Covers standard APIPA resolution and adapter resets.
