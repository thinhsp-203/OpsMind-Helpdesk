from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx

from app import config

TOKEN_RE = re.compile(r"[a-z0-9]+")
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"
STOP_WORDS = {
    "a", "an", "and", "are", "bao", "biet", "bi", "but", "cach", "can",
    "cannot", "cant", "cho", "co", "cua", "dang", "de", "did", "du", "duoc",
    "gio", "giup", "ha", "hay", "how", "i", "in", "initiate", "is", "it", "la",
    "lam", "loi", "mai", "mot", "mua", "my", "nao", "ngay", "nha", "noi", "not",
    "of", "on", "received", "repeated", "sao", "several", "tai", "team", "the",
    "tho", "thoi", "thu", "tiet", "to", "toi", "va", "ve", "viec", "viet", "voi",
    "what", "when", "where", "why", "with", "work", "works", "you",
    # Common Vietnamese function syllables (accent-folded). They appear in the Vietnamese
    # runbooks but carry no topical meaning, and otherwise let off-topic questions match.
    "khong", "khi", "nay", "thi", "rat", "nhu", "the", "sau", "truoc", "tren", "duoi",
    "lai", "van", "con", "da", "se", "phai", "neu", "nhung", "cung", "nhieu", "hon",
    "qua", "hom", "ma", "minh", "ban", "chua", "roi", "luc", "cac", "nhung", "nguoi",
    "tu", "den", "ra", "vao", "len", "xuong", "duoc", "dung", "can", "muon", "xin",
    "hien", "bang", "trong", "ngoai", "theo", "tung", "moi", "nhat", "biet", "gi",
}
SYNONYMS = {
    "wifi": "wifi",
    "wireless": "wifi",
    "internet": "network",
    "vpn": "vpn",
    "forticlient": "forticlient",
    "openvpn": "openvpn",
    "printer": "printer",
    "printing": "printer",
    "spooler": "printer",
    "outlook": "email",
    "mail": "email",
    "email": "email",
    "chungthu": "certificate",
    "certificate": "certificate",
    "folder": "access",
    "permission": "access",
    "quyen": "access",
    "erp": "erp",
    "accounting": "erp",
    "update": "update",
    "patch": "update",
    "patching": "update",
    "windows": "windows",
    "mfa": "mfa",
    "authenticator": "mfa",
    "active": "activation",
    "activate": "activation",
    "lag": "latency",
    "pst": "ost",
}
# Vietnamese (accent-folded) phrases -> English/canonical terms used by the runbooks.
# Most runbooks are written in English, so Vietnamese questions need this bilingual
# lexicon to match them. Longer phrases are matched first. An empty tuple drops a
# generic phrase that carries no topical signal.
PHRASES: dict[tuple[str, ...], tuple[str, ...]] = {
    # printing / scanning
    ("may", "in"): ("printer",),
    ("khong", "in"): ("printer", "print"),
    ("lenh", "in"): ("printer", "print", "queue"),
    ("ban", "in"): ("printer", "print"),
    ("in", "ra"): ("printer", "print"),
    ("may", "scan"): ("scan",),
    ("may", "quet"): ("scan",),
    ("quet",): ("scan",),
    ("may", "photocopy"): ("multifunction", "printer", "scan"),
    ("photocopy",): ("multifunction", "printer", "scan"),
    # certificates / signing / access (existing behaviour)
    ("chung", "thu", "so"): ("certificate",),
    ("chung", "thu"): ("certificate",),
    ("chu", "ky", "so"): ("certificate",),
    ("ky", "so"): ("certificate",),
    ("thu", "muc"): ("access",),
    ("chia", "se"): ("shared",),
    ("login", "approval", "request"): ("mfa",),
    # accounts / authentication
    ("mat", "khau"): ("password",),
    ("tai", "khoan"): ("account",),
    ("bi", "khoa"): ("locked", "lockout"),
    ("khoa", "tai", "khoan"): ("lockout", "account"),
    ("dang", "nhap"): ("login", "sign"),
    ("quen",): ("forgot", "reset"),
    ("ma", "khoi", "phuc"): ("recovery", "key"),
    ("khoi", "phuc"): ("recovery",),
    # network
    ("ket", "noi"): ("connect", "connectivity"),
    ("chap", "chon"): ("intermittent", "loses", "connectivity"),
    ("rot", "mang"): ("disconnected", "loses", "connectivity"),
    ("mat", "mang"): ("disconnected", "loses", "connectivity"),
    ("mat", "ket", "noi"): ("disconnected", "loses", "connectivity"),
    ("rot",): ("disconnected", "drops"),
    ("mang", "day"): ("ethernet", "cable"),
    ("day", "mang"): ("ethernet", "cable"),
    ("cap", "mang"): ("ethernet", "cable"),
    ("mang", "cham"): ("slow", "network", "latency"),
    ("mang", "noi", "bo"): ("internal", "network"),
    ("noi", "bo"): ("internal",),
    ("mang",): ("network",),
    ("mat", "goi"): ("packet", "loss"),
    ("trung", "ip"): ("conflict", "ip"),
    ("trung", "dia", "chi"): ("conflict", "address"),
    ("dia", "chi", "ip"): ("ip", "address"),
    ("trinh", "duyet"): ("browser",),
    ("tu", "xa"): ("remote",),
    ("dieu", "khien", "tu", "xa"): ("remote", "desktop"),
    ("dieu", "khien"): ("remote",),
    ("may", "chu"): ("server",),
    # performance / hardware
    ("man", "hinh", "xanh"): ("bsod", "blue", "screen", "crash"),
    ("khoi", "dong", "lai"): ("restart",),
    ("tu", "khoi", "dong"): ("restart",),
    ("cham",): ("slow", "performance"),
    ("chay", "cham"): ("slow", "performance"),
    ("o", "cung"): ("disk",),
    ("o", "dia"): ("disk",),
    ("o", "cung", "day"): ("disk", "full"),
    ("dung", "luong"): ("storage", "space"),
    ("ban", "phim"): ("keyboard", "usb", "peripheral"),
    ("chuot",): ("mouse", "usb", "peripheral"),
    ("khong", "nhan"): (),
    ("nhan", "ip"): ("ip", "dhcp"),
    ("nhan", "dia", "chi", "ip"): ("ip", "address", "dhcp"),
    ("treo",): ("stuck", "hang"),
    # email
    ("hop", "thu", "day"): ("mailbox", "quota", "full"),
    ("hop", "thu"): ("mailbox",),
    ("gui", "thu"): ("send", "email"),
    ("gui",): ("send",),
    ("nhan", "thu"): ("receive", "email"),
    ("nhan", "email"): ("receive", "email"),
    ("bi", "hong"): ("corruption", "repair"),
    ("hong",): ("corruption", "repair"),
    ("cau", "hinh"): ("configuration", "setup"),
    # software
    ("ban", "quyen"): ("license", "activation"),
    ("kich", "hoat"): ("activation",),
    ("cap", "nhat"): ("update",),
    ("cai", "dat"): ("install",),
    ("cai",): ("install",),
    ("phan", "mem"): ("software",),
    ("ke", "toan"): ("erp",),
    # generic phrases without topical signal
    ("may", "tinh"): (),
    ("tai", "lieu"): (),
    ("van", "phong"): (),
}
_PHRASES_BY_LENGTH = sorted(PHRASES.items(), key=lambda item: len(item[0]), reverse=True)
MIN_RELEVANCE = 0.12
CATEGORY_BY_SOURCE = {
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
URGENT_MARKERS = (
    "toan cong ty",
    "ca phong",
    "nhieu nguoi",
    "ma doc",
    "ransomware",
    "bi tan cong",
    "ro ri du lieu",
    "gateway down",
)
HIGH_PRIORITY_MARKERS = (
    "khong the lam viec",
    "khong vao duoc",
    "khong the dang nhap",
    "mat ket noi",
    "loi xac thuc",
    "chung thu het han",
)


def _normalize_title(path: Path) -> str:
    return path.stem.replace("_", " ").replace("-", " ").title()


def _fold_text(text: str) -> str:
    folded = unicodedata.normalize("NFD", text.lower())
    folded = "".join(char for char in folded if unicodedata.category(char) != "Mn")
    folded = folded.replace("đ", "d")
    # "Wi-Fi" / "e-mail" would otherwise split into meaningless fragments ("wi", "fi").
    folded = re.sub(r"\bwi[\s-]?fi\b", "wifi", folded)
    return re.sub(r"\be-mail\b", "email", folded)


def _stem(word: str) -> str:
    """Very light English suffix stripping so fail/failed/fails or update/updates/updating match."""
    if len(word) < 5 or not word.isalpha():
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    for suffix in ("ing", "ed"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            word = word[: -len(suffix)]
            break
    if word.endswith("e") and len(word) >= 5:
        word = word[:-1]
    return word


def _tokens(text: str) -> list[str]:
    words = TOKEN_RE.findall(_fold_text(text))
    normalized: list[str] = []
    index = 0
    while index < len(words):
        phrase = next(
            (
                (parts, canonical)
                for parts, canonical in _PHRASES_BY_LENGTH
                if tuple(words[index:index + len(parts)]) == parts
            ),
            None,
        )
        if phrase:
            parts, canonical = phrase
            normalized.extend(_stem(term) for term in canonical)
            index += len(parts)
            continue
        word = words[index]
        index += 1
        if word in STOP_WORDS:
            continue
        canonical_word = SYNONYMS.get(word, word)
        if canonical_word:
            normalized.append(_stem(canonical_word))
    return normalized


def _phrase_and_synonym_terms() -> frozenset[str]:
    terms = {term for canonical in PHRASES.values() for term in canonical}
    terms.update(SYNONYMS.values())
    return frozenset(_stem(term) for term in terms)


_LEXICON_TERMS = _phrase_and_synonym_terms()


def domain_vocabulary() -> frozenset[str]:
    """IT terms that make a question in scope for the Knowledge Base.

    Built from the bilingual lexicon plus the words of English runbook titles (and the
    acronyms of Vietnamese titles), so documents uploaded by an admin extend it
    automatically. Other Vietnamese title words are excluded on purpose: syllables such
    as "bo", "dong" or "chung" are too generic and let off-topic questions look relevant.
    """
    return _title_vocabulary(tuple(document["title"] for document in load_knowledge_base()))


@lru_cache(maxsize=4)
def _title_vocabulary(titles: tuple[str, ...]) -> frozenset[str]:
    vocabulary = set(_LEXICON_TERMS)
    for title in titles:
        if title.isascii():
            vocabulary.update(_tokens(title))
        else:
            # Vietnamese title: keep only acronyms / product names such as ERP or MFA.
            acronyms = [word for word in re.findall(r"[A-Za-z0-9]+", title) if word.isupper()]
            vocabulary.update(_tokens(" ".join(acronyms)))
    return frozenset(vocabulary)


@lru_cache(maxsize=1)
def load_knowledge_base() -> list[dict[str, str]]:
    documents: list[dict[str, str]] = []
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        heading = re.search(r"(?m)^#\s+(.+?)\s*$", content)
        documents.append(
            {
                "title": heading.group(1) if heading else _normalize_title(path),
                "source": path.name,
                "content": content,
            }
        )
    return documents


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
                    "content": chunk,
                    "tokens": words,
                }
            )
    return passages


def retrieve_relevant_context(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    passages = build_retrieval_index()
    query_terms = set(_tokens(query))
    if not passages or not query_terms:
        return []
    # Out-of-scope guard: BM25 scores are not comparable across queries, and generic
    # Vietnamese syllables also occur in the Vietnamese runbooks. A question is only
    # answered when it contains at least one IT domain term that the passage also matches.
    domain_terms = query_terms & domain_vocabulary()
    if not domain_terms:
        return []

    document_frequency: Counter[str] = Counter()
    for passage in passages:
        document_frequency.update(set(passage["tokens"]))
    average_length = sum(len(passage["tokens"]) for passage in passages) / len(passages) or 1
    total = len(passages)
    ranked: list[dict[str, Any]] = []

    for passage in passages:
        if domain_terms.isdisjoint(passage["tokens"]):
            continue
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
        if source in CATEGORY_BY_SOURCE
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
