#!/usr/bin/env python3
"""Neon Serverless Postgres Verification Script for OpsMind Helpdesk.

Usage:
    py scripts/verify_neon.py [DATABASE_URL]

Examples:
    py scripts/verify_neon.py
    py scripts/verify_neon.py "postgresql://user:pass@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Check command line arguments and environment before importing app modules
if len(sys.argv) > 1 and sys.argv[1].strip():
    os.environ["DATABASE_URL"] = sys.argv[1].strip()

# Default to demo_mode=true for verification script to avoid demo credential clash on local runs
os.environ.setdefault("DEMO_MODE", "true")

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from app import store  # noqa: E402


def main() -> int:
    database_url = sys.argv[1].strip() if len(sys.argv) > 1 else os.getenv("DATABASE_URL", "").strip()

    print("=" * 65)
    print("  OpsMind Helpdesk — Neon Serverless Postgres Verification")
    print("=" * 65)

    if not database_url:
        print("[!] Không tìm thấy DATABASE_URL.")
        print("    Vui lòng cung cấp connection string từ https://neon.tech:")
        print('    py scripts/verify_neon.py "postgresql://user:pass@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"')
        print("    hoặc cấu hình DATABASE_URL trong file .env")
        return 1

    # Sanitize URL for display
    sanitized = database_url
    if "@" in sanitized:
        prefix, host_part = sanitized.split("@", 1)
        scheme_user = prefix.split(":", 2)
        if len(scheme_user) >= 3:
            sanitized = f"{scheme_user[0]}:{scheme_user[1]}:***@{host_part}"

    print(f"[*] URL: {sanitized}")
    is_neon = "neon.tech" in database_url
    is_pooled = "-pooler" in database_url

    print(f"[*] Endpoint Type: {'Neon Serverless Postgres' if is_neon else 'Standard PostgreSQL'}")
    print(f"[*] Connection Mode: {'Pooled (PgBouncer) - Khuyên dùng cho Web/Serverless' if is_pooled else 'Direct Connection'}")

    # Set store database url
    store._database_url = database_url

    # Step 1: Test connection handshake
    print("\n[1/5] Kiểm tra kết nối TCP / SSL Handshake...")
    try:
        url = database_url.replace("postgres://", "postgresql://", 1)
        if "neon.tech" in url and "sslmode=" not in url:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}sslmode=require"
        with psycopg.connect(url, row_factory=dict_row, prepare_threshold=None) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                pg_version = cur.fetchone()["version"]
                print("  [OK] Đã kết nối thành công!")
                print(f"  [i] PostgreSQL Version: {pg_version.split(',')[0]}")
    except Exception as exc:
        print(f"  [FAILED] Kết nối thất bại: {exc}")
        print("\n  Gợi ý khắc phục:")
        print("  1. Kiểm tra tài khoản/mật khẩu và tên database trên https://console.neon.tech")
        print("  2. Đảm bảo có tham số '?sslmode=require' trong chuỗi kết nối")
        print("  3. Thử copy chuỗi 'Pooled connection' từ Dashboard Neon")
        return 1

    # Step 2: Initialize schema & migrations
    print("\n[2/5] Khởi tạo / Đồng bộ Schema (Tables, Indexes, Migrations)...")
    try:
        store.initialize_store()
        print("  [OK] Schema CSDL đồng bộ thành công!")
    except Exception as exc:
        print(f"  [FAILED] Lỗi khởi tạo schema: {exc}")
        return 1

    # Step 3: Check tables and row counts
    print("\n[3/5] Kiểm tra cấu trúc các bảng dữ liệu...")
    required_tables = [
        "users",
        "tickets",
        "comments",
        "audit_logs",
        "ticket_attachments",
        "chat_sessions",
        "chat_messages",
        "knowledge_documents",
        "knowledge_versions",
    ]
    with store._connect() as conn:
        for tbl in required_tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) AS count FROM {tbl}").fetchone()  # noqa: S608
                cnt = row["count"] if row else 0
                print(f"  - {tbl:22}: {cnt:4} bản ghi")
            except Exception as exc:
                print(f"  - {tbl:22}: [LỖI] {exc}")
                return 1

    # Step 4: Verify built-in knowledge base
    print("\n[4/5] Kiểm tra Kho Tri thức (Knowledge Base)...")
    kb_docs = store.list_knowledge_documents()
    print(f"  [i] Tổng số tài liệu runbook trong CSDL: {len(kb_docs)}")
    if len(kb_docs) >= 30:
        print("  [OK] Đã nạp đầy đủ 30 Runbook sự cố doanh nghiệp vào CSDL Neon!")
    else:
        print(f"  [!] Lưu ý: Số lượng tài liệu ({len(kb_docs)}) ít hơn 30. Có thể cần re-seed.")

    # Step 5: Test write-read cycle
    print("\n[5/5] Kiểm thử ghi/đọc (Roundtrip CRUD)...")
    try:
        users = store.list_users()
        active_user = users[0]["username"] if users else "admin"
        test_ticket = store.create_ticket(
            title="[Neon Verification Test] Auto Check",
            description="Testing write operations on Neon Serverless Postgres.",
            category="software",
            priority="low",
            requester=active_user,
        )
        t_id = test_ticket["id"]
        store.add_comment(t_id, active_user, "Neon Postgres CRUD roundtrip verified.")
        fetched = store.get_ticket(t_id)
        if not (fetched and fetched["id"] == t_id):
            raise RuntimeError("Không thể đọc lại ticket vừa tạo trên Neon.")
        # Clean up test ticket
        with store._connect() as conn:
            conn.execute("DELETE FROM comments WHERE ticket_id = ?", (t_id,))
            conn.execute("DELETE FROM audit_logs WHERE ticket_id = ?", (t_id,))
            conn.execute("DELETE FROM tickets WHERE id = ?", (t_id,))
        print("  [OK] Thao tác Ghi - Đọc - Xóa hoạt động hoàn hảo!")
    except Exception as exc:
        print(f"  [FAILED] Lỗi trong thao tác CRUD: {exc}")
        return 1

    print("\n" + "=" * 65)
    print("  KẾT QUẢ: NEON SERVERLESS POSTGRES ĐÃ SẴN SÀNG!")
    print("=" * 65)
    print("\nCác bước tiếp theo:")
    print("1. Cấu hình biến môi trường trên Render Web Service:")
    print("   Truy cập https://dashboard.render.com -> OpsMind Service -> Environment")
    print("   Thêm biến:")
    print(f"   DATABASE_URL = {database_url}")
    print("\n2. Chạy ứng dụng local kết nối Neon:")
    print("   Thêm dòng sau vào file .env:")
    print(f"   DATABASE_URL={database_url}")
    print("   Sau đó chạy: py -m uvicorn app.main:app --reload\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
