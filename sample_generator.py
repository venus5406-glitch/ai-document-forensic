from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont


PAGE_SIZE = (1100, 1500)


def create_sample_document(tampered: bool = False) -> Image.Image:
    image = Image.new("RGB", PAGE_SIZE, "#f8f7f2")
    draw = ImageDraw.Draw(image)
    fonts = _fonts()

    _paper_texture(image)
    _header(draw, fonts)
    _contract_body(draw, fonts)
    _table(draw, fonts, tampered)
    _footer(draw, fonts)
    _stamp(draw, tampered)

    if tampered:
        _tamper_amount_and_date(image, draw, fonts)

    return image


def sample_png_bytes(tampered: bool = False) -> bytes:
    buffer = BytesIO()
    create_sample_document(tampered=tampered).save(buffer, format="PNG")
    return buffer.getvalue()


def _fonts() -> dict[str, ImageFont.ImageFont]:
    names = ["malgun.ttf", "arial.ttf", "DejaVuSans.ttf"]

    def load(size: int, bold: bool = False) -> ImageFont.ImageFont:
        candidates = ["malgunbd.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else names
        for name in candidates:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    return {
        "title": load(44, True),
        "subtitle": load(22, False),
        "body": load(25, False),
        "body_bold": load(26, True),
        "small": load(19, False),
        "stamp": load(30, True),
    }


def _paper_texture(image: Image.Image) -> None:
    pixels = image.load()
    width, height = image.size
    for y in range(0, height, 3):
        for x in range(0, width, 3):
            shade = 246 + ((x * 17 + y * 11) % 9)
            pixels[x, y] = (shade, shade - 1, shade - 7)


def _header(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont]) -> None:
    draw.rectangle((70, 70, 1030, 190), outline="#1c2938", width=3)
    draw.text((95, 95), "OFFICIAL SUPPLY CONTRACT", fill="#111827", font=fonts["title"])
    draw.text((96, 155), "Document ID: DG-2026-0715-AX9", fill="#475569", font=fonts["subtitle"])
    draw.line((70, 230, 1030, 230), fill="#94a3b8", width=2)


def _contract_body(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont]) -> None:
    rows = [
        ("Issuer", "Blue Harbor Logistics Co., Ltd."),
        ("Recipient", "Northline Insurance & Risk Office"),
        ("Subject", "Medical equipment transport coverage agreement"),
        ("Policy No.", "INS-7429-2026"),
        ("Prepared", "2026-07-15"),
    ]
    y = 280
    for key, value in rows:
        draw.text((95, y), key, fill="#334155", font=fonts["body_bold"])
        draw.text((290, y), value, fill="#111827", font=fonts["body"])
        y += 58

    paragraph = [
        "This notice confirms the attached contract terms and payment obligation.",
        "All parties acknowledge that the values below are final unless amended",
        "through a signed and stamped written addendum.",
    ]
    y += 35
    for line in paragraph:
        draw.text((95, y), line, fill="#1f2937", font=fonts["body"])
        y += 45


def _table(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont], tampered: bool) -> None:
    x1, y1, x2, y2 = 95, 650, 1005, 920
    draw.rectangle((x1, y1, x2, y2), outline="#334155", width=2)
    draw.rectangle((x1, y1, x2, y1 + 58), fill="#e2e8f0", outline="#334155", width=2)
    headers = ["Item", "Date", "Amount", "Status"]
    xs = [120, 420, 650, 840]
    for x, header in zip(xs, headers):
        draw.text((x, y1 + 15), header, fill="#0f172a", font=fonts["body_bold"])

    rows = [
        ("Base premium", "2026-07-20", "$12,400", "Approved"),
        ("Handling rider", "2026-07-22", "$1,850", "Approved"),
        ("Total due", "2026-07-25", "$14,250", "Pending"),
    ]
    y = y1 + 75
    for row in rows:
        for x, value in zip(xs, row):
            fill = "#111827"
            if tampered and value in {"2026-07-25", "$14,250"}:
                fill = "#1f2937"
            draw.text((x, y), value, fill=fill, font=fonts["body"])
        draw.line((x1, y + 45, x2, y + 45), fill="#cbd5e1", width=1)
        y += 68


def _footer(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont]) -> None:
    draw.line((95, 1080, 490, 1080), fill="#111827", width=2)
    draw.text((95, 1095), "Authorized Signature", fill="#475569", font=fonts["small"])
    draw.text((95, 1190), "Reviewed by: M. Han", fill="#111827", font=fonts["body"])
    draw.text((95, 1235), "Retention: 7 years", fill="#64748b", font=fonts["small"])


def _stamp(draw: ImageDraw.ImageDraw, tampered: bool) -> None:
    color = "#b91c1c" if not tampered else "#d92323"
    draw.ellipse((735, 1030, 965, 1260), outline=color, width=9)
    draw.ellipse((775, 1070, 925, 1220), outline=color, width=4)
    draw.text((795, 1125), "APPROVED", fill=color)
    draw.text((815, 1160), "DOCUGUARD", fill=color)


def _tamper_amount_and_date(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    fonts: dict[str, ImageFont.ImageFont],
) -> None:
    patch = Image.new("RGB", (185, 45), "#fff9e8")
    patch_draw = ImageDraw.Draw(patch)
    for x in range(0, 185, 8):
        patch_draw.line((x, 0, x, 45), fill="#f1ead8")
    patch_draw.text((0, -4), "$24,950", fill="#0b1220", font=fonts["body"])
    patch = patch.filter(ImageFilter.UnsharpMask(radius=1.6, percent=180, threshold=2))
    image.paste(_jpeg_roundtrip(patch, quality=28), (650, 862))

    patch = Image.new("RGB", (180, 45), "#f2f0e7")
    patch_draw = ImageDraw.Draw(patch)
    for y in range(0, 45, 6):
        patch_draw.line((0, y, 180, y), fill="#e2ded2")
    patch_draw.text((0, -4), "2026-08-05", fill="#111827", font=fonts["body"])
    patch = patch.filter(ImageFilter.GaussianBlur(radius=1.1))
    image.paste(_jpeg_roundtrip(patch, quality=24), (420, 862))


def _jpeg_roundtrip(image: Image.Image, quality: int) -> Image.Image:
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")
