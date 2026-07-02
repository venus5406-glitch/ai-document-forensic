from __future__ import annotations

from io import BytesIO
from typing import Any

import cv2
import fitz
import numpy as np
from PIL import Image, ImageChops, ImageEnhance

Box = tuple[int, int, int, int]


def load_document_pages(uploaded_file: Any) -> list[Image.Image]:
    """Load an uploaded image or every page of a PDF as RGB images."""
    filename = uploaded_file.name.lower()
    data = uploaded_file.getvalue()

    if filename.endswith(".pdf"):
        return _load_pdf_pages(data)

    return [Image.open(BytesIO(data)).convert("RGB")]


def load_document_preview(uploaded_file: Any) -> Image.Image:
    """Backward-compatible helper that returns the first loaded page."""
    return load_document_pages(uploaded_file)[0]


def analyze_document(image: Image.Image) -> dict[str, Any]:
    """Run OpenCV-based document forgery checks with conservative box filtering."""
    resized = _resize_image(image.convert("RGB"))

    ela = error_level_analysis(resized)
    noise = noise_inconsistency_analysis(resized)
    blur = blur_difference_analysis(resized)
    background = background_inconsistency_analysis(resized)

    base_map = _combine_maps([ela, noise, blur])
    text_mask = _text_edge_mask(resized)
    priority_mask = _priority_region_mask(resized)
    score_map = _candidate_score_map(base_map, background, text_mask, priority_mask)
    boxes = _find_suspicious_boxes(score_map, text_mask)
    result_image = _draw_boxes(resized, boxes)
    score = _calculate_score(score_map, boxes)

    return {
        "score": score,
        "level": _level_from_score(score),
        "result_image": result_image,
        "boxes": boxes,
        "summary": _summary(boxes),
        "reasons": _build_reasons(ela, noise, blur, score_map, boxes),
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
    """Estimate local noise residual differences against the document-wide pattern."""
    cv_image = _pil_to_bgr(image)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    residual = cv2.absdiff(gray, blurred)
    local_noise = cv2.GaussianBlur(residual, (0, 0), 7)
    document_noise = cv2.GaussianBlur(local_noise, (0, 0), 45)
    difference = cv2.absdiff(local_noise, document_noise)
    return _normalize(difference)


def blur_difference_analysis(image: Image.Image) -> np.ndarray:
    """Find areas whose sharpness differs from nearby document regions."""
    cv_image = _pil_to_bgr(image)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_32F)
    sharpness = cv2.GaussianBlur(np.abs(laplacian), (0, 0), 5)
    local_average = cv2.GaussianBlur(sharpness, (0, 0), 35)
    difference = np.abs(sharpness - local_average)
    return _normalize(difference)


def background_inconsistency_analysis(image: Image.Image) -> np.ndarray:
    """Find rectangular background/texture changes that are not ordinary text strokes."""
    cv_image = _pil_to_bgr(image)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    local_background = cv2.GaussianBlur(gray, (0, 0), 17)
    page_background = cv2.GaussianBlur(gray, (0, 0), 75)
    difference = cv2.absdiff(local_background, page_background)
    return _normalize(difference)


def _load_pdf_pages(data: bytes) -> list[Image.Image]:
    document = fitz.open(stream=data, filetype="pdf")
    if document.page_count == 0:
        raise ValueError("PDF has no pages.")

    pages: list[Image.Image] = []
    for page_index in range(document.page_count):
        page = document.load_page(page_index)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        pages.append(Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB"))

    return pages


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
    weighted = maps[0].astype(np.float32) * 0.42
    weighted += maps[1].astype(np.float32) * 0.34
    weighted += maps[2].astype(np.float32) * 0.24
    return _normalize(weighted)


def _text_edge_mask(image: Image.Image) -> np.ndarray:
    """Return a mask for ordinary text strokes so they can be downweighted."""
    cv_image = _pil_to_bgr(image)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    dark_text = cv2.threshold(gray, 125, 255, cv2.THRESH_BINARY_INV)[1]
    edges = cv2.Canny(gray, 80, 180)
    mask = cv2.bitwise_or(dark_text, edges)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3))
    mask = cv2.dilate(mask, kernel, iterations=1)
    return mask > 0


def _priority_region_mask(image: Image.Image) -> np.ndarray:
    """Prioritize likely edited zones: dates, amounts, signatures, stamps, tables."""
    width, height = image.size
    mask = np.zeros((height, width), dtype=np.float32)

    # Table/payment zones are often in the middle of contracts.
    mask[int(height * 0.38) : int(height * 0.70), int(width * 0.25) : int(width * 0.92)] = 1.0
    # Signature and stamp zones tend to be near the lower page area.
    mask[int(height * 0.68) : int(height * 0.92), int(width * 0.05) : int(width * 0.95)] = 1.0

    # Keep a weak baseline elsewhere so uploaded layouts still work.
    return np.maximum(mask, 0.45)


def _candidate_score_map(
    base_map: np.ndarray,
    background_map: np.ndarray,
    text_mask: np.ndarray,
    priority_mask: np.ndarray,
) -> np.ndarray:
    score = base_map.astype(np.float32) * 0.35 + background_map.astype(np.float32) * 0.75

    # Text strokes naturally have high edges/noise. Keep them, but heavily reduce their weight.
    score[text_mask] *= 0.10
    score *= priority_mask

    local_mean = cv2.GaussianBlur(score, (0, 0), 33)
    local_delta = np.maximum(score - local_mean, 0)
    score = score * 0.45 + local_delta * 1.15
    return np.uint8(np.clip(score, 0, 255))


