# Remote Desktop (RDP) Connection and NLA Troubleshooting

## Symptoms
- Remote Desktop Connection displays: 'Remote Desktop can\'t connect to the remote computer for one of these reasons' (Error code 0x204 or 0x104).
- Error popup: 'An authentication error has occurred. The function requested is not supported' (CredSSP / NLA error).
- Screen remains black upon connecting or immediately minimizes and disconnects.

## Checks
1. Ensure the user is connected to corporate LAN or connected to corporate VPN before initiating RDP.
2. In Command Prompt, test port 3389 reachability: `powershell Test-NetConnection -ComputerName <target_ip> -Port 3389`.
3. Verify target workstation is powered on, awake (not in Sleep/Hibernate mode), and logged in or at lock screen.
4. Verify user account is in the 'Remote Desktop Users' group on the target machine.

## Resolution
- Verify hostname/IP address entered in `mstsc.exe` is correct.
- If CredSSP encryption oracle error occurs, install latest Windows Cumulative Updates on both client and host machines.
- On host computer: System Properties > Remote tab > ensure 'Allow remote connections to this computer' is selected.
- Lower display configuration: In RDP client > Show Options > Display tab > set Colors to 'High Color (16 bit)' if connection bandwidth is limited.

## Escalation
If target machine shows port 3389 closed, dispatch on-site IT Helpdesk technician to check target computer power status and Windows Defender Firewall inbound RDP rules.

## Hướng dẫn nhanh (Tiếng Việt)
1. Bắt buộc phải kết nối VPN công ty trước khi mở ứng dụng Remote Desktop Connection (`mstsc`).
2. Kiểm tra lại địa chỉ IP máy tính bàn tại văn phòng và đảm bảo máy ở công ty đang bật nguồn (không bị tắt hay sleep).
3. Cập nhật Windows Update mới nhất trên cả máy ở nhà và máy công ty để khắc phục lỗi bảo mật CredSSP.
4. Nếu báo lỗi quyền truy cập, liên hệ IT để được cấp quyền vào nhóm 'Remote Desktop Users'.

## Source and scope
- Microsoft Learn, [Troubleshoot Remote Desktop disconnected errors](https://learn.microsoft.com/en-us/troubleshoot/windows-server/remote/troubleshoot-remote-desktop-disconnected-errors), accessed 2026-10-06.
