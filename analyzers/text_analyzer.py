from __future__ import annotations

import re
from typing import Any

from .scoring import make_result


SUSPICIOUS_KEYWORDS = [
    "urgent",
    "verify",
    "password",
    "login",
    "wallet",
    "bank",
    "account",
    "update",
    "free",
    "gift",
    "claim",
    "event",
    "secure",
]

DATE_RE = re.compile(r"\b(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b")
AMOUNT_RE = re.compile(r"(?:[$€£₩]\s?\d[\d,]*(?:\.\d{2})?|\d[\d,]*(?:\.\d{2})?\s?(?:usd|krw|won|달러|원))", re.I)
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\d{2,4}[-.\s]?){2,4}\d{3,4}\b")
URL_RE = re.compile(r"https?://[^\s)>\]]+", re.I)


def analyze_text(text: str, required_keywords: list[str] | None = None, name: str = "텍스트 이상 탐지") -> dict[str, Any]:
    text = text or ""
    lowered = text.lower()
    suspicious: list[str] = []
    safe: list[str] = []
    logs: list[str] = []
    score = 0

    dates = DATE_RE.findall(text)
    amounts = AMOUNT_RE.findall(text)
    emails = EMAIL_RE.findall(text)
    phones = PHONE_RE.findall(text)
    urls = URL_RE.findall(text)
    keyword_hits = [keyword for keyword in SUSPICIOUS_KEYWORDS if keyword in lowered]
    broken_ratio = _broken_char_ratio(text)

    if keyword_hits:
        added = min(len(keyword_hits) * 3, 15)
        score += added
        suspicious.append(f"의심 키워드가 발견되었습니다: {', '.join(keyword_hits)}")
    if _mixed_date_formats(dates):
        score += 8
        suspicious.append("날짜 형식이 한 문서 안에서 일관되지 않습니다.")
    if broken_ratio > 0.08:
        score += 10
        suspicious.append("깨진 문자 또는 비정상 인코딩 비율이 높습니다.")
    if len(urls) + len(emails) >= 8:
        score += 10
        suspicious.append("URL 또는 이메일이 과도하게 많습니다.")
    missing = [item for item in (required_keywords or []) if item.lower() not in lowered]
    if missing:
        score += 5
        suspicious.append(f"중요 필드 후보가 누락되었습니다: {', '.join(missing[:5])}")

    if dates:
        safe.append(f"날짜 패턴 {len(dates)}개를 확인했습니다.")
    if amounts:
        safe.append(f"금액 패턴 {len(amounts)}개를 확인했습니다.")
    if emails or phones:
        safe.append("연락처 패턴을 추출했습니다.")
    if not text.strip():
        logs.append("분석 가능한 텍스트가 거의 없습니다.")

    return make_result(
        name=name,
        score=score,
        max_score=58,
        suspicious_points=suspicious,
        safe_points=safe,
        logs=logs,
        raw={
            "text_length": len(text),
            "dates": dates[:50],
            "amounts": amounts[:50],
            "emails": emails[:50],
            "phones": phones[:50],
            "urls": urls[:50],
            "keyword_hits": keyword_hits,
            "broken_ratio": broken_ratio,
        },
    )


def _mixed_date_formats(dates: list[str]) -> bool:
    if len(dates) < 2:
        return False
    separators = {next((char for char in date if char in "-/."), "") for date in dates}
    starts_with_year = {bool(re.match(r"^\d{4}", date)) for date in dates}
    return len(separators) > 1 or len(starts_with_year) > 1


def _broken_char_ratio(text: str) -> float:
    if not text:
        return 0.0
    broken = sum(1 for char in text if char == "\ufffd" or ord(char) < 32 and char not in "\n\r\t")
    return broken / max(len(text), 1)

