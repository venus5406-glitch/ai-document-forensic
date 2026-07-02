from __future__ import annotations

from io import BytesIO
from typing import Any

import cv2
import fitz
import numpy as np
from PIL import Image, ImageChops, ImageEnhance


def load_document_preview(uploaded_file: Any) -> Image.Image:
    """Load an uploaded image or the first page of a PDF as an RGB preview."""
    filename = uploaded_file.name.lower()
    data = uploaded_file.getvalue()

    if filename.endswith(".pdf"):
        return _load_pdf_first_page(data)

    return Image.open(BytesIO(data)).convert("RGB")


def analyze_document(image: Image.Image) -> dict[str, Any]:
    """Run lightweight OpenCV-based document forgery checks."""
    resized = _resize_image(image.convert("RGB"))

    ela = error_level_analysis(resized)
    noise = noise_inconsistency_analysis(resized)
    blur = blur_difference_analysis(resized)

    combined = _combine_maps([ela, noise, blur])
    boxes = _find_suspicious_boxes(combined)
    result_image = _draw_boxes(resized, boxes)
    score = _calculate_score(ela, noise, blur, boxes)

    return {
        "score": score,
        "level": _level_from_score(score),
        "result_image": result_image,
        "boxes": boxes,
        "summary": _summary(boxes),
        "reasons": _build_reasons(ela, noise, blur, boxes),
    }


def error_level_analysis(image: Image.Image, quality: int = 88) -> np.ndarray:
    """Detect regions that react differently after JPEG recompression."""
    buffer = BytesIO()
    image.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)

    recompressed = Image.open(buffer).convert("RGB")
    diff = ImageChops.difference(image, recompressed)
    diff = ImageEnhance.Brightness(diff).enhance(8)
    gray = cv2.cvtColor(np.array(diff), cv2.COLOR_RGB2GRAY)
    return _normalize(gray)


def noise_inconsistency_analysis(image: Image.Image) -> np.ndarray:
    """Estimate local noise residual differences across the document."""
    cv_image = _pil_to_bgr(image)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    residual = cv2.absdiff(gray, blurred)
    local_noise = cv2.GaussianBlur(residual, (0, 0), 7)
    local_average = cv2.GaussianBlur(local_noise, (0, 0), 25)
    difference = cv2.absdiff(local_noise, local_average)
    return _normalize(difference)


def blur_difference_analysis(image: Image.Image) -> np.ndarray:
    """Find areas whose sharpness differs from nearby document regions."""
    cv_image = _pil_to_bgr(image)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_32F)
    sharpness = cv2.GaussianBlur(np.abs(laplacian), (0, 0), 5)
    local_average = cv2.GaussianBlur(sharpness, (0, 0), 25)
    difference = np.abs(sharpness - local_average)
    return _normalize(difference)


def _load_pdf_first_page(data: bytes) -> Image.Image:
    document = fitz.open(stream=data, filetype="pdf")
    if document.page_count == 0:
        raise ValueError("PDF에 페이지가 없습니다.")

    page = document.load_page(0)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    return Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")


def _resize_image(image: Image.Image, max_side: int = 1400) -> Image.Image:
    width, height = image.size
    scale = min(max_side / max(width, height), 1.0)
    if scale >= 1.0:
        return image
    return image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)


def _pil_to_bgr(image: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)


