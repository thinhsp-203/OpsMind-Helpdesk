"""Test Phase 4 Navi IT Helpdesk Auto-Triage classification and resolution scopes."""

from app.rag import generate_answer


def test_triage_six_navi_categories() -> None:
    # 1. Windows
    win = generate_answer("Máy tính bị màn hình xanh chết chóc BSOD và khởi động lại")
    assert win["triage"]["navi_category"] == "Windows"
    assert win["triage"]["resolution_scope"] in {"SELF_SERVICE", "ESCALATE_IT"}

    # 2. Office (2016/19/21/365)
    office = generate_answer("Outlook không gửi và nhận được thư mới, báo lỗi kết nối máy chủ mail")
    assert office["triage"]["navi_category"] == "Office (2016/19/21/365)"

    # 3. Teams
    teams = generate_answer("Không nhận được thông báo xác thực login approval trên Microsoft Authenticator")
    assert teams["triage"]["navi_category"] == "Teams"

    # 4. Máy in & Photo
    printer = generate_answer("Máy in bị kẹt lệnh trong hàng đợi print spooler")
    assert printer["triage"]["navi_category"] == "Máy in & Photo"

    # 5. Mạng (LAN/Wi-Fi Nội bộ/Khách)
    network = generate_answer("Dây cáp mạng cắm vào máy tính nhưng biểu tượng mạng hiện quả cầu có dấu gạch chéo")
    assert network["triage"]["navi_category"] == "Mạng (LAN/Wi-Fi Nội bộ/Khách)"

    # 6. VPN & NAS
    nas = generate_answer("Không thể truy cập vào thư mục dùng chung trên máy chủ lưu trữ NAS")
    assert nas["triage"]["navi_category"] == "VPN & NAS"


def test_resolution_scope_self_service_vs_escalate_it() -> None:
    # Self-service: Print spooler queue troubleshooting
    printer = generate_answer("Lệnh in bị kẹt trong hàng đợi print spooler không in ra được")
    assert printer["triage"]["resolution_scope"] == "SELF_SERVICE"

    # Self-service: Ethernet cable re-plug
    cable = generate_answer("Cáp mạng cắm vào máy tính nhưng hiện biểu tượng quả cầu gạch chéo")
    assert cable["triage"]["resolution_scope"] == "SELF_SERVICE"

    # Escalate IT: NAS folder permission / access denied
    nas_perm = generate_answer("Thư mục dùng chung trên mạng báo lỗi Access Denied không có quyền ghi dữ liệu")
    assert nas_perm["triage"]["resolution_scope"] == "ESCALATE_IT"
    assert "NAS" in nas_perm["triage"]["escalation_reason"] or "phân quyền" in nas_perm["triage"]["escalation_reason"].lower()

    # Escalate IT: AD Account Lockout (requires Domain Admin)
    lockout = generate_answer("Tài khoản của tôi bị khóa sau khi gõ sai mật khẩu nhiều lần")
    assert lockout["triage"]["resolution_scope"] == "ESCALATE_IT"
    assert "Active Directory" in lockout["triage"]["escalation_reason"]

    # Escalate IT: BitLocker 48-digit key (requires IT Admin key retrieval)
    bitlocker = generate_answer("Laptop yêu cầu nhập mã BitLocker Recovery Key 48 số")
    assert bitlocker["triage"]["resolution_scope"] == "ESCALATE_IT"
    assert "BitLocker" in bitlocker["triage"]["escalation_reason"]

    # Escalate IT: VPN request (policy restricted to Reception & IT)
    vpn_req = generate_answer("Yêu cầu cấp tài khoản VPN mới để làm việc tại nhà")
    assert vpn_req["triage"]["resolution_scope"] == "ESCALATE_IT"
    assert "Lễ tân và IT" in vpn_req["triage"]["escalation_reason"]

    # Escalate IT: Broken hardware / photocopier breakdown
    hardware = generate_answer("Máy photocopy bị hỏng phần cứng và kẹt giấy nặng bốc khói")
    assert hardware["triage"]["resolution_scope"] == "ESCALATE_IT"


def test_triage_backward_compatibility() -> None:
    """Verify legacy triage fields category and priority remain intact."""
    ans = generate_answer("Máy in bị kẹt lệnh")
    triage = ans["triage"]
    assert triage["category"] == "hardware"
    assert triage["priority"] in {"low", "medium", "high", "urgent"}
    assert triage["requires_confirmation"] is True
    assert "navi_category" in triage
    assert "priority_label" in triage
    assert "resolution_scope" in triage
