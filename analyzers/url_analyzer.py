from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .scoring import make_result
from .text_analyzer import SUSPICIOUS_KEYWORDS

try:
    import tldextract  # type: ignore
except Exception:
    tldextract = None


def analyze_url_risk(url: str) -> dict[str, Any]:
    normalized = _normalize_url(url)
    suspicious: list[str] = []
    safe: list[str] = []
    logs: list[str] = []
    score = 0
    parsed = urlparse(normalized)
    host = parsed.netloc.lower().split("@")[-1].split(":")[0]
    extracted = _extract_domain_parts(normalized, host)

    if parsed.scheme != "https":
        score += 20
        suspicious.append("HTTPS가 아닌 URL입니다.")
    else:
        safe.append("HTTPS URL입니다.")
    if len(normalized) > 110:
        score += 10
        suspicious.append("URL 길이가 과도하게 깁니다.")
    if host.count(".") >= 3:
        score += 10
        suspicious.append("서브도메인이 많습니다.")
    if _domain_digit_hyphen_ratio(host) > 0.32:
        score += 10
        suspicious.append("도메인에 숫자 또는 하이픈 비율이 높습니다.")

    fetch_raw: dict[str, Any] = {}
    page_text = ""
    try:
        response = requests.get(
            normalized,
            timeout=10,
            allow_redirects=True,
            headers={"User-Agent": "DocuGuardAI/1.0"},
        )
        history = [item.url for item in response.history]
        final_url = response.url
        if len(history) >= 3:
            score += 10
            suspicious.append("리다이렉트가 3회 이상 발생했습니다.")
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        description_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
        description = description_tag.get("content", "") if description_tag else ""
        password_inputs = soup.find_all("input", attrs={"type": re.compile("password", re.I)})
        if password_inputs:
            score += 10
            suspicious.append("페이지에 비밀번호 입력 필드가 있습니다.")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        page_text = soup.get_text(" ", strip=True)
        keyword_hits = [keyword for keyword in SUSPICIOUS_KEYWORDS if keyword in page_text.lower()]
        if keyword_hits:
            score += min(len(keyword_hits) * 3, 15)
            suspicious.append(f"의심 키워드가 포함되어 있습니다: {', '.join(keyword_hits)}")
        fetch_raw = {
            "reachable": True,
            "status_code": response.status_code,
            "redirect_count": len(history),
            "redirect_history": history,
            "final_url": final_url,
            "title": title,
            "description": description,
            "password_inputs": len(password_inputs),
            "keyword_hits": keyword_hits,
            "text": page_text[:20000],
        }
        safe.append(f"HTTP 상태 코드 {response.status_code} 응답을 받았습니다.")
    except requests.RequestException as exc:
        score += 5
        suspicious.append("URL 요청에 실패했습니다.")
        logs.append(f"Request failed: {exc}")
        fetch_raw = {
            "reachable": False,
            "status_code": None,
            "redirect_count": 0,
            "redirect_history": [],
            "final_url": normalized,
            "title": "",
            "description": "",
            "password_inputs": 0,
            "keyword_hits": [],
            "text": "",
            "error": str(exc),
        }

    return make_result(
        name="URL 위험도 분석",
        score=score,
        max_score=100,
        suspicious_points=suspicious,
        safe_points=safe,
        logs=logs,
        raw={
            "input_url": normalized,
            "scheme": parsed.scheme,
            "host": host,
            "domain": extracted["domain"],
            "subdomain": extracted["subdomain"],
            **fetch_raw,
        },
    )


def _normalize_url(url: str) -> str:
    value = url.strip()
    if not value:
        return ""
    if not re.match(r"^https?://", value, flags=re.I):
        return f"https://{value}"
    return value


def _domain_digit_hyphen_ratio(host: str) -> float:
    if not host:
        return 0.0
    count = sum(1 for char in host if char.isdigit() or char == "-")
    return count / len(host)


def _extract_domain_parts(url: str, host: str) -> dict[str, str]:
    if tldextract is not None:
        extracted = tldextract.extract(url)
        domain = f"{extracted.domain}.{extracted.suffix}" if extracted.suffix else host
        return {"domain": domain, "subdomain": extracted.subdomain}

    parts = [part for part in host.split(".") if part]
    if len(parts) >= 2:
        return {"domain": ".".join(parts[-2:]), "subdomain": ".".join(parts[:-2])}
    return {"domain": host, "subdomain": ""}
