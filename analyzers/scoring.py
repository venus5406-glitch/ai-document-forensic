from __future__ import annotations

from typing import Any


AnalyzerResult = dict[str, Any]


def make_result(
    *,
    name: str,
    score: int = 0,
    max_score: int = 100,
    suspicious_points: list[str] | None = None,
    safe_points: list[str] | None = None,
    logs: list[str] | None = None,
    raw: dict[str, Any] | None = None,
    success: bool = True,
) -> AnalyzerResult:
    score = max(0, min(int(score), int(max_score)))
    return {
        "name": name,
        "score": score,
        "max_score": max(1, int(max_score)),
        "risk_level": risk_level_from_score(normalize_score(score, max_score)),
        "suspicious_points": suspicious_points or [],
        "safe_points": safe_points or [],
        "logs": logs or [],
        "raw": raw or {},
        "success": success,
    }


def normalize_score(score: int | float, max_score: int | float) -> int:
    if max_score <= 0:
        return 0
    return max(0, min(100, round((float(score) / float(max_score)) * 100)))


def risk_level_from_score(score: int) -> str:
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def verdict_from_score(score: int) -> str:
    if score >= 65:
        return "위조 의심"
    if score >= 35:
        return "추가 확인 필요"
    return "정상 가능성 높음"


def combine_results(results: list[AnalyzerResult]) -> dict[str, Any]:
    successful = [item for item in results if item.get("success", True)]
    total_max = sum(int(item.get("max_score", 0)) for item in successful)
    total_score = sum(int(item.get("score", 0)) for item in successful)

    # Failed analyzers lower confidence rather than directly increasing risk.
    normalized = normalize_score(total_score, total_max) if total_max else 0
    confidence = round((len(successful) / len(results)) * 100) if results else 0

    suspicious_points: list[str] = []
    safe_points: list[str] = []
    logs: list[str] = []
    for item in results:
        suspicious_points.extend(item.get("suspicious_points", []))
        safe_points.extend(item.get("safe_points", []))
        logs.extend(f"{item.get('name', 'Analyzer')}: {log}" for log in item.get("logs", []))

    return {
        "score": normalized,
        "risk_level": risk_level_from_score(normalized),
        "verdict": verdict_from_score(normalized),
        "confidence": confidence,
        "analyzers": results,
        "suspicious_points": suspicious_points,
        "safe_points": safe_points,
        "logs": logs,
    }


def recommended_actions(score: int) -> list[str]:
    if score >= 65:
        return [
            "문서 제출자에게 원본 파일 재제출을 요청하세요.",
            "발급 기관 또는 공식 사이트에서 문서 번호를 직접 확인하세요.",
            "링크 클릭, 결제, 개인정보 입력을 중단하세요.",
            "내부 검토 또는 법적 확인 절차가 필요할 수 있습니다.",
        ]
    if score >= 35:
        return [
            "발급 기관 공식 사이트에서 문서 번호를 확인하세요.",
            "발신자 이메일 도메인과 URL 도메인을 비교하세요.",
            "원본 파일 또는 이전 버전과 메타데이터를 비교하세요.",
        ]
    return [
        "기본 정보는 비교적 일관적으로 보입니다.",
        "중요 문서라면 발급 기관 원본 확인을 권장합니다.",
    ]