def _bgr_to_pil(image: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


def _normalize(values: np.ndarray) -> np.ndarray:
    values = values.astype(np.float32)
    min_value = float(values.min())
    max_value = float(values.max())
    if max_value <= min_value:
        return np.zeros(values.shape, dtype=np.uint8)
    normalized = (values - min_value) / (max_value - min_value)
    return np.uint8(np.clip(normalized * 255, 0, 255))


def _combine_maps(maps: list[np.ndarray]) -> np.ndarray:
    weighted = maps[0].astype(np.float32) * 0.45
    weighted += maps[1].astype(np.float32) * 0.30
    weighted += maps[2].astype(np.float32) * 0.25
    return _normalize(weighted)


def _find_suspicious_boxes(score_map: np.ndarray) -> list[tuple[int, int, int, int]]:
    threshold_value = max(210, int(np.percentile(score_map, 99.4)))
    _, binary = cv2.threshold(score_map, threshold_value, 255, cv2.THRESH_BINARY)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 9))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    binary = cv2.dilate(binary, kernel, iterations=1)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = score_map.shape[0] * score_map.shape[1]
    boxes: list[tuple[int, int, int, int]] = []

    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        area = width * height
        if area < max(250, image_area * 0.00025):
            continue
        if width < 18 or height < 12:
            continue
        boxes.append((x, y, x + width, y + height))

    boxes.sort(key=lambda box: (box[2] - box[0]) * (box[3] - box[1]), reverse=True)
    return boxes[:10]


def _draw_boxes(image: Image.Image, boxes: list[tuple[int, int, int, int]]) -> Image.Image:
    result = _pil_to_bgr(image)

    for x1, y1, x2, y2 in boxes:
        cv2.rectangle(result, (x1, y1), (x2, y2), (0, 0, 255), 3)
        cv2.putText(
            result,
            "Suspicious",
            (x1, max(y1 - 8, 18)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    return _bgr_to_pil(result)


def _calculate_score(
    ela: np.ndarray,
    noise: np.ndarray,
    blur: np.ndarray,
    boxes: list[tuple[int, int, int, int]],
) -> int:
    ela_signal = _map_signal(ela)
    noise_signal = _map_signal(noise)
    blur_signal = _map_signal(blur)
    box_signal = min(len(boxes) * 4, 20)

    score = ela_signal * 0.38 + noise_signal * 0.28 + blur_signal * 0.24 + box_signal
    return int(np.clip(round(score), 0, 100))


def _map_signal(score_map: np.ndarray) -> float:
    high_pixels = score_map[score_map >= 210]
    if high_pixels.size == 0:
        return 0.0
    intensity = float(np.mean(high_pixels) / 255.0)
    coverage = float(high_pixels.size / score_map.size)
    return min((intensity * 34) + (coverage * 4200), 100)


def _level_from_score(score: int) -> str:
    if score >= 70:
        return "높음"
    if score >= 40:
        return "주의"
    return "낮음"


def _summary(boxes: list[tuple[int, int, int, int]]) -> str:
    if not boxes:
        return "큰 조작 의심 영역은 발견되지 않았습니다. 다만 이미지 품질에 따라 결과가 달라질 수 있습니다."
    return f"ELA, 노이즈, 블러 패턴을 종합해 {len(boxes)}개의 의심 영역을 표시했습니다."


def _build_reasons(
    ela: np.ndarray,
    noise: np.ndarray,
    blur: np.ndarray,
    boxes: list[tuple[int, int, int, int]],
) -> list[str]:
    reasons: list[str] = []

    if _map_signal(ela) >= 38:
        reasons.append("일부 영역에서 JPEG 재압축 후 밝기 차이가 크게 나타나 압축 이력 불일치가 의심됩니다.")
    if _map_signal(noise) >= 35:
        reasons.append("문서 배경과 글자 주변의 노이즈 패턴이 균일하지 않아 붙여넣기 흔적 가능성이 있습니다.")
    if _map_signal(blur) >= 35:
        reasons.append("특정 영역의 선명도와 블러 정도가 주변 텍스트와 달라 부분 편집 가능성이 있습니다.")
    if boxes:
        reasons.append(f"빨간 박스로 표시된 {len(boxes)}개 영역은 세 분석 결과가 겹친 우선 검토 후보입니다.")

    if not reasons:
        reasons.append("현재 이미지에서는 ELA, 노이즈, 블러 분석 기준의 강한 이상 신호가 낮게 관찰됩니다.")

    return reasons
