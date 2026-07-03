from __future__ import annotations

from typing import Any

from .scoring import recommended_actions


def build_rule_based_report(summary: dict[str, Any]) -> str:
    score = int(summary.get("score", 0))
    verdict = summary.get("verdict", "추가 확인 필요")
    confidence = int(summary.get("confidence", 0))
    suspicious = summary.get("suspicious_points", [])[:6]
    safe = summary.get("safe_points", [])[:4]
    actions = recommended_actions(score)

    lines = [
        "### 보조 분석 리포트",
        f"- 최종 판정 보조값: {verdict}",
        f"- 위험 점수: {score}/100",
        f"- 신뢰도: {confidence}%",
        "",
        "이 리포트는 규칙 기반 분석 엔진의 결과를 사용자가 이해하기 쉽게 정리한 보조 설명입니다. 법적 또는 최종 진위 판정이 아닙니다.",
    ]
    if suspicious:
        lines.extend(["", "의심 신호:"])
        lines.extend(f"- {item}" for item in suspicious)
    if safe:
        lines.extend(["", "안전 신호:"])
        lines.extend(f"- {item}" for item in safe)
    lines.extend(["", "추천 조치:"])
    lines.extend(f"- {item}" for item in actions)
    return "\n".join(lines)

