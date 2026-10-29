from __future__ import annotations

import json
import logging
import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from app import config

logger = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[a-z0-9]+")
BASE_KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"
STORAGE_KNOWLEDGE_DIR = Path(config.STORAGE_PATH).resolve() / "knowledge"
KNOWLEDGE_DIR = BASE_KNOWLEDGE_DIR
DICTIONARY_PATH = Path(__file__).resolve().parent.parent / "data" / "rag_dictionary.json"

DEFAULT_STOP_WORDS = {
    "a", "an", "and", "are", "bao", "biet", "bi", "bị", "but", "cach", "can",
    "cannot", "cant", "cho", "co", "cua", "dang", "de", "did", "du", "duoc",
    "gio", "giup", "ha", "hay", "how", "i", "in", "initiate", "is", "it", "la",
    "lam", "loi", "mai", "mot", "mua", "my", "nao", "ngay", "nha", "noi", "not",
    "of", "on", "received", "repeated", "sao", "several", "tai", "team", "the",
    "tho", "thoi", "thu", "tiet", "to", "toi", "va", "ve", "viec", "viet", "voi",
    "what", "when", "where", "why", "with", "work", "works", "you",
}
DEFAULT_SYNONYMS = {
    "wifi": "wifi",
    "wireless": "wifi",
    "internet": "internet",
    "lan": "lan",
    "dns": "dns",
    "dhcp": "dhcp",
    "ethernet": "ethernet",
    "vpn": "vpn",
    "forticlient": "forticlient",
    "openvpn": "openvpn",
    "printer": "printer",
    "printing": "printer",
    "spooler": "printer",
    "scanner": "scanner",
    "scan": "scanner",
    "outlook": "outlook",
    "mail": "email",
    "email": "email",
    "autodiscover": "autodiscover",
    "chungthu": "certificate",
    "certificate": "certificate",
    "folder": "access",
    "permission": "access",
    "quyen": "access",
    "smb": "smb",
    "offline": "offline",
    "status": "status",
    "quota": "quota",
    "sync": "sync",
    "driver": "driver",
    "erp": "erp",
    "accounting": "erp",
    "update": "update",
    "patch": "update",
    "patching": "update",
    "windows": "windows",
    "mfa": "mfa",
    "authenticator": "mfa",
}
DEFAULT_COMPOUNDS = {
    ("may", "in"): "printer",
    ("chung", "thu", "so"): "certificate",
    ("chung", "thu"): "certificate",
    ("chu", "ky", "so"): "certificate",
    ("ky", "so"): "certificate",
    ("thu", "muc"): "access",
    ("login", "approval", "request"): "mfa",
    ("login", "approval"): "mfa",
    ("phe", "duyet"): "approval",
    ("quet", "tai", "lieu"): "scanner",
    ("may", "da", "chuc", "nang"): "scanner",
    ("may", "scan"): "scanner",
    ("may", "quet"): "scanner",
    ("scan", "to", "folder"): "scanner",
    ("cau", "hinh", "tu", "dong"): "autodiscover",
    ("them", "tai", "khoan"): "autodiscover",
    ("hop", "thu"): "email",
    ("hom", "thu"): "email",
    ("han", "ngach"): "quota",
    ("dung", "luong"): "quota",
    ("vuot", "qua"): "quota",
    ("khong", "cap", "nhat"): "sync",
    ("khong", "dong", "bo"): "sync",
    ("dong", "bo"): "sync",
    ("xung", "dot"): "conflict",
    ("trung", "ip"): "conflict",
    ("dia", "chi", "ip"): "ip",
    ("cai", "dat", "driver"): "driver",
    ("trang", "thai"): "status",
    ("bat", "nguon"): "power",
    ("binh", "thuong"): "",
    ("van", "phong"): "",
}
DEFAULT_CATEGORY_BY_SOURCE = {
    "ad_account_lockout.md": "security",
    "bitlocker_recovery_key.md": "security",
    "certificate_signature.md": "security",
    "dns_dhcp_conflict.md": "network",
    "email_send_receive_error.md": "software",
    "erp_accounting.md": "software",
    "ethernet_cable_disconnect.md": "network",
    "folder_access.md": "security",
    "high_cpu_ram_disk.md": "software",
    "mfa_account.md": "security",
    "openvpn_client_error.md": "network",
    "outlook_autodiscover_failed.md": "software",
    "outlook_email.md": "software",
    "outlook_mailbox_quota.md": "software",
    "outlook_ost_corruption.md": "software",
    "printer_driver_install.md": "hardware",
    "printer_offline_status.md": "hardware",
    "printer_queue.md": "hardware",
    "proxy_pac_bypass.md": "network",
    "remote_desktop_rdp.md": "software",
    "scanner_smb_folder.md": "hardware",
    "shared_folder_permission.md": "security",
    "slow_network_latency.md": "network",
    "usb_peripheral_not_recognized.md": "hardware",
    "vpn_forticlient.md": "network",
    "vpn_split_tunnel.md": "network",
    "wifi_network.md": "network",
    "windows_bsod_crash.md": "software",
    "windows_license_activation.md": "software",
    "windows_update.md": "software",
}
DEFAULT_URGENT_MARKERS = (
    "toan cong ty",
    "ca phong",
    "nhieu nguoi",
    "ma doc",
    "ransomware",
    "bi tan cong",
    "ro ri du lieu",
    "gateway down",
)
DEFAULT_HIGH_PRIORITY_MARKERS = (
    "khong the lam viec",
    "khong vao duoc",
    "khong the dang nhap",
    "mat ket noi",
    "loi xac thuc",
    "chung thu het han",
)
DEFAULT_OUT_OF_SCOPE_PATTERNS = (
    "thoi tiet",
    "bai tho",
    "lam tho",
    "nau an",
    "bong da",
    "chuyen xe",
    "gia vang",
    "ty gia",
    "phim anh",
    "du lich",
    "may giat",
    "xe may",
    "o to",
    "xe hoi",
    "tu lanh",
    "dieu hoa",
    "bep gas",
    "bep tu",
    "noi com",
    "may say",
    "may loc nuoc",
    "binh nong lanh",
    "ngu duoc",
    "mat ngu",
    "suc khoe",
    "uong thuoc",
    "benh vien",
    "kham benh",
    "lan ho diep",
    "cay canh",
    "trong cay",
    "thu cung",
    "cho meo",
    "tai khoan ngan hang",
    "so tiet kiem",
    "the tin dung",
    "the atm",
    "facebook ca nhan",
    "tiktok",
    "instagram",
    "bat dong san",
    "vneid",
    "dinh danh dien tu",
    "ngay ram",
    "cam hoa",
    "ban tho",
    "tap gym",
    "giam mo",
    "hoa hong",
    "chuyen nhuong",
)


