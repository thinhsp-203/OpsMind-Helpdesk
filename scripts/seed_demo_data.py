#!/usr/bin/env python3
"""Seed realistic demo dataset for OpsMind Helpdesk thesis defense.

Usage:
    py scripts/seed_demo_data.py [--reset] [--overwrite-passwords] [--yes]

Options:
    --reset                Clear existing tickets/comments/audit logs before seeding (preserves schema & KB)
    --overwrite-passwords  Overwrite existing users' passwords with demo passwords (default: keep existing passwords)
    --yes, --force         Confirm running against remote DATABASE_URL (e.g. Neon Postgres)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment
env_file = PROJECT_ROOT / ".env"
if env_file.is_file():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

os.environ.setdefault("DEMO_MODE", "true")

from app import config, store  # noqa: E402
from app.config import STORAGE_PATH  # noqa: E402


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def main() -> int:
    reset_data = "--reset" in sys.argv
    print("=" * 65)
    print("  OpsMind Helpdesk — Seeding Demo Data for Thesis Defense")
    print("=" * 65)

    base_time = datetime.now(timezone.utc)

    if config.DATABASE_URL and "--force" not in sys.argv and "--yes" not in sys.argv:
        from urllib.parse import urlparse
        try:
            parsed = urlparse(config.DATABASE_URL)
            db_host = parsed.hostname or "remote-host"
        except Exception:
            db_host = "remote-host"
        print(f"\n[CẢNH BÁO BẢO MẬT] Phát hiện cấu hình DATABASE_URL trỏ tới cơ sở dữ liệu từ xa: {db_host}")
        print("Script seed_demo_data.py sẽ thao tác trực tiếp trên CSDL này.")
        print("Để tiếp tục, vui lòng chạy lại kèm cờ --yes hoặc --force (Ví dụ: py scripts/seed_demo_data.py --yes)")
        return 1

    with store._connect() as conn:
        if reset_data:
            print("[*] Đang làm sạch dữ liệu cũ (--reset)...")
            conn.execute("DELETE FROM comments")
            conn.execute("DELETE FROM audit_logs")
            conn.execute("DELETE FROM ticket_attachments")
            conn.execute("DELETE FROM tickets")
            conn.execute("DELETE FROM chat_messages")
            conn.execute("DELETE FROM chat_sessions")
            print("    [OK] Đã xóa tickets, comments, audit logs, chat sessions.")

        # 1. Seed Users with strong passwords
        print("\n[1/4] Khởi tạo tài khoản người dùng chuẩn...")
        overwrite_passwords = "--overwrite-passwords" in sys.argv
        demo_users = [
            # (username, password, role, full_name, email, dept, phone)
            ("admin", "OpsMindAdmin2026!", "admin", "Nguyễn Hoàng Minh (Admin)", "admin@opsmind.vn", "IT Operations", "0901234567"),
            ("agent_nam", "AgentPass2026!", "agent", "Nguyễn Văn Nam (IT Net)", "nam.nguyen@opsmind.vn", "Hạ tầng & Mạng", "0912345678"),
            ("agent_hoa", "AgentPass2026!", "agent", "Trần Thị Hoa (IT Sec/App)", "hoa.tran@opsmind.vn", "Hệ thống & Ứng dụng", "0923456789"),
            ("user_linh", "UserPass2026!", "user", "Lê Thùy Linh (Kế toán)", "linh.le@opsmind.vn", "Phòng Kế toán", "0934567890"),
            ("user_tuan", "UserPass2026!", "user", "Phạm Anh Tuấn (Kinh doanh)", "tuan.pham@opsmind.vn", "Phòng Kinh doanh", "0945678901"),
            ("user_mai", "UserPass2026!", "user", "Hoàng Thị Mai (Nhân sự)", "mai.hoang@opsmind.vn", "Phòng Nhân sự", "0956789012"),
        ]

        for u, pwd, role, fn, mail, dept, ph in demo_users:
            existing = conn.execute("SELECT username FROM users WHERE username = ?", (u,)).fetchone()
            if not existing:
                conn.execute(
                    """
                    INSERT INTO users (username, password_hash, role, full_name, email, department, phone, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (u, store._password_hash(pwd), role, fn, mail, dept, ph),
                )
                print(f"    + Tạo mới: {u:12} [{role:5}] - {fn}")
            elif overwrite_passwords:
                conn.execute(
                    """
                    UPDATE users SET password_hash = ?, role = ?, full_name = ?, email = ?, department = ?, phone = ?, is_active = 1
                    WHERE username = ?
                    """,
                    (store._password_hash(pwd), role, fn, mail, dept, ph, u),
                )
                print(f"    * Cập nhật (ghi đè mật khẩu demo): {u:12} [{role:5}] - {fn}")
            else:
                conn.execute(
                    """
                    UPDATE users SET role = ?, full_name = ?, email = ?, department = ?, phone = ?, is_active = 1
                    WHERE username = ?
                    """,
                    (role, fn, mail, dept, ph, u),
                )
                print(f"    * Cập nhật thông tin (giữ mật khẩu hiện tại): {u:12} [{role:5}] - {fn}")

    # Ensure KB is initialized
    store.initialize_store()

    # 2. Seed 20 Tickets with full lifecycle
    print("\n[2/4] Khởi tạo 20 ticket đa dạng trạng thái, ưu tiên và danh mục...")
    tickets_specs = [
        # --- NEW (3) ---
        {
            "title": "Lỗi kết nối máy in phòng Kế toán tầng 3",
            "desc": "Máy in HP LaserJet P2035 báo đèn vàng nhấp nháy, các máy trạm không thể in phiếu thu chi cuối tháng.",
            "cat": "hardware", "prio": "medium", "req": "user_linh", "status": "new",
            "delta_hours_ago": 3,
        },
        {
            "title": "Không thể truy cập ổ đĩa dùng chung Z:\\Projects",
            "desc": "Sáng nay mở File Explorer báo 'Access is denied'. Cần lấy tài liệu báo giá gửi khách hàng gấp.",
            "cat": "security", "prio": "high", "req": "user_tuan", "status": "new",
            "delta_hours_ago": 1,
        },
        {
            "title": "Xin cấp tài khoản phần mềm kế toán MISA cho nhân sự mới",
            "desc": "Nhân viên thực tập Nguyễn Thị Thu bắt đầu làm việc từ tuần này, cần cấp quyền phân hệ Kế toán mua hàng.",
            "cat": "software", "prio": "low", "req": "user_linh", "status": "new",
            "delta_hours_ago": 6,
        },
        # --- IN_PROGRESS (3) ---
        {
            "title": "Mất kết nối mạng LAN tại khu vực Kinh doanh tầng 2",
            "desc": "Cả dãy bàn kinh doanh 8 máy không có IP (báo 169.254.x.x), đã thử cắm lại switch nhưng chưa được.",
            "cat": "network", "prio": "urgent", "req": "user_tuan", "status": "in_progress",
            "assignee": "agent_nam", "delta_hours_ago": 2,
            "comments": [
                ("agent_nam", "IT đang kiểm tra switch trung gian tầng 2 và cổng uplink kết nối Core switch."),
                ("user_tuan", "Dạ nhờ IT xử lý sớm giúp team em đang chốt hợp đồng quý."),
            ],
        },
        {
            "title": "Outlook báo lỗi hòm thư vượt dung lượng 50GB",
            "desc": "Không thể gửi và nhận mail từ chiều qua. Xuất hiện thông báo 'Mailbox quota exceeded'.",
            "cat": "software", "prio": "medium", "req": "user_mai", "status": "in_progress",
            "assignee": "agent_hoa", "delta_hours_ago": 8,
            "comments": [
                ("agent_hoa", "Chào chị Mai, em đang tạo file lưu trữ archive .PST cho các email từ năm 2024 trở về trước."),
            ],
        },
        {
            "title": "Màn hình xanh BSOD (CRITICAL_PROCESS_DIED) khi khởi động",
            "desc": "Máy trạm Dell Optiplex sau bản update Windows sáng nay thì liên tục khởi động lại vào màn hình xanh.",
            "cat": "software", "prio": "high", "req": "user_tuan", "status": "in_progress",
            "assignee": "agent_nam", "delta_hours_ago": 4,
            "comments": [
                ("agent_nam", "Đã thu thập file minidump, nghi vấn driver card mạng Intel bị xung đột với bản vá mới."),
            ],
        },
        # --- PENDING_WAITING_USER (2) ---
        {
            "title": "Không nhận diện chữ ký số khi ký hóa đơn điện tử",
            "desc": "Cắm USB Token Viettel-CA vào máy nhưng phần mềm hóa đơn báo không tìm thấy chứng thư hợp lệ.",
            "cat": "security", "prio": "high", "req": "user_linh", "status": "pending_waiting_user",
            "assignee": "agent_hoa", "delta_hours_ago": 12,
            "comments": [
                ("agent_hoa", "Em đã cài lại middleware Token Manager. Chị Linh cắm lại USB sang cổng USB phía sau thùng máy và kiểm tra lại giúp em nhé."),
            ],
        },
        {
            "title": "Cần mở port firewall truy cập máy chủ nội bộ qua VPN",
            "desc": "Nhân viên làm việc từ xa cần kết nối vào máy chủ kiểm thử 192.168.10.50 cổng 8443.",
            "cat": "network", "prio": "medium", "req": "user_tuan", "status": "pending_waiting_user",
            "assignee": "agent_nam", "delta_hours_ago": 15,
            "comments": [
                ("agent_nam", "Anh Tuấn vui lòng cung cấp địa chỉ IP tĩnh hoặc user VPN cần cấp quyền để IT tạo chính sách tường lửa."),
            ],
        },
        # --- RESOLVED (3) ---
        {
            "title": "Lỗi Autodiscover khi cấu hình email Outlook trên máy mới",
            "desc": "Nhập địa chỉ email và mật khẩu nhưng wizard tự động không tải được thông số Exchange.",
            "cat": "software", "prio": "medium", "req": "user_mai", "status": "resolved",
            "assignee": "agent_hoa", "delta_hours_ago": 20,
            "rating": 5, "rating_cmt": "IT hỗ trợ rất nhanh qua TeamViewer, hướng dẫn tận tình!",
            "comments": [
                ("agent_hoa", "Đã thêm bản ghi registry cấu hình ExcludeExplicitO365Endpoint và kết nối thành công."),
            ],
        },
        {
            "title": "Mạng Wi-Fi nội bộ chập chờn tại phòng họp 301",
            "desc": "Trong cuộc họp ban giám đốc sáng nay sóng Wi-Fi bị ngắt liên tục, mất kết nối trình chiếu không dây.",
            "cat": "network", "prio": "high", "req": "user_linh", "status": "resolved",
            "assignee": "agent_nam", "delta_hours_ago": 26,
            "rating": 4, "rating_cmt": "Đã đo lại sóng thấy ổn định, phòng họp đã kết nối mượt.",
            "comments": [
                ("agent_nam", "Đã điều chỉnh công suất phát và chuyển kênh tần số của Access Point Aruba AP-301 sang channel 36 tránh nghẽn."),
            ],
        },
        {
            "title": "Tài khoản Active Directory bị khóa sau 3 lần nhập sai",
            "desc": "Do đổi mật khẩu điện thoại chưa cập nhật nên bị khóa tài khoản đăng nhập Windows.",
            "cat": "security", "prio": "urgent", "req": "user_tuan", "status": "resolved",
            "assignee": "agent_hoa", "delta_hours_ago": 5,
            "rating": 5, "rating_cmt": "Mở khóa ngay sau 5 phút gọi điện, kịp giờ gửi báo cáo.",
            "comments": [
                ("agent_hoa", "Đã mở khóa tài khoản và hướng dẫn anh Tuấn xóa thông tin Wi-Fi cũ trên điện thoại."),
            ],
        },
        # --- CLOSED (4) ---
        {
            "title": "Cài đặt máy in HP LaserJet cho phòng Nhân sự",
            "desc": "Phòng Nhân sự mới được cấp thêm máy in mới, cần chia sẻ cho 4 máy trong phòng.",
            "cat": "hardware", "prio": "low", "req": "user_mai", "status": "closed",
            "assignee": "agent_nam", "delta_hours_ago": 72,
            "rating": 5, "rating_cmt": "In rất tốt, đã hướng dẫn in 2 mặt.",
        },
        {
            "title": "Cập nhật chứng chỉ số SSL cho ứng dụng ERP nội bộ",
            "desc": "Trình duyệt cảnh báo chứng chỉ số hết hạn 'Your connection is not private' khi truy cập erp.noi-bo.vn.",
            "cat": "security", "prio": "high", "req": "user_linh", "status": "closed",
            "assignee": "agent_hoa", "delta_hours_ago": 96,
            "rating": 5, "rating_cmt": "Chứng chỉ đã xanh, hết cảnh báo.",
        },
        {
            "title": "Dây cáp mạng RJ45 bị gãy lẫy tiếp xúc tại bàn làm việc",
            "desc": "Dây mạng lỏng chân cắm, hơi động vào là mất mạng.",
            "cat": "network", "prio": "low", "req": "user_tuan", "status": "closed",
            "assignee": "agent_nam", "delta_hours_ago": 120,
            "rating": 4, "rating_cmt": "Đã bấm lại đầu hạt mạng mới chắc chắn.",
        },
        {
            "title": "Nâng cấp RAM laptop Lenovo ThinkPad lên 16GB",
            "desc": "Máy thường xuyên báo đầy bộ nhớ khi mở nhiều file Excel lớn cùng lúc.",
            "cat": "hardware", "prio": "medium", "req": "user_linh", "status": "closed",
            "assignee": "agent_nam", "delta_hours_ago": 150,
            "rating": 5, "rating_cmt": "Máy chạy nhanh hơn hẳn, không còn giật lag.",
        },
        # --- ESCALATED (2) ---
        {
            "title": "Đứt cáp quang kết nối liên chi nhánh Hà Nội - Đà Nẵng",
            "desc": "Kênh truyền VPN Site-to-Site mất kết nối từ 11h trưa, chi nhánh Đà Nẵng không đồng bộ được dữ liệu.",
            "cat": "network", "prio": "urgent", "req": "user_tuan", "status": "escalated",
            "assignee": "agent_nam", "delta_hours_ago": 1,
            "comments": [
                ("agent_nam", "Đã kiểm tra đầu Router Cisco báo LOS (Loss of Signal). Chuyển cấp Giám đốc CNTT duyệt chuyển tuyến dự phòng 4G và làm việc với Viettel Telecom."),
            ],
        },
        {
            "title": "Nghi vấn máy trạm bị mã hóa tệp dữ liệu bởi ransomware qua email",
            "desc": "Nhận được email giả mạo thông báo thuế, lỡ mở file đính kèm thì các file Word trên Desktop bị đổi đuôi lạ.",
            "cat": "security", "prio": "urgent", "req": "user_mai", "status": "escalated",
            "assignee": "agent_hoa", "delta_hours_ago": 2,
            "comments": [
                ("agent_hoa", "Đã cô lập ngay máy trạm khỏi mạng nội bộ (rút dây mạng, disable Wi-Fi). Chuyển cấp Đội ứng cứu sự cố bảo mật điều tra mẫu mã độc."),
            ],
        },
        # --- MORE REALISTIC TICKETS (3) ---
        {
            "title": "Không xuất được báo cáo tổng hợp quý ra file Excel từ phần mềm ERP",
            "desc": "Khi nhấn nút 'Xuất Excel' hệ thống xoay vòng tròn và báo lỗi Timeout sau 30 giây.",
            "cat": "software", "prio": "medium", "req": "user_linh", "status": "new",
            "delta_hours_ago": 4,
        },
        {
            "title": "Máy scan HP ScanJet không đẩy được file PDF vào thư mục SMB",
            "desc": "Scan tài liệu xong màn hình máy báo lỗi 'Network path not found', không thấy file trong thư mục \\\\nas\\scans.",
            "cat": "hardware", "prio": "low", "req": "user_mai", "status": "in_progress",
            "assignee": "agent_nam", "delta_hours_ago": 7,
            "comments": [
                ("agent_nam", "Đang kiểm tra lại quyền NTLMv2 và user xác thực lưu trong máy scan."),
            ],
        },
        {
            "title": "Cấu hình VPN FortiClient Split-Tunneling để tối ưu băng thông",
            "desc": "Khi bật VPN thì việc xem video đào tạo nội bộ trên YouTube bị chậm do toàn bộ traffic đi qua công ty.",
            "cat": "network", "prio": "medium", "req": "user_tuan", "status": "resolved",
            "assignee": "agent_hoa", "delta_hours_ago": 30,
            "rating": 5, "rating_cmt": "Đã cấu hình split tunnel, giờ xem YouTube nhanh và vẫn truy cập server cty tốt.",
        },
    ]

    created_tickets = []
    for spec in tickets_specs:
        created_dt = base_time - timedelta(hours=spec["delta_hours_ago"])
        created_str = _iso(created_dt)
        prio_hours = store.PRIORITY_HOURS.get(spec["prio"], 24)
        sla_deadline = _iso(created_dt + timedelta(hours=prio_hours))

        # Insert directly to preserve timestamps
        with store._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO tickets
                    (title, description, category, priority, requester, assignee, status,
                     created_at, updated_at, sla_deadline, resolved_at, closed_at, rating, rating_comment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """ if store._database_url else """
                INSERT INTO tickets
                    (title, description, category, priority, requester, assignee, status,
                     created_at, updated_at, sla_deadline, resolved_at, closed_at, rating, rating_comment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    spec["title"],
                    spec["desc"],
                    spec["cat"],
                    spec["prio"],
                    spec["req"],
                    spec.get("assignee"),
                    spec["status"],
                    created_str,
                    created_str,
                    sla_deadline,
                    created_str if spec["status"] in ("resolved", "closed") else None,
                    created_str if spec["status"] == "closed" else None,
                    spec.get("rating"),
                    spec.get("rating_cmt"),
                ),
            )
            t_id = cur.fetchone()["id"] if store._database_url else cur.lastrowid
            created_tickets.append((t_id, spec))

            # Initial audit log
            conn.execute(
                """
                INSERT INTO audit_logs (ticket_id, actor, event, from_status, to_status, details, timestamp)
                VALUES (?, ?, 'created', NULL, 'new', 'Tạo ticket sự cố ban đầu', ?)
                """,
                (t_id, spec["req"], created_str),
            )

            # Assign audit log
            if spec.get("assignee"):
                conn.execute(
                    """
                    INSERT INTO audit_logs (ticket_id, actor, event, from_status, to_status, details, timestamp)
                    VALUES (?, 'admin', 'assigned', 'new', 'in_progress', ?, ?)
                    """,
                    (t_id, f"Phân công cho {spec['assignee']}", created_str),
                )

            # Comments
            for author, cmt_text in spec.get("comments", []):
                cmt_time = _iso(created_dt + timedelta(minutes=15))
                conn.execute(
                    """
                    INSERT INTO comments (ticket_id, author, comment, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (t_id, author, cmt_text, cmt_time),
                )
                conn.execute(
                    """
                    INSERT INTO audit_logs (ticket_id, actor, event, from_status, to_status, details, timestamp)
                    VALUES (?, ?, 'comment_added', ?, ?, 'Thêm bình luận trao đổi xử lý', ?)
                    """,
                    (t_id, author, spec["status"], spec["status"], cmt_time),
                )

    print(f"    [OK] Đã tạo thành công {len(created_tickets)} tickets mẫu.")

    # 3. Seed Sample Attachments
    print("\n[3/4] Tạo tệp đính kèm mẫu (Attachment Diagnostics)...")
    att_dir = Path(STORAGE_PATH).resolve() / "attachments"
    att_dir.mkdir(parents=True, exist_ok=True)

    sample_att_name = "network_diag_log.txt"
    sample_file_path = att_dir / sample_att_name
    sample_content = (
        "=== DIAGNOSTIC REPORT ===\n"
        "Timestamp: 2026-10-14 10:15:22 UTC\n"
        "Target Host: core-switch-01.opsmind.local (192.168.1.1)\n"
        "Ping statistics: 4 packets transmitted, 0 received, 100% packet loss\n"
        "Traceroute:\n"
        " 1  192.168.10.1 (gw-vlan10.opsmind.local)  1.23 ms\n"
        " 2  * * * Request timed out.\n"
        "Error: Interface GigabitEthernet0/24 changed state to down\n"
        "========================\n"
    )
    sample_file_path.write_text(sample_content, encoding="utf-8")

    # Attach to ticket 4 (network LAN outage)
    t4_id = created_tickets[3][0]
    with store._connect() as conn:
        conn.execute(
            """
            INSERT INTO ticket_attachments
                (id, ticket_id, original_name, stored_name, content_type, size_bytes, uploaded_by, created_at)
            VALUES (?, ?, 'network_diag_log.txt', ?, 'text/plain', ?, 'user_tuan', ?)
            """,
            (
                "att-sample-network-log",
                t4_id,
                sample_att_name,
                len(sample_content.encode("utf-8")),
                _iso(base_time - timedelta(hours=2)),
            ),
        )
    print(f"    [OK] Đã đính kèm tệp chẩn đoán vào Ticket #{t4_id}.")

    # 4. Seed RAG Chat History & Feedback
    print("\n[4/4] Khởi tạo lịch sử tra cứu RAG thực tế...")
    rag_sessions = [
        {
            "user": "user_linh",
            "q": "Máy in văn phòng báo offline hoặc paused thì làm sao in được?",
            "ans": (
                "Dựa theo quy trình trong tài liệu **Xử lý sự cố máy in báo Offline (printer_offline_status.md)**:\n\n"
                "1. **Khởi động lại Print Spooler**:\n"
                "   - Mở cửa sổ Run (`Win + R`), gõ `services.msc` và nhấn Enter.\n"
                "   - Tìm dịch vụ **Print Spooler**, click chuột phải chọn **Restart**.\n\n"
                "2. **Kiểm tra trạng thái Use Printer Offline**:\n"
                "   - Vào *Control Panel > Devices and Printers*.\n"
                "   - Click đúp vào máy in > chọn tab *Printer* > Bỏ tích chọn **Use Printer Offline**.\n\n"
                "3. **Kiểm tra kết nối mạng/cáp**:\n"
                "   - Ping thử đến địa chỉ IP máy in xem có phản hồi không.\n"
                "Nếu vẫn không in được, vui lòng bấm nút **'Tạo Ticket'** để kỹ thuật viên IT xuống kiểm tra trực tiếp."
            ),
            "sources": [{"title": "Xử lý sự cố máy in báo Offline", "source": "printer_offline_status.md"}],
            "feedback": "up",
        },
        {
            "user": "user_tuan",
            "q": "Không kết nối được VPN FortiClient báo lỗi credential hoặc timeout",
            "ans": (
                "Dựa theo tài liệu **Hướng dẫn xử lý lỗi VPN FortiClient (vpn_forticlient.md)**:\n\n"
                "1. Kiểm tra tài khoản AD không bị khóa (thử đăng nhập cổng thông tin nội bộ).\n"
                "2. Đảm bảo cổng kết nối SSL-VPN (mặc định 443 hoặc 10443) không bị chặn bởi mạng Wi-Fi công cộng.\n"
                "3. Reset card mạng ảo Fortinet Virtual Ethernet Adapter trong Device Manager."
            ),
            "sources": [{"title": "Hướng dẫn xử lý lỗi VPN FortiClient", "source": "vpn_forticlient.md"}],
            "feedback": "up",
        },
    ]

    for s in rag_sessions:
        sid = store.save_chat_exchange(
            username=s["user"],
            session_id=None,
            question=s["q"],
            answer=s["ans"],
            sources=s["sources"],
        )
        chat = store.get_chat_session(s["user"], sid)
        if chat and len(chat["messages"]) > 1:
            msg_id = chat["messages"][1]["id"]
            store.set_chat_feedback(s["user"], msg_id, s["feedback"])
        print(f"    + RAG Session [{s['user']}]: '{s['q'][:45]}...' (👍 Upvoted)")

    print("\n" + "=" * 65)
    print("  HOÀN TẤT SEED DỮ LIỆU DEMO BẢO VỆ ĐỒ ÁN!")
    print("=" * 65)
    print("\nDanh sách tài khoản demo:")
    print("  - Quản trị viên (Admin)   : admin     / OpsMindAdmin2026!")
    print("  - Kỹ thuật viên (IT Net)  : agent_nam / AgentPass2026!")
    print("  - Kỹ thuật viên (IT App)  : agent_hoa / AgentPass2026!")
    print("  - Nhân viên (Kế toán)     : user_linh / UserPass2026!")
    print("  - Nhân viên (Kinh doanh)  : user_tuan / UserPass2026!")
    print("  - Nhân viên (Nhân sự)     : user_mai  / UserPass2026!")
    print("\nTổng quan số liệu hiện có:")
    analytics = store.get_analytics()
    statuses = analytics["status_breakdown"]
    print(f"  - Tổng số ticket : {analytics['total_tickets']} tickets")
    print(f"    * Mới tiếp nhận (new)         : {statuses.get('new', 0)}")
    print(f"    * Đang xử lý (in_progress)    : {statuses.get('in_progress', 0)}")
    print(f"    * Chờ người dùng (waiting)    : {statuses.get('pending_waiting_user', 0)}")
    print(f"    * Đã giải quyết (resolved)    : {statuses.get('resolved', 0)}")
    print(f"    * Đã đóng (closed)            : {statuses.get('closed', 0)}")
    print(f"    * Chuyển cấp (escalated)      : {statuses.get('escalated', 0)}")
    print(f"  - Điểm hài lòng CSAT : {analytics['average_rating']} / 5 sao ⭐")
    return 0


if __name__ == "__main__":
    sys.exit(main())
