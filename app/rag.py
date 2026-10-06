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
    "a", "an", "and", "are", "bao", "biet", "bi", "bị", "cach", "cho", "co",
    "cua", "de", "did", "du", "duoc", "gio", "giup", "ha", "hay", "how", "i",
    "in", "initiate", "is", "it", "la", "lam", "loi", "mai", "mot", "mua", "my",
    "ngay", "noi", "not", "of", "on", "tai", "the", "tho", "thoi", "thu", "tiet",
    "toi", "to", "va", "ve", "voi", "what", "when", "where", "why", "viet", "you",
    "bai", "received",
    "can", "dang", "ket", "noi", "team", "viec",
}
SYNONYMS = {
    "wifi": "network",
    "wireless": "network",
    "internet": "network",
    "lan": "network",
    "vpn": "vpn",
    "forticlient": "vpn",
    "openvpn": "vpn",
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
    "windows": "windows",
    "mfa": "mfa",
    "authenticator": "mfa",
}
MIN_RELEVANCE = 0.12
CATEGORY_BY_SOURCE = {
    "certificate_signature.md": "security",
    "erp_accounting.md": "software",
    "folder_access.md": "security",
    "mfa_account.md": "security",
    "outlook_email.md": "software",
    "printer_queue.md": "hardware",
    "vpn_forticlient.md": "network",
    "wifi_network.md": "network",
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
    return folded.replace("đ", "d")


def _tokens(text: str) -> list[str]:
    words = TOKEN_RE.findall(_fold_text(text))
    compounds = {
        ("may", "in"): "printer",
        ("chung", "thu", "so"): "certificate",
        ("chung", "thu"): "certificate",
        ("chu", "ky", "so"): "certificate",
        ("ky", "so"): "certificate",
        ("thu", "muc"): "access",
        ("login", "approval", "request"): "mfa",
    }
    normalized = []
    index = 0
    while index < len(words):
        compound = next(
            (
                (parts, canonical)
                for parts, canonical in compounds.items()
                if tuple(words[index:index + len(parts)]) == parts
            ),
            None,
        )
        if compound:
            parts, canonical = compound
            normalized.append(canonical)
            index += len(parts)
            continue
        word = words[index]
        index += 1
        if word in STOP_WORDS:
            continue
        canonical = SYNONYMS.get(word, word)
        if canonical:
            normalized.append(canonical)
    return normalized


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
