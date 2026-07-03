from __future__ import annotations

from typing import Any

import cv2
import numpy as np
from PIL import Image

from forensics import analyze_document, blur_difference_analysis, error_level_analysis, noise_inconsistency_analysis

from .scoring import make_result


def analyze_image_forensics(image: Image.Image, page_label: str = "page") -> dict[str, Any]:
    suspicious: list[str] = []
    safe: list[str] = []
    logs: list[str] = []

    try:
        rgb = image.convert("RGB")
        visual = analyze_document(rgb)
        ela = error_level_analysis(rgb)
        blur = blur_difference_analysis(rgb)
        noise = noise_inconsistency_analysis(rgb)
        ela_mean = float(np.mean(ela))
        ela_max = float(np.max(ela))
        blur_signal = _map_signal(blur)
        noise_signal = _map_signal(noise)
        score = int(visual.get("score", 0))

        # ELA is an auxiliary signal only. It raises review priority but never
        # acts as a standalone authenticity decision.
        if ela_mean > 28:
            score += 10
            suspicious.append("ELA 평균 차이가 높아 압축 이력 차이를 추가 확인해야 합니다.")
        if ela_max > 220:
            score += 10
            suspicious.append("ELA 최대 차이가 높은 영역이 있습니다.")
        if blur_signal > 42:
            score += 10
            suspicious.append("특정 영역의 선명도/블러 차이가 주변과 다릅니다.")
        elif blur_signal > 28:
            score += 5
            suspicious.append("약한 블러 불균형 신호가 있습니다.")
        if noise_signal > 40:
            score += 10
            suspicious.append("노이즈 분포가 균일하지 않은 영역이 있습니다.")
        if not visual.get("boxes"):
            safe.append("강한 국소 편집 후보 박스는 발견되지 않았습니다.")
        else:
            suspicious.extend(str(item) for item in visual.get("reasons", []))

        return make_result(
            name=f"이미지 포렌식 분석 ({page_label})",
            score=min(score, 100),
            max_score=100,
            suspicious_points=suspicious,
            safe_points=safe,
            logs=logs,
            raw={
                "visual": visual,
                "ela_mean": ela_mean,
                "ela_max": ela_max,
                "blur_signal": blur_signal,
                "noise_signal": noise_signal,
            },
        )
    except Exception as exc:
        return make_result(
            name=f"이미지 포렌식 분석 ({page_label})",
            score=0,
            suspicious_points=["이미지 포렌식 분석을 완료하지 못했습니다."],
            logs=[str(exc)],
            success=False,
        )


def _map_signal(score_map: np.ndarray) -> float:
    values = score_map.astype(np.float32)
    threshold = float(np.mean(values) + 2.5 * np.std(values))
    high_pixels = values[values >= threshold]
    if high_pixels.size == 0:
        return 0.0
    intensity = float(np.mean(high_pixels) / 255.0)
    coverage = float(high_pixels.size / values.size)
    peak = float(np.percentile(high_pixels, 95) / 255.0)
    return min((intensity * 42) + (peak * 18) + (coverage * 900), 100)