def _find_suspicious_boxes(score_map: np.ndarray, text_mask: np.ndarray) -> list[Box]:
    score = score_map.astype(np.float32)
    mean = float(np.mean(score))
    std = float(np.std(score))
    threshold_value = int(np.clip(mean + 3.0 * std, 105, 245))
    _, binary = cv2.threshold(score_map, threshold_value, 255, cv2.THRESH_BINARY)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 13))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    binary = cv2.dilate(binary, kernel, iterations=1)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = score_map.shape[0] * score_map.shape[1]
    candidates: list[tuple[Box, float]] = []

    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        area = width * height
        if width < 20 or height < 10:
            continue
        if area < max(1400, image_area * 0.0012):
            continue
        if area > image_area * 0.18:
            continue

        box = (x, y, x + width, y + height)
        x1, y1, x2, y2 = box
        region = score_map[y1:y2, x1:x2]
        text_coverage = float(np.mean(text_mask[y1:y2, x1:x2]))
        if text_coverage > 0.28:
            continue
        region_peak = float(np.percentile(region, 95))
        if region_peak < threshold_value + 12:
            continue
        suspicious_score = float(np.mean(region) + region_peak)
        candidates.append((box, suspicious_score))

    merged = _merge_ranked_boxes(candidates, max_distance=28)
    merged.sort(key=lambda item: item[1], reverse=True)
    return [box for box, _ in merged[:5]]


def _merge_ranked_boxes(candidates: list[tuple[Box, float]], max_distance: int) -> list[tuple[Box, float]]:
    merged: list[tuple[Box, float]] = []

    for box, score in sorted(candidates, key=lambda item: item[1], reverse=True):
        did_merge = False
        for index, (existing, existing_score) in enumerate(merged):
            if _iou(box, existing) > 0.12 or _box_distance(box, existing) <= max_distance:
                new_box = _union_box(box, existing)
                merged[index] = (new_box, max(score, existing_score))
                did_merge = True
                break
        if not did_merge:
            merged.append((box, score))

    return merged


def _iou(a: Box, b: Box) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(ix2 - ix1, 0) * max(iy2 - iy1, 0)
    if inter == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / float(area_a + area_b - inter)


def _box_distance(a: Box, b: Box) -> int:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    dx = max(bx1 - ax2, ax1 - bx2, 0)
    dy = max(by1 - ay2, ay1 - by2, 0)
    return int((dx * dx + dy * dy) ** 0.5)


def _union_box(a: Box, b: Box) -> Box:
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _draw_boxes(image: Image.Image, boxes: list[Box]) -> Image.Image:
    result = _pil_to_bgr(image)

    for index, (x1, y1, x2, y2) in enumerate(boxes, start=1):
        cv2.rectangle(result, (x1, y1), (x2, y2), (0, 0, 255), 3)
        label = f"Additional review {index}"
        cv2.putText(
            result,
            label,
            (x1, max(y1 - 8, 18)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    return _bgr_to_pil(result)


def _calculate_score(score_map: np.ndarray, boxes: list[Box]) -> int:
    candidate_signal = _map_signal(score_map)
    if not boxes:
        return int(np.clip(round(candidate_signal * 0.45), 0, 35))

    box_signals = []
    for x1, y1, x2, y2 in boxes:
        region = score_map[y1:y2, x1:x2]
        box_signals.append(float(np.mean(region) * 0.45 + np.percentile(region, 95) * 0.55) / 255 * 100)

    score = candidate_signal * 0.45 + max(box_signals) * 0.55
    return int(np.clip(round(score), 0, 100))


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


def _level_from_score(score: int) -> str:
    if score >= 70:
        return "High"
    if score >= 40:
        return "Review"
    return "Low"


def _summary(boxes: list[Box]) -> str:
    if not boxes:
        return "No strong local review candidates were found. This is not a final authenticity decision."
    return f"{len(boxes)} local review candidate area(s) were found after filtering ordinary text edges."


def _build_reasons(
    ela: np.ndarray,
    noise: np.ndarray,
    blur: np.ndarray,
    score_map: np.ndarray,
    boxes: list[Box],
) -> list[str]:
    if not boxes:
        return ["No strong local anomalies were found after filtering ordinary text edges. This is an additional-review aid, not a final authenticity decision."]

    reasons: list[str] = []

    if _map_signal(ela) >= 42:
        reasons.append("Some local areas react differently after JPEG recompression, so compression history mismatch is a review candidate.")
    if _map_signal(noise) >= 38:
        reasons.append("A local noise pattern differs from the document-wide background pattern.")
    if _map_signal(blur) >= 38:
        reasons.append("A local sharpness or blur pattern differs from nearby content.")
    if _map_signal(score_map) >= 38 and boxes:
        reasons.append("Only the strongest merged local candidates are shown; ordinary text stroke edges are downweighted.")

    if not reasons:
        reasons.append("ELA, noise, and blur checks did not find strong local anomalies. This is not a final authenticity decision.")

    return reasons
