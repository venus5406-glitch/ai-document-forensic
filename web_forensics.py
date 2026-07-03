from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

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
MAX_URL_LENGTH = 2048
MAX_REDIRECTS = 5
REQUEST_TIMEOUT = 8
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
ALLOWED_PORTS = {80, 443}


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
    validation_error = _validate_public_url(normalized_url)
    if validation_error:
        return _blocked_url_result(normalized_url, validation_error)

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
    try:
        port = parsed.port
    except ValueError:
        port = None
        warnings.append("포트 형식이 유효하지 않습니다.")

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
    if port and port not in {80, 443}:
        warnings.append("일반 웹 포트가 아닌 포트를 사용합니다.")

    return warnings


def check_redirect(url: str) -> dict:
    normalized_url = _normalize_url(url)
    try:
        response, history = _safe_get(normalized_url)
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
        response, _ = _safe_get(url)
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


def _safe_get(url: str) -> tuple[requests.Response, list[str]]:
    current_url = url
    history: list[str] = []

    for _ in range(MAX_REDIRECTS + 1):
        validation_error = _validate_public_url(current_url)
        if validation_error:
            raise requests.RequestException(validation_error)

        response = _request_limited(current_url)
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("location")
            if not location:
                return response, history
            history.append(response.url)
            current_url = urljoin(response.url, location)
            continue
        return response, history

    raise requests.RequestException("리다이렉트 횟수가 너무 많습니다.")


def _request_limited(url: str) -> requests.Response:
    session = requests.Session()
    session.trust_env = False
    try:
        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=False,
            headers={"User-Agent": "DocuGuardAI/1.0"},
            stream=True,
        )
        chunks: list[bytes] = []
        total_bytes = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total_bytes += len(chunk)
            if total_bytes > MAX_RESPONSE_BYTES:
                response.close()
                raise requests.RequestException("응답 본문이 너무 큽니다.")
            chunks.append(chunk)
        response._content = b"".join(chunks)
        return response
    finally:
        session.close()


def _validate_public_url(url: str) -> str:
    if not url:
        return "URL을 입력하세요."
    if len(url) > MAX_URL_LENGTH:
        return "URL이 너무 깁니다."

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return "HTTP 또는 HTTPS URL만 분석할 수 있습니다."
    if not parsed.hostname:
        return "유효한 도메인을 찾지 못했습니다."
    if parsed.username or parsed.password:
        return "사용자 정보가 포함된 URL은 분석할 수 없습니다."
    try:
        port = parsed.port
    except ValueError:
        return "URL 포트 형식이 유효하지 않습니다."
    if port is not None and port not in ALLOWED_PORTS:
        return "표준 HTTP/HTTPS 포트만 분석할 수 있습니다."

    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "0.0.0.0"} or host.endswith(".local"):
        return "내부 또는 로컬 주소는 보안상 분석할 수 없습니다."

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return _validate_resolved_host(host)

    if _is_private_address(ip):
        return "내부망, 로컬, 예약 IP 주소는 보안상 분석할 수 없습니다."
    return ""


def _validate_resolved_host(host: str) -> str:
    try:
        addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return ""

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if _is_private_address(ip):
            return "내부망으로 해석되는 URL은 보안상 분석할 수 없습니다."
    return ""


def _is_private_address(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _blocked_url_result(url: str, message: str) -> dict:
    parsed = urlparse(url)
    results = {
        "input_url": url,
        "reachable": False,
        "status_code": None,
        "final_url": url,
        "title": "",
        "domain": parsed.netloc,
        "scheme": parsed.scheme,
        "redirect": {
            "ok": False,
            "redirected": False,
            "history": [],
            "final_url": url,
            "status_code": None,
            "warning": message,
        },
        "domain_warnings": [message],
        "keyword_hits": [],
        "error": message,
    }
    results["trust_score"] = calculate_web_trust_score(results)
    results["risk_level"] = _risk_level(results["trust_score"])
    results["reasons"] = _build_reasons(results)
    return results


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
