from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

import cv2
import fitz
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from skimage import exposure, filters, measure, morphology, restoration


@dataclass
class Finding:
    label: str
    description: str
    severity: float


def load_document(uploaded_file: Any) -> Image.Image:
    """Load a JPG/PNG/PDF upload as an RGB PIL image. PDFs use page 1."""
    name = uploaded_file.name.lower()
    data = uploaded_file.getvalue()

    if name.endswith(".pdf"):
        doc = fitz.open(stream=data, filetype="pdf")
        if doc.page_count == 0:
            raise ValueError("PDF에 페이지가 없습니다.")
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        return Image.open(BytesIO(pix.tobytes("png"))).convert("RGB")

    return Image.open(BytesIO(data)).convert("RGB")


def pil_to_cv(image: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)


def cv_to_pil(image: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


def run_forensic_analysis(image: Image.Image) -> dict[str, Any]:
    cv_image = pil_to_cv(image)
    resized = _resize_for_analysis(cv_image)

    ela_map = _ela_map(cv_to_pil(resized))
    noise_map = _noise_inconsistency_map(resized)
    blur_map = _blur_difference_map(resized)
    compression_map = _compression_trace_map(resized)
    stamp_map = _signature_stamp_color_map(resized)

    maps = {
        "압축 흔적 불일치": ela_map,
        "일부 영역의 노이즈 패턴 다름": noise_map,
        "특정 영역의 선명도 차이": blur_map,
        "텍스트 주변 압축 흔적": compression_map,
        "서명/도장 영역 색상 이상": stamp_map,
    }

    combined = _combine_maps(list(maps.values()))
    boxes = _suspicious_boxes(combined, resized.shape[:2])
    score = _score_from_maps(maps, boxes)
    verdict = _verdict(score)
    explanations = _build_explanations(maps, score)
    result = _draw_boxes(resized, boxes)

    return {
        "score": score,
        "verdict": verdict,
        "findings": explanations,
        "boxes": boxes,
        "result_image": cv_to_pil(result),
        "heatmap": Image.fromarray(_color_heatmap(combined)),
        "ela_preview": Image.fromarray(_color_heatmap(ela_map)),
    }


def _resize_for_analysis(image: np.ndarray, max_side: int = 1400) -> np.ndarray:
    height, width = image.shape[:2]
    scale = min(max_side / max(height, width), 1.0)
    if scale == 1.0:
        return image.copy()
    return cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)


def _normalize(values: np.ndarray) -> np.ndarray:
    values = values.astype(np.float32)
    if values.max() <= values.min():
        return np.zeros_like(values, dtype=np.uint8)
    values = (values - values.min()) / (values.max() - values.min())
    return np.uint8(np.clip(values * 255, 0, 255))


def _ela_map(image: Image.Image, quality: int = 88) -> np.ndarray:
    buffer = BytesIO()
    image.save(buffer, "JPEG", quality=quality)
    buffer.seek(0)
    recompressed = Image.open(buffer).convert("RGB")
    diff = ImageChops.difference(image.convert("RGB"), recompressed)
    diff = ImageEnhance.Brightness(diff).enhance(8)
    gray = cv2.cvtColor(np.array(diff), cv2.COLOR_RGB2GRAY)
    return _postprocess_map(gray)


def _noise_inconsistency_map(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = restoration.denoise_wavelet(gray, channel_axis=None, rescale_sigma=True)
    residual = np.abs(gray.astype(np.float32) - denoised.astype(np.float32) * 255.0)
    local_noise = filters.gaussian(residual, sigma=3)
    return _postprocess_map(_normalize(local_noise))


def _blur_difference_map(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_32F)
    sharpness = cv2.GaussianBlur(np.abs(laplacian), (0, 0), 5)
    local_mean = cv2.GaussianBlur(sharpness, (0, 0), 21)
    difference = np.abs(sharpness - local_mean)
    return _postprocess_map(_normalize(difference))


def _compression_trace_map(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 160)
    dilated_edges = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=1)
    block_artifacts = np.zeros_like(gray, dtype=np.float32)

    for offset in range(8, gray.shape[1], 8):
        block_artifacts[:, offset - 1 : offset + 1] += 1
    for offset in range(8, gray.shape[0], 8):
        block_artifacts[offset - 1 : offset + 1, :] += 1

    high_freq = cv2.Laplacian(gray, cv2.CV_32F)
    local_background = cv2.medianBlur(gray, 31)
    background_residual = np.abs(gray.astype(np.float32) - local_background.astype(np.float32))
    patch_edges = cv2.Canny(_normalize(background_residual), 35, 110)
    patch_edges = cv2.dilate(patch_edges, np.ones((3, 3), np.uint8), iterations=1)
    trace = (
        np.abs(high_freq) * (dilated_edges > 0)
        + block_artifacts * 18
        + background_residual * 2.4
        + patch_edges.astype(np.float32) * 0.8
    )
    return _postprocess_map(_normalize(trace))


