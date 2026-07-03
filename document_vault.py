from __future__ import annotations

import base64
import hashlib
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image


MAX_VAULT_ITEMS = 10
VAULT_STORAGE_KEY = "docuguard_document_vault_v1"


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def infer_document_type(name: str) -> str:
    suffix = Path(name).suffix.replace(".", "").upper()
    return suffix or "SAMPLE"


def make_duplicate_key(name: str, document_key: str, page_count: int) -> str:
    raw_key = f"{name}|{document_key}|{page_count}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def create_document_vault_item(
    *,
    name: str,
    document_key: str,
    uploaded_at: str,
    pages: list[Image.Image],
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    analyzed_at = utc_now_iso()
    duplicate_key = make_duplicate_key(name, document_key, len(pages))
    max_score = max((int(result.get("score", 0)) for result in results), default=0)
    high_result = max(results, key=lambda result: int(result.get("score", 0)), default={})
    suspicious_count = sum(len(result.get("reasons", [])) for result in results)

    return {
        "id": hashlib.sha256(f"{duplicate_key}|{analyzed_at}".encode("utf-8")).hexdigest()[:16],
        "duplicate_key": duplicate_key,
        "name": name,
        "uploaded_at": uploaded_at,
        "analyzed_at": analyzed_at,
        "verdict": _verdict_from_score(max_score),
        "confidence": max(0, min(100, 100 - max_score)),
        "suspicion_score": max_score,
        "document_type": infer_document_type(name),
        "summary": str(high_result.get("summary", "분석 요약이 없습니다.")),
        "suspicious_count": suspicious_count,
        "thumbnail": make_thumbnail_data_url(pages[0]) if pages else "",
        "pages": pages,
        "results": results,
    }


def add_document_to_vault(vault: list[dict[str, Any]], item: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    if any(saved.get("duplicate_key") == item.get("duplicate_key") for saved in vault):
        return vault, "duplicate"

    next_vault = [*vault, item]
    if len(next_vault) > MAX_VAULT_ITEMS:
        next_vault = next_vault[-MAX_VAULT_ITEMS:]

    return next_vault, "saved"


def remove_document_from_vault(vault: list[dict[str, Any]], document_id: str) -> list[dict[str, Any]]:
    return [item for item in vault if item.get("id") != document_id]


def sort_vault_items(items: list[dict[str, Any]], sort_mode: str) -> list[dict[str, Any]]:
    if sort_mode == "오래된순":
        return sorted(items, key=lambda item: str(item.get("analyzed_at", "")))
    if sort_mode == "진위 여부별":
        order = {"위험": 0, "검토 필요": 1, "신뢰 가능": 2}
        return sorted(items, key=lambda item: (order.get(str(item.get("verdict")), 9), -int(item.get("confidence", 0))))
    if sort_mode == "신뢰도순":
        return sorted(items, key=lambda item: int(item.get("confidence", 0)), reverse=True)
    return sorted(items, key=lambda item: str(item.get("analyzed_at", "")), reverse=True)


def filter_vault_items(items: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return items
    return [item for item in items if normalized_query in str(item.get("name", "")).lower()]


def local_storage_payload(vault: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": 1,
        "maxItems": MAX_VAULT_ITEMS,
        "savedCount": len(vault),
        "items": [
            {
                "id": item.get("id"),
                "duplicateKey": item.get("duplicate_key"),
                "name": item.get("name"),
                "uploadedAt": item.get("uploaded_at"),
                "analyzedAt": item.get("analyzed_at"),
                "verdict": item.get("verdict"),
                "confidence": item.get("confidence"),
                "suspicionScore": item.get("suspicion_score"),
                "documentType": item.get("document_type"),
                "summary": item.get("summary"),
                "suspiciousCount": item.get("suspicious_count"),
                "thumbnail": item.get("thumbnail"),
            }
            for item in vault
        ],
    }


def make_thumbnail_data_url(image: Image.Image) -> str:
    thumbnail = image.copy().convert("RGB")
    thumbnail.thumbnail((220, 160))
    buffer = BytesIO()
    thumbnail.save(buffer, format="JPEG", quality=72, optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _verdict_from_score(score: int) -> str:
    if score >= 70:
        return "위험"
    if score >= 40:
        return "검토 필요"
    return "신뢰 가능"
