# VPN Split Tunneling and Internal Subnet Routing

## Symptoms
- User is connected to corporate VPN but cannot open internal intranet websites (10.x.x.x or 192.168.x.x).
- Public internet traffic is extremely slow because all traffic routes through company gateway.
- Internal network shares fail to connect while VPN icon shows connected.

## Checks
1. In Command Prompt, run `route print` to check the active IPv4 routing table.
2. Check if default route (0.0.0.0) points to corporate VPN gateway or local home router.
3. Test ping to internal corporate DNS server (e.g., `ping 10.0.0.2`).
4. In FortiClient/AnyConnect/OpenVPN settings, verify if Split Tunnel policy is active.

## Resolution
- If corporate policy permits Split Tunneling, ensure the VPN client configuration does not enable 'Use default gateway on remote network'.
- In Windows Adapter properties > IPv4 > Advanced > uncheck 'Use default gateway on remote network' if custom manual split tunneling is authorized.
- Flush routing and DNS cache: `ipconfig /flushdns`.
- Reconnect VPN profile to receive updated route table pushed by VPN Gateway.

## Escalation
Contact IT Network Security team if custom static routes to internal database subnets (e.g., SAP, Oracle, ERP) are missing from the central VPN firewall profile.

## Hướng dẫn nhanh (Tiếng Việt)
1. Ngắt kết nối VPN và kết nối lại để cập nhật bảng định tuyến (routing table) mới nhất từ Gateway.
2. Kiểm tra xem có ping được địa chỉ IP máy chủ nội bộ (10.x.x.x) trong cmd không.
3. Nếu vào mạng bên ngoài quá chậm khi bật VPN, kiểm tra xem cấu hình VPN của bạn có được bật Split Tunneling không.
4. Trường hợp không truy cập được một máy chủ ERP hoặc Database cụ thể, gửi ticket cho nhóm Network bổ sung route.

## Source and scope
- Fortinet Knowledge Base, [Configuring SSL VPN with Split Tunneling](https://docs.fortinet.com/document/fortigate/7.4.0/administration-guide/526743/split-tunneling-for-ssl-vpn), accessed 2026-10-06.
