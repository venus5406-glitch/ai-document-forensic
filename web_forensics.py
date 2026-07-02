from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


SUSPICIOUS_KEYWORDS = [
    "당첨",
    "무료",
    "긴급",
    "인증",
    "계좌",
    "환급",
    "투자",
    "이벤트",
    "로그인",
    "비밀번호",
    "winner",
    "free",
    "urgent",
    "verify",
    "account",
    "refund",
    "investment",
    "event",
    "login",
    "password",
]

SHORTENER_DOMAINS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "cutt.ly",
    "rebrand.ly",
    "shorturl.at",
}


@dataclass
class UrlFetchResult:
    reachable: bool
    status_code: int | None
    final_url: str
    title: str
    text: str
    error: str


def analyze_url(url: str) -> dict:
    normalized_url = _normalize_url(url)
    redirect = check_redirect(normalized_url)
    domain_warnings = check_domain_suspicion(normalized_url)

    fetch = _fetch_page(normalized_url)
    keyword_hits = detect_suspicious_keywords(fetch.text)

    results = {
        "input_url": normalized_url,
        "reachable": fetch.reachable,
        "status_code": fetch.status_code,
        "final_url": fetch.final_url,
        "title": fetch.title,
        "domain": urlparse(fetch.final_url or normalized_url).netloc,
        "scheme": urlparse(normalized_url).scheme,
        "redirect": redirect,
        "domain_warnings": domain_warnings,
        "keyword_hits": keyword_hits,
        "error": fetch.error,
    }
    results["trust_score"] = calculate_web_trust_score(results)
    results["risk_level"] = _risk_level(results["trust_score"])
    results["reasons"] = _build_reasons(results)
    return results


def check_domain_suspicion(url: str) -> list:
    parsed = urlparse(_normalize_url(url))
    host = parsed.netloc.lower().split("@")[-1].split(":")[0]
    warnings: list[str] = []

    if parsed.scheme != "https":
        warnings.append("HTTPS가 아닌 주소입니다.")
    if host in SHORTENER_DOMAINS:
        warnings.append("단축 URL 도메인입니다. 최종 이동 주소 확인이 필요합니다.")
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
        warnings.append("도메인 대신 IP 주소를 사용합니다.")
    if host.startswith("xn--"):
        warnings.append("Punycode 도메인입니다. 유사 도메인 가능성을 확인하세요.")
    if host.count("-") >= 2:
        warnings.append("하이픈이 많은 도메인입니다.")
    if sum(char.isdigit() for char in host) >= 4:
        warnings.append("숫자가 많은 도메인입니다.")
    if host.count(".") >= 3:
        warnings.append("서브도메인이 많은 주소입니다.")
    if len(host) > 45:
        warnings.append("도메인 길이가 비정상적으로 깁니다.")

    return warnings


def check_redirect(url: str) -> dict:
    normalized_url = _normalize_url(url)
    try:
        response = requests.get(
            normalized_url,
            timeout=8,
            allow_redirects=True,
            headers={"User-Agent": "DocuGuardAI/1.0"},
        )
        history = [item.url for item in response.history]
        final_url = response.url
        redirected = _strip_fragment(normalized_url) != _strip_fragment(final_url)
        return {
            "ok": True,
            "redirected": redirected,
            "history": history,
            "final_url": final_url,
            "status_code": response.status_code,
            "warning": "입력 URL과 최종 접속 URL이 다릅니다." if redirected else "",
        }
    except requests.RequestException as exc:
        return {
            "ok": False,
            "redirected": False,
            "history": [],
            "final_url": normalized_url,
            "status_code": None,
            "warning": f"리다이렉트 확인 실패: {exc}",
        }


def detect_suspicious_keywords(text: str) -> list:
    lowered = text.lower()
    hits = []
    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword.lower() in lowered:
            hits.append(keyword)
    return sorted(set(hits))


def calculate_web_trust_score(results: dict) -> int:
    score = 100

    if not results.get("reachable"):
        score -= 28
    if results.get("scheme") != "https":
        score -= 12
    if results.get("redirect", {}).get("redirected"):
        score -= 14

    score -= min(len(results.get("domain_warnings", [])) * 8, 32)
    score -= min(len(results.get("keyword_hits", [])) * 5, 25)

    status_code = results.get("status_code")
    if status_code and status_code >= 400:
        score -= 15

    return max(0, min(100, int(score)))


def _fetch_page(url: str) -> UrlFetchResult:
    try:
        response = requests.get(
            url,
            timeout=10,
            allow_redirects=True,
            headers={"User-Agent": "DocuGuardAI/1.0"},
        )
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and not response.text.strip().startswith("<"):
            return UrlFetchResult(
                reachable=True,
                status_code=response.status_code,
                final_url=response.url,
                title="",
                text="",
                error="HTML 페이지가 아닐 수 있습니다.",
            )

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(" ", strip=True)
        return UrlFetchResult(
            reachable=True,
            status_code=response.status_code,
            final_url=response.url,
            title=title,
            text=text[:20000],
            error="",
        )
    except requests.RequestException as exc:
        return UrlFetchResult(
            reachable=False,
            status_code=None,
            final_url=url,
            title="",
            text="",
            error=str(exc),
        )


def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, flags=re.IGNORECASE):
        return f"https://{url}"
    return url


def _strip_fragment(url: str) -> str:
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl().rstrip("/")


def _risk_level(trust_score: int) -> str:
    if trust_score < 45:
        return "높음"
    if trust_score < 75:
        return "주의"
    return "낮음"


def _build_reasons(results: dict) -> list[str]:
    reasons: list[str] = []

    if not results.get("reachable"):
        reasons.append("현재 URL에 접속하지 못했습니다. 증거 보존 상태나 주소 유효성을 추가 확인해야 합니다.")
    if results.get("redirect", {}).get("redirected"):
        reasons.append("입력 URL과 실제 접속 URL이 달라 리다이렉트 경로 확인이 필요합니다.")
    for warning in results.get("domain_warnings", []):
        reasons.append(warning)
    if results.get("keyword_hits"):
        keywords = ", ".join(results["keyword_hits"])
        reasons.append(f"피싱 또는 조작 증거에서 자주 확인되는 키워드가 발견되었습니다: {keywords}")
    if not reasons:
        reasons.append("URL 기본 점검에서 강한 위험 요소는 낮게 관찰됩니다.")

    reasons.append("본 결과는 조작 또는 피싱 가능성이 있어 추가 검토가 필요한 후보를 선별하기 위한 MVP 판단입니다.")
    return reasons
