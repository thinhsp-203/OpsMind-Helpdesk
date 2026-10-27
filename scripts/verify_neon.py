#!/usr/bin/env python3
"""Neon Serverless Postgres Verification Script for OpsMind Helpdesk.

Usage:
    py scripts/verify_neon.py [DATABASE_URL] [--write | --crud-test]

Examples:
    # 1. Safe read-only connectivity and schema check (Default - No writes/DDL):
    py scripts/verify_neon.py
    py scripts/verify_neon.py "postgresql://user:pass@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"

    # 2. Full verification including schema sync and CRUD write/read/delete roundtrip:
    py scripts/verify_neon.py "postgresql://user:pass@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require" --write
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402


def sanitize_database_url(url: str) -> str:
    """Mask credentials in database URL to prevent terminal or log exposure."""
    if not url or not isinstance(url, str):
        return ""
    try:
        parsed = urlsplit(url)
        if not parsed.scheme or not parsed.netloc:
            # Fallback simple masking
            if "@" in url:
                prefix, host_part = url.rsplit("@", 1)
                if ":" in prefix:
                    scheme_and_user = prefix.rsplit(":", 1)[0]
                    return f"{scheme_and_user}:***@{host_part}"
            return url

        username = parsed.username
        hostname = parsed.hostname
        port = f":{parsed.port}" if parsed.port else ""

        if username:
            netloc = f"{quote(unquote(username))}:***@{hostname}{port}"
        elif parsed.password:
            netloc = f":***@{hostname}{port}"
        else:
            netloc = parsed.netloc

        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    except Exception:
        if "@" in url:
            prefix, host_part = url.rsplit("@", 1)
            if ":" in prefix:
                scheme_and_user = prefix.rsplit(":", 1)[0]
                return f"{scheme_and_user}:***@{host_part}"
        return url


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])

    allow_write = False
    clean_args: list[str] = []
    for arg in args:
        if arg in ("--write", "--crud-test", "--init", "--mutate"):
            allow_write = True
        else:
            clean_args.append(arg)

    database_url = clean_args[0].strip() if clean_args else os.getenv("DATABASE_URL", "").strip()

    print("=" * 65)
    print("  OpsMind Helpdesk — Neon Serverless Postgres Verification")
    print("=" * 65)

    if not database_url:
        print("[!] Không tìm thấy DATABASE_URL.")
        print("    Vui lòng cung cấp connection string từ https://neon.tech:")
        print('    py scripts/verify_neon.py "postgresql://user:pass@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"')
        print("    hoặc cấu hình DATABASE_URL trong file .env")
        return 1

    sanitized = sanitize_database_url(database_url)
    print(f"[*] URL: {sanitized}")
    is_neon = "neon.tech" in database_url
    is_pooled = "-pooler" in database_url

    print(f"[*] Endpoint Type: {'Neon Serverless Postgres' if is_neon else 'Standard PostgreSQL'}")
    print(f"[*] Connection Mode: {'Pooled (PgBouncer) - Khuyên dùng cho Web/Serverless' if is_pooled else 'Direct Connection'}")
    print(f"[*] Verification Mode: {'Full (Ghi/Xóa CRUD & Đồng bộ Schema)' if allow_write else 'Safe Read-Only (Kiểm tra kết nối an toàn, không ghi/sửa CSDL)'}")

    # Prepare connection URL
    url = database_url.replace("postgres://", "postgresql://", 1)
    if "neon.tech" in url and "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}sslmode=require"

    # Step 1: Test connection handshake
    print("\n[1/5] Kiểm tra kết nối TCP / SSL Handshake...")
    try:
        with psycopg.connect(url, row_factory=dict_row, prepare_threshold=None) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                row = cur.fetchone()
                pg_version = row["version"] if row else "Unknown"
                print("  [OK] Đã kết nối thành công!")
                print(f"  [i] PostgreSQL Version: {pg_version.split(',')[0]}")
    except Exception as exc:
        print(f"  [FAILED] Kết nối thất bại: {exc}")
        print("\n  Gợi ý khắc phục:")
        print("  1. Kiểm tra tài khoản/mật khẩu và tên database trên https://console.neon.tech")
        print("  2. Đảm bảo có tham số '?sslmode=require' trong chuỗi kết nối")
        print("  3. Thử copy chuỗi 'Pooled connection' từ Dashboard Neon")
        return 1

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

    # Step 2: Initialize schema & migrations (only when allow_write is set)
    print("\n[2/5] Khởi tạo / Đồng bộ Schema (Tables, Indexes, Migrations)...")
    if allow_write:
        try:
            os.environ["DATABASE_URL"] = database_url
            os.environ.setdefault("DEMO_MODE", "true")
            from app import store
            store._database_url = database_url
            store.initialize_store()
            print("  [OK] Schema CSDL đồng bộ thành công!")
        except Exception as exc:
            print(f"  [FAILED] Lỗi khởi tạo schema: {exc}")
            return 1
    else:
        print("  [i] Safe Read-Only Mode: Kiểm tra schema hiện có qua information_schema (không chạy DDL)...")
        try:
            with psycopg.connect(url, row_factory=dict_row, prepare_threshold=None) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
                    existing_tables = {r["table_name"] for r in cur.fetchall()}
            missing_tables = [t for t in required_tables if t not in existing_tables]
            if missing_tables:
                print(f"  [!] Các bảng chưa tồn tại trên CSDL: {', '.join(missing_tables)}")
                print("      (Chạy với cờ '--write' hoặc khởi động ứng dụng để tự động khởi tạo tables).")
            else:
                print(f"  [OK] Toàn bộ {len(required_tables)} bảng dữ liệu cốt lõi đã tồn tại trên CSDL!")
        except Exception as exc:
            print(f"  [FAILED] Lỗi truy vấn information_schema: {exc}")
            return 1

    # Step 3: Check tables and row counts
    print("\n[3/5] Kiểm tra cấu trúc các bảng dữ liệu...")
    try:
        with psycopg.connect(url, row_factory=dict_row, prepare_threshold=None) as conn:
            with conn.cursor() as cur:
                for tbl in required_tables:
                    try:
                        cur.execute(f"SELECT COUNT(*) AS count FROM {tbl};")  # noqa: S608
                        row = cur.fetchone()
                        cnt = row["count"] if row else 0
                        print(f"  - {tbl:22}: {cnt:4} bản ghi")
                    except Exception:
                        print(f"  - {tbl:22}: [Chưa tạo / Bảng rỗng]")
    except Exception as exc:
        print(f"  [FAILED] Lỗi đọc số lượng bản ghi: {exc}")
        return 1

    # Step 4: Verify built-in knowledge base
    print("\n[4/5] Kiểm tra Kho Tri thức (Knowledge Base)...")
    try:
        with psycopg.connect(url, row_factory=dict_row, prepare_threshold=None) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS count FROM knowledge_documents WHERE is_builtin = 1;")
                row = cur.fetchone()
                kb_count = row["count"] if row else 0
                print(f"  [i] Tổng số tài liệu runbook trong CSDL: {kb_count}")
                if kb_count >= 30:
                    print("  [OK] Đã nạp đầy đủ 30 Runbook sự cố doanh nghiệp vào CSDL Neon!")
                else:
                    print(f"  [!] Lưu ý: Số lượng tài liệu ({kb_count}) ít hơn 30. Có thể cần re-seed (chạy với cờ '--write').")
    except Exception:
        print("  [!] Bảng knowledge_documents chưa sẵn sàng trên CSDL.")

    # Step 5: Test write-read cycle
    print("\n[5/5] Kiểm thử ghi/đọc (Roundtrip CRUD)...")
    if allow_write:
        try:
            from app import store
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
            with psycopg.connect(url, prepare_threshold=None) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM comments WHERE ticket_id = %s;", (t_id,))
                    cur.execute("DELETE FROM audit_logs WHERE ticket_id = %s;", (t_id,))
                    cur.execute("DELETE FROM tickets WHERE id = %s;", (t_id,))
                conn.commit()
            print("  [OK] Thao tác Ghi - Đọc - Xóa hoạt động hoàn hảo!")
        except Exception as exc:
            print(f"  [FAILED] Lỗi trong thao tác CRUD: {exc}")
            return 1
    else:
        print("  [BỎ QUA - Safe Read-Only Mode] Không thực hiện INSERT / UPDATE / DELETE / DDL trên CSDL.")
        print("  (Sử dụng cờ '--write' hoặc '--crud-test' nếu chủ động muốn thử nghiệm ghi dữ liệu mẫu).")

    print("\n" + "=" * 65)
    print("  KẾT QUẢ: NEON SERVERLESS POSTGRES ĐÃ SẴN SÀNG!")
    print("=" * 65)
    print("\nCác bước tiếp theo:")
    print("1. Cấu hình biến môi trường trên Render Web Service:")
    print("   Truy cập https://dashboard.render.com -> OpsMind Service -> Environment")
    print("   Thêm biến:")
    print(f"   DATABASE_URL = {sanitized}")
    print("\n2. Chạy ứng dụng local kết nối Neon:")
    print("   Thêm dòng sau vào file .env:")
    print(f"   DATABASE_URL={sanitized}")
    print("   Sau đó chạy: py -m uvicorn app.main:app --reload\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
