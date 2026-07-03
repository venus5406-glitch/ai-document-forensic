from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image

from .scoring import make_result


def analyze_ocr(pages: list[Image.Image], pdf_text: str = "") -> dict[str, Any]:
    suspicious: list[str] = []
    safe: list[str] = []
    logs: list[str] = []
    extracted_pages: list[str] = []
    score = 0

    reader = None
    easyocr_error = ""
    try:
        import easyocr  # type: ignore

        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        logs.append("easyocr 엔진을 사용했습니다.")
    except Exception as exc:
        easyocr_error = str(exc)
        logs.append(f"easyocr unavailable: {exc}")

    for index, page in enumerate(pages, start=1):
        text = ""
        try:
            if reader is not None:
                results = reader.readtext(np.array(page.convert("RGB")), detail=0, paragraph=True)
                text = "\n".join(str(item) for item in results)
            else:
                try:
                    import pytesseract  # type: ignore

                    text = pytesseract.image_to_string(page)
                    logs.append("pytesseract fallback을 사용했습니다.")
                except Exception as exc:
                    logs.append(f"Page {index} OCR skipped: {exc}")
        except Exception as exc:
            logs.append(f"Page {index} OCR failed: {exc}")
        extracted_pages.append(text)

    ocr_text = "\n".join(extracted_pages).strip()
    broken_ratio = _broken_char_ratio(ocr_text)
    pdf_len = len((pdf_text or "").strip())
    ocr_len = len(ocr_text)

    if not ocr_text:
        score += 10 if reader is not None else 0
        suspicious.append("OCR 텍스트가 거의 추출되지 않았습니다.")
    else:
        safe.append(f"OCR 텍스트 {ocr_len}자를 추출했습니다.")
    if broken_ratio > 0.08:
        score += 10
        suspicious.append("OCR 결과에서 깨진 문자 비율이 높습니다.")
    if pdf_len > 80 and ocr_len > 20:
        gap = abs(pdf_len - ocr_len) / max(pdf_len, ocr_len)
        if gap > 0.65:
            score += 20
            suspicious.append("PDF 내부 텍스트와 OCR 텍스트 길이 차이가 큽니다.")
        else:
            safe.append("PDF 내부 텍스트와 OCR 텍스트 길이가 크게 어긋나지 않습니다.")
    elif pdf_len < 20 and ocr_len > 80:
        safe.append("이미지 기반 문서에서 OCR 텍스트를 보조 추출했습니다.")

    success = bool(reader is not None or ocr_text)
    if not success:
        logs.append("OCR 엔진이 없어 OCR 항목은 신뢰도 계산에만 반영됩니다.")

    return make_result(
        name="OCR 텍스트 분석",
        score=score,
        max_score=50,
        suspicious_points=suspicious,
        safe_points=safe,
        logs=logs,
        raw={
            "text": ocr_text,
            "page_texts": extracted_pages,
            "ocr_length": ocr_len,
            "pdf_text_length": pdf_len,
            "broken_ratio": broken_ratio,
            "easyocr_error": easyocr_error,
        },
        success=success,
    )


def _broken_char_ratio(text: str) -> float:
    if not text:
        return 0.0
    broken = sum(1 for char in text if char == "\ufffd")
    return broken / max(len(text), 1)

