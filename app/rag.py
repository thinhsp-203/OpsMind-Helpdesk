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


@lru_cache(maxsize=1)
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
    directory: Path,
    original_name: str,
    title: str,
    content: str,
) -> dict[str, str]:
    normalized = unicodedata.normalize("NFKD", Path(original_name).stem.lower())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    normalized = normalized.replace("đ", "d")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")[:64]
    if not slug:
        raise ValueError("Document filename does not contain a usable name.")
    if not title.strip():
        raise ValueError("Document title is required.")

    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{slug}.md"
    if path.exists():
        raise FileExistsError(path.name)
    if directory.resolve() == STORAGE_KNOWLEDGE_DIR.resolve() and (BASE_KNOWLEDGE_DIR / f"{slug}.md").exists():
        raise FileExistsError(path.name)

    document = f"# {title.strip()}\n\n{content.strip()}\n"
    created = False
    try:
        with path.open("x", encoding="utf-8", newline="\n") as file:
            created = True
            file.write(document)
    except FileExistsError:
        raise
    except OSError:
        if created:
            path.unlink(missing_ok=True)
        raise

    try:
        from app import store
        store.create_knowledge_document(
            title=title.strip(),
            category=CATEGORY_BY_SOURCE.get(path.name, "general"),
            content=content.strip(),
            custom_slug=path.name,
            status="published",
            author="admin",
            is_builtin=0,
        )
    except Exception as exc:
        logger.debug("Could not record knowledge document in store: %s", exc)

    load_knowledge_base.cache_clear()
    build_retrieval_index.cache_clear()
    return {"title": title.strip(), "source": path.name}


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
def build_retrieval_index() -> list[dict[str, Any]]:
    passages: list[dict[str, Any]] = []
    for document in load_knowledge_base():
        for chunk in chunk_markdown(document["content"]):
            words = _tokens(f"{document['title']} {chunk}")
            passages.append(
                {
                    "title": document["title"],
                    "source": document["source"],
                    "category": document.get("category", CATEGORY_BY_SOURCE.get(document["source"], "general")),
                    "tags": document.get("tags", ""),
                    "content": chunk,
                    "tokens": words,
                }
            )
    return passages


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


def suggest_ticket_triage(
    question: str,
    matches: list[dict[str, Any]],
) -> dict[str, str | bool]:
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
    return {
        "category": category,
        "category_reason": category_reason,
        "priority": priority,
        "priority_reason": priority_reason,
        "requires_confirmation": True,
    }


def synthesize_answer_with_llm(
    question: str,
    matches: list[dict[str, Any]],
) -> str | None:
    """Tổng hợp câu trả lời tự nhiên từ ngữ cảnh Runbook bằng LLM (nếu được kích hoạt).

    Nguyên tắc an toàn (Zero-Hallucination & Fallback):
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
        "triage": triage,
        "llm_generated": llm_generated,
    }
