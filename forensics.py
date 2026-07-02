from __future__ import annotations

from io import BytesIO
from typing import Any

import fitz
from PIL import Image


def load_document_preview(uploaded_file: Any) -> Image.Image:
    """Load an uploaded image or the first page of a PDF as an RGB preview."""
    filename = uploaded_file.name.lower()
    data = uploaded_file.getvalue()

    if filename.endswith(".pdf"):
        return _load_pdf_first_page(data)

    return Image.open(BytesIO(data)).convert("RGB")


def analyze_document_dummy(filename: str) -> dict[str, str | int]:
    """Return a deterministic placeholder score for the stage-1 MVP."""
    score = 37 + (sum(filename.encode("utf-8")) % 18)
    level = "주의" if score >= 40 else "낮음"

    return {
        "score": score,
        "level": level,
        "message": "1단계 MVP에서는 실제 포렌식 분석 대신 업로드와 결과 표시 흐름만 검증합니다.",
    }


def _load_pdf_first_page(data: bytes) -> Image.Image:
    document = fitz.open(stream=data, filetype="pdf")
    if document.page_count == 0:
        raise ValueError("PDF에 페이지가 없습니다.")

    page = document.load_page(0)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    return Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")