def load_rag_dictionary(dict_file: Path | None = None) -> tuple[
    set[str],
    dict[str, str],
    dict[tuple[str, ...], str],
    dict[str, str],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    target = dict_file or DICTIONARY_PATH
    if target.is_file():
        try:
            with target.open(encoding="utf-8") as f:
                raw = json.load(f)
            stop_words = set(raw.get("stop_words", [])) or DEFAULT_STOP_WORDS
            synonyms = raw.get("synonyms", {}) or DEFAULT_SYNONYMS

            compounds_raw = raw.get("compounds", {})
            if isinstance(compounds_raw, dict):
                compounds = {
                    tuple(k.split()): v for k, v in compounds_raw.items()
                }
            else:
                compounds = DEFAULT_COMPOUNDS

            category_by_source = raw.get("category_by_source", {}) or DEFAULT_CATEGORY_BY_SOURCE
            urgent_markers = tuple(raw.get("urgent_markers", [])) or DEFAULT_URGENT_MARKERS
            high_priority_markers = tuple(raw.get("high_priority_markers", [])) or DEFAULT_HIGH_PRIORITY_MARKERS
            out_of_scope_patterns = tuple(raw.get("out_of_scope_patterns", [])) or DEFAULT_OUT_OF_SCOPE_PATTERNS
            return (
                stop_words,
                synonyms,
                compounds,
                category_by_source,
                urgent_markers,
                high_priority_markers,
                out_of_scope_patterns,
            )
        except Exception as exc:
            logger.warning("Failed to load RAG dictionary from %s, using defaults: %s", target, exc)

    return (
        DEFAULT_STOP_WORDS,
        DEFAULT_SYNONYMS,
        DEFAULT_COMPOUNDS,
        DEFAULT_CATEGORY_BY_SOURCE,
        DEFAULT_URGENT_MARKERS,
        DEFAULT_HIGH_PRIORITY_MARKERS,
        DEFAULT_OUT_OF_SCOPE_PATTERNS,
    )


(
    STOP_WORDS,
    SYNONYMS,
    COMPOUNDS,
    CATEGORY_BY_SOURCE,
    URGENT_MARKERS,
    HIGH_PRIORITY_MARKERS,
    OUT_OF_SCOPE_PATTERNS,
) = load_rag_dictionary()

MIN_RELEVANCE = 0.12


def reload_rag_dictionary(dict_file: Path | None = None) -> None:
    global STOP_WORDS, SYNONYMS, COMPOUNDS, CATEGORY_BY_SOURCE, URGENT_MARKERS, HIGH_PRIORITY_MARKERS, OUT_OF_SCOPE_PATTERNS
    (
        STOP_WORDS,
        SYNONYMS,
        COMPOUNDS,
        CATEGORY_BY_SOURCE,
        URGENT_MARKERS,
        HIGH_PRIORITY_MARKERS,
        OUT_OF_SCOPE_PATTERNS,
    ) = load_rag_dictionary(dict_file)
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()


IT_DOMAIN_WORDS: set[str] = {
    "windows", "macos", "linux", "office", "word", "excel", "outlook", "email", "mail",
    "erp", "misa", "sap", "fast", "bravo", "chrome", "edge", "firefox",
    "vpn", "forticlient", "openvpn", "wifi", "wireless", "internet", "ip", "dhcp", "dns",
    "proxy", "pac", "ping", "router", "switch", "gateway", "server", "pc", "laptop",
    "printer", "scanner", "scan", "usb", "ram", "cpu", "ssd", "bios", "driver",
    "mfa", "otp", "authenticator", "bitlocker", "smb", "rdp", "login", "password", "auth",
    "account", "apps", "app", "approval", "certificate", "signature", "quota", "share",
    "bsod", "spooler", "helpdesk", "ticket",
    "access", "permission", "permissions", "remote", "network", "print", "printing",
    "queue", "crash", "reboot", "restart", "connect", "connection", "folder", "file",
    "ethernet", "ipconfig", "flushdns",
}

IT_DOMAIN_PHRASES: tuple[str, ...] = (
    "wi-fi", "wi fi", "may tinh", "may chu", "may in", "man hinh", "chuot", "ban phim", "o dia", "o cung",
    "day mang", "cap mang", "cong mang", "mang lan", "cong lan", "mang noi bo", "duong truyen", "mat mang", "cham mang", "rot mang",
    "mat wifi", "song wifi", "mang wifi", "ket noi wifi",
    "phan mem", "ung dung", "ban quyen", "kich hoat",
    "tai khoan", "mat khau", "dang nhap", "khoa tai khoan", "mo khoa tai khoan", "doi mat khau", "quen mat khau", "reset mat khau",
    "chung thu", "chu ky", "ky so", "quyen truy cap", "truy cap", "thu muc", "chia se file",
    "login approval", "approval request",
    "man hinh xanh", "treo may", "do may", "ket lenh", "lenh in", "ket giay", "het muc", "in an",
    "khong nhan usb", "khong in duoc", "khong gui duoc mail", "khong nhan duoc mail",
    "khong vao duoc mang", "khong vao duoc vpn", "khong ket noi duoc vpn",
)


def is_out_of_scope(query: str) -> bool:
    folded = _fold_text(query)
    words = set(TOKEN_RE.findall(folded))
    has_it = bool(words & IT_DOMAIN_WORDS) or any(phrase in folded for phrase in IT_DOMAIN_PHRASES)
    has_oos = any(pattern in folded for pattern in OUT_OF_SCOPE_PATTERNS)
    if has_oos:
        strong_it_terms = {"misa", "sap", "erp", "vpn", "bitlocker", "bsod", "outlook", "excel", "word", "printer"}
        strong_it_phrases = ("wi-fi", "wi fi", "wifi", "may tinh", "may in", "cap mang", "day mang", "phan mem ke toan", "thu muc chia se")
        strong_it = bool(words & strong_it_terms) or any(p in folded for p in strong_it_phrases) or (len(words & IT_DOMAIN_WORDS) >= 2)
        if not strong_it:
            return True
        return False
    if not has_it:
        return True
    return False


def _normalize_title(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title()


def contextualize_question(question: str, messages: list[dict[str, Any]]) -> str:
    """Resolve short follow-ups from bounded user text, never assistant claims.

    This is a conservative rule, not unrestricted conversational memory. Explicit
    new IT topics and out-of-scope requests must not inherit the previous topic.
    """
    folded = _fold_text(question)
    followup = re.match(
        r"^(?:van (?:khong|chua)|toi da (?:thu|lam)|da (?:thu|lam)|buoc (?:do|nay)|"
        r"lam (?:roi|theo)|khong duoc|chua duoc|it still|still (?:not|doesn)|"
        r"i (?:tried|did)|that (?:step|didn))\b", folded,
    )
    if (len(question) > 300 or not followup or not is_out_of_scope(question)
            or any(pattern in folded for pattern in OUT_OF_SCOPE_PATTERNS)):
        return question
    for message in reversed(messages[-6:]):
        previous = str(message.get("content", ""))
        if message.get("role") == "user" and not is_out_of_scope(previous):
            return f"Sự cố người dùng đã mô tả: {previous[:2000]}\nCập nhật hiện tại: {question}"
    return question


def _fold_text(text: str) -> str:
    folded = unicodedata.normalize("NFD", text.lower())
    folded = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    return folded.replace("đ", "d")


def _tokens(text: str) -> list[str]:
    words = TOKEN_RE.findall(_fold_text(text))
    sorted_compounds = sorted(COMPOUNDS.items(), key=lambda item: len(item[0]), reverse=True)
    normalized = []
    index = 0
    while index < len(words):
        matched = False
        for parts, canonical in sorted_compounds:
            p_len = len(parts)
            if index + p_len <= len(words) and tuple(words[index:index + p_len]) == parts:
                if canonical:
                    normalized.append(canonical)
                index += p_len
                matched = True
                break
        if matched:
            continue
        word = words[index]
        index += 1
        if word in STOP_WORDS:
            continue
        canonical = SYNONYMS.get(word, word)
        if canonical:
            normalized.append(canonical)
    return normalized


class KnowledgeBaseUnavailableError(RuntimeError):
    """The authoritative publication store could not be read."""


def load_knowledge_base() -> list[dict[str, Any]]:
    if KNOWLEDGE_DIR.resolve() == BASE_KNOWLEDGE_DIR.resolve():
        try:
            from app import store
            db_docs = store.list_knowledge_documents(status="published")
        except Exception as exc:
            logger.warning("Could not read published knowledge documents from the store")
            # Exceptions are not cached: a recovered store can be retried immediately.
            raise KnowledgeBaseUnavailableError("Knowledge Base unavailable") from exc
        # An empty published set is authoritative, not a reason to revive files.
        return [
            {
                "title": doc["title"],
                "source": doc["slug"],
                "content": doc["content"],
                "category": doc["category"],
                "tags": doc["tags"],
                "is_builtin": bool(doc["is_builtin"]),
                "id": doc["id"],
            }
            for doc in sorted(db_docs, key=lambda d: d["slug"])
        ]

    # Explicit directory overrides support isolated filesystem fixtures; never failover here.
    docs_by_source: dict[str, dict[str, Any]] = {}
    if KNOWLEDGE_DIR.is_dir():
        for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            heading = re.search(r"(?m)^#\s+(.+?)\s*$", content)
            docs_by_source[path.name] = {
                "title": heading.group(1) if heading else _normalize_title(path),
                "source": path.name,
                "content": content,
                "category": CATEGORY_BY_SOURCE.get(path.name, "general"),
                "tags": f"{CATEGORY_BY_SOURCE.get(path.name, 'general')}, runbook",
                "is_builtin": False,
            }
    return sorted(docs_by_source.values(), key=lambda d: d["source"])


def save_knowledge_document(
    original_name: str,
    title: str,
    content: str,
    *,
    author: str,
) -> dict[str, Any]:
    """Import Markdown into the same DB transaction/version history as the editor.

    Packaged runbooks are read-only seed input. No mutable file copy is created.
    """
    from app import store

    normalized = unicodedata.normalize("NFKD", Path(original_name).stem.lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = normalized.replace("đ", "d")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")[:64]
    if not slug:
        raise ValueError("Document filename does not contain a usable name.")
    if not title.strip():
        raise ValueError("Document title is required.")
    source = f"{slug}.md"
    if (BASE_KNOWLEDGE_DIR / source).is_file():
        raise FileExistsError(source)
    try:
        document = store.create_knowledge_document(
            title=title.strip(),
            category=CATEGORY_BY_SOURCE.get(source, "general"),
            content=content.strip(),
            custom_slug=source,
            status="published",
            author=author,
            is_builtin=0,
        )
    except store.DatabaseIntegrityError as exc:
        # The unique slug constraint arbitrates concurrent uploads. Do not turn
        # unrelated constraint/version-write failures into a duplicate response.
        if store.get_knowledge_document(source) is not None:
            raise FileExistsError(source) from exc
        raise
    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    return {**document, "source": source}


def chunk_markdown(text: str, chunk_size: int = 650) -> list[str]:
    normalized = re.sub(r"\n{3,}", "\n\n", text).strip()
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", normalized) if part.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for paragraph in paragraphs:
        if current and current_length + len(paragraph) > chunk_size:
            chunks.append("\n\n".join(current))
            current = [current[-1], paragraph] if len(current[-1]) < 180 else [paragraph]
            current_length = sum(len(part) for part in current)
        else:
            current.append(paragraph)
            current_length += len(paragraph)
    if current:
        chunks.append("\n\n".join(current))
    return chunks or ([normalized] if normalized else [])


@lru_cache(maxsize=1)
def _cached_retrieval_index(
    snapshot: tuple[tuple[str, str, str, str, str], ...],
) -> list[dict[str, Any]]:
    passages: list[dict[str, Any]] = []
    for title, source, category, tags, content in snapshot:
        for chunk in chunk_markdown(content):
            words = _tokens(f"{title} {chunk}")
            passages.append(
                {
                    "title": title,
                    "source": source,
                    "category": category,
                    "tags": tags,
                    "content": chunk,
                    "tokens": words,
                }
            )
    return passages


def build_retrieval_index() -> list[dict[str, Any]]:
    # Read publication state on every lookup, including when a local index is warm.
    # Immutable content keys let workers observe commits without shared cache invalidation.
    snapshot = tuple(
        (
            document["title"], document["source"],
            document.get("category", CATEGORY_BY_SOURCE.get(document["source"], "general")),
            document.get("tags", ""), document["content"],
        )
        for document in load_knowledge_base()
    )
    return _cached_retrieval_index(snapshot)


def clear_retrieval_cache() -> None:
    _cached_retrieval_index.cache_clear()


# Preserve existing internal invalidation hooks; DB documents themselves are never cached.
load_knowledge_base.cache_clear = clear_retrieval_cache
build_retrieval_index.cache_clear = clear_retrieval_cache


def retrieve_relevant_context(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    if is_out_of_scope(query):
        return []
    passages = build_retrieval_index()
    query_terms = set(_tokens(query))
    if not passages or not query_terms:
        return []

    document_frequency: Counter[str] = Counter()
    for passage in passages:
        document_frequency.update(set(passage["tokens"]))
    average_length = sum(len(passage["tokens"]) for passage in passages) / len(passages) or 1
    total = len(passages)
    ranked: list[dict[str, Any]] = []

    for passage in passages:
        frequencies = Counter(passage["tokens"])
        title_terms = set(_tokens(passage["title"]))
        length = len(passage["tokens"])
        score = 0.0
        for term in query_terms:
            frequency = frequencies[term] + (2 if term in title_terms else 0)
            if not frequency:
                continue
            inverse_frequency = math.log(
                1 + (total - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5)
            )
            score += inverse_frequency * (
                frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * length / average_length))
            )
        ranked.append(
            {
                "title": passage["title"],
                "source": passage["source"],
                "category": passage.get("category", "general"),
                "tags": passage.get("tags", ""),
                "content": passage["content"],
                "score": score,
            }
        )

    ranked.sort(key=lambda item: item["score"], reverse=True)
    unique_sources: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for match in ranked:
        if match["score"] < MIN_RELEVANCE:
            continue
        if match["source"] in seen_sources:
            continue
        seen_sources.add(match["source"])
        unique_sources.append(match)
        if len(unique_sources) == top_k:
            break
    return unique_sources


NAVI_CATEGORY_MAP: dict[str, str] = {
    # 1. Windows
    "windows_update.md": "Windows",
    "high_cpu_ram_disk.md": "Windows",
    "windows_bsod_crash.md": "Windows",
    "usb_peripheral_not_recognized.md": "Windows",
    "bitlocker_recovery_key.md": "Windows",
    "windows_license_activation.md": "Windows",
    # 2. Office (2016/19/21/365)
    "email_send_receive_error.md": "Office (2016/19/21/365)",
    "outlook_mailbox_quota.md": "Office (2016/19/21/365)",
    "outlook_ost_corruption.md": "Office (2016/19/21/365)",
    "outlook_autodiscover_failed.md": "Office (2016/19/21/365)",
    "outlook_email.md": "Office (2016/19/21/365)",
    "erp_accounting.md": "Office (2016/19/21/365)",
    # 3. Teams
    "mfa_account.md": "Teams",
    "ad_account_lockout.md": "Teams",
    "certificate_signature.md": "Teams",
    # 4. Máy in & Photo
    "printer_queue.md": "Máy in & Photo",
    "printer_offline_status.md": "Máy in & Photo",
    "printer_driver_install.md": "Máy in & Photo",
    "scanner_smb_folder.md": "Máy in & Photo",
    # 5. Mạng (LAN/Wi-Fi Nội bộ/Khách)
    "ethernet_cable_disconnect.md": "Mạng (LAN/Wi-Fi Nội bộ/Khách)",
    "wifi_network.md": "Mạng (LAN/Wi-Fi Nội bộ/Khách)",
    "dns_dhcp_conflict.md": "Mạng (LAN/Wi-Fi Nội bộ/Khách)",
    "slow_network_latency.md": "Mạng (LAN/Wi-Fi Nội bộ/Khách)",
    "proxy_pac_bypass.md": "Mạng (LAN/Wi-Fi Nội bộ/Khách)",
    "remote_desktop_rdp.md": "Mạng (LAN/Wi-Fi Nội bộ/Khách)",
    # 6. VPN & NAS
    "vpn_forticlient.md": "VPN & NAS",
    "openvpn_client_error.md": "VPN & NAS",
    "vpn_split_tunnel.md": "VPN & NAS",
    "folder_access.md": "VPN & NAS",
    "shared_folder_permission.md": "VPN & NAS",
}

PRIORITY_VI_LABELS: dict[str, str] = {
    "urgent": "Khẩn cấp",
    "high": "Cao",
    "medium": "Trung bình",
    "low": "Thấp",
}

ESCALATE_SOURCES: set[str] = {
    "folder_access.md",
    "shared_folder_permission.md",
    "bitlocker_recovery_key.md",
    "ad_account_lockout.md",
    "windows_license_activation.md",
    "certificate_signature.md",
}


def suggest_ticket_triage(
    question: str,
    matches: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized = _fold_text(question)
    source = matches[0]["source"] if matches else ""
    category = "general"
    if matches and matches[0].get("category"):
        category = matches[0]["category"]
    elif source:
        try:
            from app import store
            db_cat = store.get_document_category_from_db(source)
            category = db_cat or CATEGORY_BY_SOURCE.get(source, "general")
        except Exception:
            category = CATEGORY_BY_SOURCE.get(source, "general")

    if any(marker in normalized for marker in URGENT_MARKERS):
        priority = "urgent"
        priority_reason = "Có dấu hiệu ảnh hưởng nhiều người hoặc sự cố an ninh; cần IT xác nhận."
    elif any(marker in normalized for marker in HIGH_PRIORITY_MARKERS):
        priority = "high"
        priority_reason = "Mô tả cho thấy người dùng có thể bị gián đoạn công việc; cần IT xác nhận."
    else:
        priority = "medium"
        priority_reason = "Mức mặc định; hãy điều chỉnh theo tác động thực tế."

    category_reason = (
        f"Gợi ý từ runbook {source}."
        if source
        else "Chưa có runbook đủ phù hợp; chọn danh mục thủ công."
    )

    # 1. Phân loại Navi Category (6 nhóm hạ tầng thực tế)
    navi_category = NAVI_CATEGORY_MAP.get(source)
    if not navi_category:
        if any(w in normalized for w in ["windows", "bsod", "man hinh xanh", "cap nhat", "update", "cpu", "ram", "disk", "usb", "bitlocker"]):
            navi_category = "Windows"
        elif any(w in normalized for w in ["office", "outlook", "word", "excel", "email", "mail", "ost", "mailbox", "misa", "erp"]):
            navi_category = "Office (2016/19/21/365)"
        elif any(w in normalized for w in ["teams", "mfa", "authenticator", "otp", "xac thuc", "tai khoan", "khoa tai khoan", "ky so", "token", "chung thu"]):
            navi_category = "Teams"
        elif any(w in normalized for w in ["may in", "printer", "photo", "photocopy", "scan", "spooler", "ket lenh"]):
            navi_category = "Máy in & Photo"
        elif any(w in normalized for w in ["wifi", "wi-fi", "mang day", "lan", "ethernet", "mat mang", "dns", "dhcp", "ip", "ping", "cham mang", "rdp", "remote desktop"]):
            navi_category = "Mạng (LAN/Wi-Fi Nội bộ/Khách)"
        elif any(w in normalized for w in ["vpn", "forticlient", "openvpn", "nas", "thu muc chia se", "o dia mang", "shared folder", "folder", "access denied"]):
            navi_category = "VPN & NAS"
        else:
            navi_category = "Khác"

    priority_label = PRIORITY_VI_LABELS.get(priority, "Trung bình")

    # 2. Phân luồng xử lý (Resolution Scope): SELF_SERVICE vs ESCALATE_IT
    is_escalate = False
    escalation_reason = ""
    if not matches:
        is_escalate = True
        escalation_reason = "Chưa có hướng dẫn tự khắc phục phù hợp trong hệ thống; cần kỹ thuật viên IT tiếp nhận và xử lý trực tiếp."
    elif source in ESCALATE_SOURCES:
        is_escalate = True
        if source in {"folder_access.md", "shared_folder_permission.md"}:
            escalation_reason = "Truy cập và cấp quyền thư mục chia sẻ trên NAS đòi hỏi phân quyền Quản trị viên IT (Admin / NTFS ACL) hoặc phê duyệt của Quản lý."
        elif source == "bitlocker_recovery_key.md":
            escalation_reason = "Mã khôi phục BitLocker Recovery Key 48 số được lưu trữ bảo mật trên hệ thống máy chủ Quản trị IT."
        elif source == "ad_account_lockout.md":
            escalation_reason = "Tài khoản bị khóa trên Active Directory / Domain Controller cần kỹ thuật viên IT mở khóa trực tiếp."
        elif source == "windows_license_activation.md":
            escalation_reason = "Kích hoạt bản quyền Windows / Office yêu cầu máy chủ cấp phép bản quyền của IT nội bộ."
        elif source == "certificate_signature.md":
            escalation_reason = "Gia hạn chứng thư số hoặc lỗi thiết bị USB Token cần kỹ thuật viên IT / An toàn thông tin xử lý."
    elif priority == "urgent":
        is_escalate = True
        escalation_reason = "Sự cố mức độ khẩn cấp ảnh hưởng diện rộng, cần chuyển thẳng kỹ thuật viên IT ứng cứu ngay lập tức."
    else:
        escalate_keywords = [
            "cap quyen", "cấp quyền", "xin quyen", "xin quyền", "phan quyen", "phân quyền",
            "mo khoa", "mở khóa", "quen mat khau", "quên mật khẩu",
            "hong may", "hỏng máy", "hong phan cung", "hỏng phần cứng",
            "thay muc", "thay mực", "chay no", "cháy nổ",
            "dut cap", "đứt cáp", "ket giay nang", "kẹt giấy nặng",
            "hong photo", "hỏng photo", "vuot quyen", "vượt quyền",
            "chuyen thang it", "chuyển thẳng it", "can it", "cần it",
            "cap vpn", "cấp vpn", "xin vpn", "cai vpn", "cài vpn"
        ]
        if "vpn" in normalized and any(w in normalized for w in ["cap", "xin", "yeu cau", "cai dat", "dang ky"]):
            is_escalate = True
            escalation_reason = "Chính sách công ty quy định VPN chỉ cấp cho nhân sự Lễ tân và IT. Yêu cầu cấp mới VPN cần có phê duyệt của Quản lý và chuyển thẳng IT xử lý."
        elif any(kw in normalized for kw in escalate_keywords):
            is_escalate = True
            escalation_reason = "Sự cố có dấu hiệu vượt thẩm quyền người dùng (cần quyền Admin, cấp quyền NAS/VPN hoặc thay thế phần cứng). Cần chuyển thẳng cho IT."

    resolution_scope = "ESCALATE_IT" if is_escalate else "SELF_SERVICE"

    return {
        "category": category,
        "category_reason": category_reason,
        "priority": priority,
        "priority_reason": priority_reason,
        "requires_confirmation": True,
        "navi_category": navi_category,
        "priority_label": priority_label,
        "resolution_scope": resolution_scope,
        "escalation_reason": escalation_reason,
    }


def synthesize_answer_with_llm(
    question: str,
    matches: list[dict[str, Any]],
) -> str | None:
    """Tổng hợp câu trả lời tự nhiên từ ngữ cảnh Runbook bằng LLM (nếu được kích hoạt).

    Giới hạn và fallback (prompt không bảo đảm loại bỏ hallucination):
    - Nếu ENABLE_LLM_GENERATION=false hoặc thiếu API key -> trả về None.
    - System prompt ràng buộc chặt chẽ: chỉ dùng dữ liệu từ các đoạn Runbook được trích xuất.
    - Timeout ngắn (mặc định 5s) và bọc try/except an toàn -> fallback về template tĩnh nếu lỗi.
    """
    if not config.ENABLE_LLM_GENERATION or not config.LLM_API_KEY or not matches:
        return None

    context_blocks: list[str] = []
    for idx, match in enumerate(matches[:3], start=1):
        context_blocks.append(
            f"--- Runbook [{idx}]: {match['title']} ({match['source']}) ---\n{match['content']}"
        )
    context_text = "\n\n".join(context_blocks)

    system_prompt = (
        "Bạn là trợ lý IT Helpdesk nội bộ. Hãy dựa CHỈ vào các đoạn Runbook bên dưới để "
        "hướng dẫn người dùng giải quyết sự cố CNTT ngắn gọn, rõ ràng theo từng bước.\n"
        "Nếu tài liệu không đủ thông tin, hãy nêu rõ và khuyên người dùng tạo ticket hỗ trợ.\n"
        "Tuyệt đối không tự suy đoán thông tin ngoài Runbook."
    )
    user_prompt = f"Runbook tham khảo:\n{context_text}\n\nSự cố của người dùng: {question}"

    try:
        url = f"{config.LLM_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 512,
        }
        response = httpx.post(url, headers=headers, json=payload, timeout=config.LLM_TIMEOUT_SECONDS)
        if response.status_code == 200:
            data = response.json()
            choices = data.get("choices")
            if choices and isinstance(choices, list):
                content = choices[0].get("message", {}).get("content", "").strip()
                if content:
                    return content
    except Exception:
        return None
    return None


def generate_answer(question: str) -> dict[str, Any]:
    if is_out_of_scope(question):
        triage = suggest_ticket_triage(question, [])
        return {
            "answer": (
                "Yêu cầu của bạn nằm ngoài phạm vi hỗ trợ kỹ thuật CNTT của hệ thống OpsMind. "
                "Hệ thống chỉ hỗ trợ giải quyết sự cố thiết bị, phần mềm, mạng và tài khoản doanh nghiệp. "
                "Nếu bạn gặp sự cố CNTT, vui lòng mô tả lỗi hoặc tạo ticket hỗ trợ."
            ),
            "sources": [],
            "matches": [],
            "grounded": False,
            "has_sources": False,
            "answer_verification": "not_verified",
            "triage": triage,
            "llm_generated": False,
        }

    matches = retrieve_relevant_context(question)
    triage = suggest_ticket_triage(question, matches)
    if not matches:
        return {
            "answer": (
                "Mình chưa tìm thấy hướng dẫn đủ liên quan trong Knowledge Base. "
                "Bạn có thể tạo ticket để IT kiểm tra trực tiếp."
            ),
            "sources": [],
            "matches": [],
            "grounded": False,
            "has_sources": False,
            "answer_verification": "not_verified",
            "triage": triage,
            "llm_generated": False,
        }

    sources = [
        {
            "title": match["title"],
            "source": match["source"],
            "score": round(match["score"], 3),
        }
        for match in matches
    ]

    llm_synthesized = synthesize_answer_with_llm(question, matches)
    if llm_synthesized:
        answer = llm_synthesized
        llm_generated = True
    else:
        answer = (
            "Mình tìm thấy hướng dẫn liên quan trong Knowledge Base. "
            "Hãy thử các bước được trích dẫn bên dưới; nếu chưa khắc phục được, hãy tạo ticket "
            "và chuyển cho IT Support."
        )
        llm_generated = False

    return {
        "answer": answer,
        "sources": sources,
        "matches": matches,
        "grounded": True,
        # Compatibility field: grounded means retrieved sources, not verified claims.
        "has_sources": True,
        "answer_verification": "not_verified",
        "triage": triage,
        "llm_generated": llm_generated,
    }
