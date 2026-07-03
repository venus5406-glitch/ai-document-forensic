from __future__ import annotations

from io import BytesIO
from typing import Any

import fitz

from .scoring import make_result


SUSPICIOUS_PRODUCERS = (
    "canva",
    "photoshop",
    "illustrator",
    "smallpdf",
    "ilovepdf",
    "adobe photoshop",
)


def analyze_pdf(data: bytes, filename: str = "") -> dict[str, Any]:
    suspicious: list[str] = []
    safe: list[str] = []
    logs: list[str] = []
    score = 0
    raw: dict[str, Any] = {"filename": filename}

    try:
        document = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        return make_result(
            name="PDF 메타데이터 분석",
            score=0,
            suspicious_points=["PDF 구조를 열 수 없어 메타데이터 분석을 건너뛰었습니다."],
            logs=[f"PDF open failed: {exc}"],
            raw=raw,
            success=False,
        )

    metadata = document.metadata or {}
    page_sizes: list[tuple[float, float]] = []
    page_texts: list[str] = []
    image_counts: list[int] = []
    font_names: set[str] = set()

    for page in document:
        rect = page.rect
        page_sizes.append((round(rect.width, 2), round(rect.height, 2)))
        try:
            page_texts.append(page.get_text("text") or "")
        except Exception as exc:
            page_texts.append("")
            logs.append(f"Page {page.number + 1} text extraction failed: {exc}")
        try:
            image_counts.append(len(page.get_images(full=True)))
        except Exception as exc:
            image_counts.append(0)
            logs.append(f"Page {page.number + 1} image count failed: {exc}")
        try:
            for font in page.get_fonts(full=True):
                if len(font) > 3 and font[3]:
                    font_names.add(str(font[3]))
        except Exception as exc:
            logs.append(f"Page {page.number + 1} font extraction failed: {exc}")

    creator = str(metadata.get("creator") or "")
    producer = str(metadata.get("producer") or "")
    creation = str(metadata.get("creationDate") or "")
    modified = str(metadata.get("modDate") or "")
    text_length = sum(len(text.strip()) for text in page_texts)
    total_images = sum(image_counts)

    raw.update(
        {
            "page_count": document.page_count,
            "metadata": metadata,
            "page_sizes": page_sizes,
            "image_counts": image_counts,
            "font_names": sorted(font_names),
            "text_length": text_length,
            "page_texts": page_texts,
        }
    )
    _augment_with_pypdf(data, raw, logs)
    _augment_with_pdfplumber(data, raw, logs)

    if not metadata:
        score += 5
        suspicious.append("PDF 메타데이터가 비어 있습니다.")
    else:
        safe.append("PDF 메타데이터를 읽었습니다.")
    if not creation:
        score += 5
        suspicious.append("CreationDate가 없습니다.")
    if modified and not creation:
        score += 5
        suspicious.append("수정일만 있고 생성일이 없습니다.")
    if any(tool in f"{creator} {producer}".lower() for tool in SUSPICIOUS_PRODUCERS):
        score += 10
        suspicious.append(f"Creator/Producer에 편집 도구 흔적이 있습니다: {creator or producer}")
    if len(set(page_sizes)) > 1:
        score += 10
        suspicious.append("페이지 크기가 서로 다릅니다.")
    else:
        safe.append("페이지 크기가 일관적입니다.")
    if document.page_count and total_images / document.page_count >= 8:
        score += 10
        suspicious.append("페이지당 이미지 객체 수가 많습니다.")
    if text_length < 40 and total_images >= max(1, document.page_count):
        score += 15
        suspicious.append("텍스트가 거의 없고 이미지 중심으로 구성된 PDF입니다.")
    if font_names:
        safe.append(f"폰트 {min(len(font_names), 5)}종을 확인했습니다.")

    return make_result(
        name="PDF 메타데이터 분석",
        score=score,
        max_score=60,
        suspicious_points=suspicious,
        safe_points=safe,
        logs=logs,
        raw=raw,
    )


def _augment_with_pypdf(data: bytes, raw: dict[str, Any], logs: list[str]) -> None:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(BytesIO(data))
        raw["pypdf_metadata"] = {str(key): str(value) for key, value in (reader.metadata or {}).items()}
        raw["pypdf_page_count"] = len(reader.pages)
        logs.append("pypdf metadata cross-check completed.")
    except Exception as exc:
        logs.append(f"pypdf cross-check skipped: {exc}")


def _augment_with_pdfplumber(data: bytes, raw: dict[str, Any], logs: list[str]) -> None:
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(BytesIO(data)) as pdf:
            raw["pdfplumber_page_count"] = len(pdf.pages)
            raw["pdfplumber_text_lengths"] = [len(page.extract_text() or "") for page in pdf.pages[:20]]
        logs.append("pdfplumber text cross-check completed.")
    except Exception as exc:
        logs.append(f"pdfplumber cross-check skipped: {exc}")