def _signature_stamp_color_map(image: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hue, saturation, value = cv2.split(hsv)

    red_mask = ((hue < 12) | (hue > 168)) & (saturation > 70) & (value > 70)
    blue_mask = (hue > 90) & (hue < 135) & (saturation > 50) & (value > 50)
    dark_ink_mask = (value < 90) & (saturation > 25)
    color_mask = (red_mask | blue_mask | dark_ink_mask).astype(np.uint8) * 255

    if np.count_nonzero(color_mask) == 0:
        return np.zeros(image.shape[:2], dtype=np.uint8)

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    chroma = cv2.GaussianBlur(np.std(lab[:, :, 1:].astype(np.float32), axis=2), (0, 0), 4)
    anomaly = _normalize(chroma) * (color_mask > 0)
    return _postprocess_map(anomaly)


def _postprocess_map(mask: np.ndarray) -> np.ndarray:
    normalized = _normalize(mask)
    p98 = np.percentile(normalized, 98)
    threshold = max(85, p98)
    binary = (normalized >= threshold).astype(np.uint8) * 255
    binary = morphology.area_opening(binary.astype(bool), area_threshold=80)
    binary = morphology.closing(binary, morphology.disk(4))
    return np.where(binary, normalized, 0).astype(np.uint8)


def _combine_maps(maps: list[np.ndarray]) -> np.ndarray:
    if not maps:
        raise ValueError("분석 맵이 없습니다.")
    stacked = np.stack([m.astype(np.float32) / 255.0 for m in maps], axis=0)
    combined = np.maximum.reduce(stacked)
    combined = cv2.GaussianBlur(combined, (0, 0), 3)
    return np.uint8(np.clip(combined * 255, 0, 255))


def _suspicious_boxes(mask: np.ndarray, shape: tuple[int, int]) -> list[tuple[int, int, int, int]]:
    height, width = shape
    threshold = max(120, int(np.percentile(mask, 97)))
    binary = mask >= threshold
    binary = morphology.area_opening(binary, area_threshold=max(120, int(width * height * 0.00025)))
    binary = morphology.dilation(binary, morphology.footprint_rectangle((7, 11)))
    labels = measure.label(binary)

    boxes: list[tuple[int, int, int, int]] = []
    for region in measure.regionprops(labels):
        min_row, min_col, max_row, max_col = region.bbox
        box_w = max_col - min_col
        box_h = max_row - min_row
        area = box_w * box_h
        if area < width * height * 0.0004:
            continue
        if box_w < 18 or box_h < 12:
            continue
        pad = 10
        boxes.append(
            (
                max(min_col - pad, 0),
                max(min_row - pad, 0),
                min(max_col + pad, width - 1),
                min(max_row + pad, height - 1),
            )
        )

    boxes.sort(key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
    return boxes[:10]


def _score_from_maps(maps: dict[str, np.ndarray], boxes: list[tuple[int, int, int, int]]) -> int:
    weighted = 0.0
    weights = {
        "압축 흔적 불일치": 0.28,
        "일부 영역의 노이즈 패턴 다름": 0.24,
        "특정 영역의 선명도 차이": 0.2,
        "텍스트 주변 압축 흔적": 0.18,
        "서명/도장 영역 색상 이상": 0.1,
    }
    for label, mask in maps.items():
        intensity = float(np.mean(mask) / 255.0)
        peak = float(np.percentile(mask, 99) / 255.0)
        weighted += min((intensity * 420) + (peak * 26), 100) * weights[label]

    weighted += min(len(boxes) * 4, 18)
    return int(np.clip(round(weighted), 0, 100))


def _verdict(score: int) -> str:
    if score >= 70:
        return "높음"
    if score >= 40:
        return "주의"
    return "낮음"


def _build_explanations(maps: dict[str, np.ndarray], score: int) -> list[Finding]:
    findings: list[Finding] = []
    for label, mask in maps.items():
        ratio = np.count_nonzero(mask) / mask.size
        intensity = float(np.mean(mask) / 255.0)
        if ratio > 0.0015 and intensity > 0.0008:
            severity = min((intensity * 420) + float(np.percentile(mask, 99) / 255.0) * 26, 100)
            findings.append(
                Finding(
                    label=label,
                    description=_description_for(label),
                    severity=round(float(severity), 1),
                )
            )

    if not findings:
        findings.append(
            Finding(
                label="명확한 위조 흔적 낮음",
                description="현재 이미지에서는 큰 압축, 노이즈, 선명도 불일치가 강하게 관찰되지 않았습니다.",
                severity=float(score),
            )
        )
    return findings


def _description_for(label: str) -> str:
    descriptions = {
        "압축 흔적 불일치": "다른 저장 이력이나 부분 편집이 있었을 때 ELA 반응이 주변과 다르게 나타날 수 있습니다.",
        "일부 영역의 노이즈 패턴 다름": "붙여넣기 또는 재촬영 영역은 배경 노이즈 분포가 원본 문서와 다르게 보일 수 있습니다.",
        "특정 영역의 선명도 차이": "금액, 날짜, 이름처럼 수정된 영역은 주변 글자보다 흐리거나 지나치게 선명할 수 있습니다.",
        "텍스트 주변 압축 흔적": "문자 경계 주변의 JPEG 블록 흔적과 고주파 패턴을 비교했습니다.",
        "서명/도장 영역 색상 이상": "서명, 도장, 컬러 잉크 후보 영역의 색상 분포가 주변과 다른지 확인했습니다.",
    }
    return descriptions[label]


def _draw_boxes(image: np.ndarray, boxes: list[tuple[int, int, int, int]]) -> np.ndarray:
    result = image.copy()
    overlay = result.copy()
    for x1, y1, x2, y2 in boxes:
        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 255), -1)
        cv2.rectangle(result, (x1, y1), (x2, y2), (0, 0, 255), 3)
    result = cv2.addWeighted(overlay, 0.16, result, 0.84, 0)
    for x1, y1, x2, y2 in boxes:
        cv2.rectangle(result, (x1, y1), (x2, y2), (0, 0, 255), 3)
    return result


def _color_heatmap(mask: np.ndarray) -> np.ndarray:
    equalized = exposure.rescale_intensity(mask, out_range=(0, 255)).astype(np.uint8)
    colored = cv2.applyColorMap(equalized, cv2.COLORMAP_INFERNO)
    return cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
