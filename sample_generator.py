from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont


PAGE_SIZE = (1100, 1500)


def create_contract_sample(tampered: bool = False) -> Image.Image:
    image = Image.new("RGB", PAGE_SIZE, "#faf8f1")
    draw = ImageDraw.Draw(image)
    fonts = _load_fonts()

    _draw_paper_texture(image)
    _draw_header(draw, fonts)
    _draw_parties(draw, fonts)
    _draw_payment_table(draw, fonts)
    _draw_signature_area(draw, fonts)

    if tampered:
        _tamper_date_amount_signature(image, fonts)

    return image


def _load_fonts() -> dict[str, ImageFont.ImageFont]:
    def load(size: int, bold: bool = False) -> ImageFont.ImageFont:
        candidates = (
            ["malgunbd.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]
            if bold
            else ["malgun.ttf", "arial.ttf", "DejaVuSans.ttf"]
        )
        for name in candidates:
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    return {
        "title": load(46, True),
        "section": load(28, True),
        "body": load(25),
        "small": load(19),
        "signature": load(34, True),
    }


def _draw_paper_texture(image: Image.Image) -> None:
    pixels = image.load()
    width, height = image.size
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            shade = 246 + ((x * 13 + y * 7) % 8)
            pixels[x, y] = (shade, shade - 1, shade - 6)


def _draw_header(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont]) -> None:
    draw.rectangle((70, 70, 1030, 190), outline="#1f2937", width=3)
    draw.text((95, 96), "SERVICE SUPPLY CONTRACT", fill="#111827", font=fonts["title"])
    draw.text((98, 157), "Contract No. DG-2026-0715-A19", fill="#475569", font=fonts["small"])
    draw.line((70, 230, 1030, 230), fill="#94a3b8", width=2)


def _draw_parties(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont]) -> None:
    rows = [
        ("Seller", "Blue Harbor Logistics Co., Ltd."),
        ("Buyer", "Northline Insurance & Risk Office"),
        ("Subject", "Document inspection and archive service"),
        ("Effective Date", "2026-07-15"),
        ("Payment Due", "2026-07-30"),
    ]
    y = 285
    for key, value in rows:
        draw.text((95, y), key, fill="#334155", font=fonts["section"])
        draw.text((330, y + 2), value, fill="#111827", font=fonts["body"])
        y += 62

    body = [
        "Both parties agree to the inspection, delivery, and payment terms below.",
        "Any modification must be confirmed by written amendment and signature.",
    ]
    y += 32
    for line in body:
        draw.text((95, y), line, fill="#1f2937", font=fonts["body"])
        y += 46


def _draw_payment_table(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont]) -> None:
    x1, y1, x2, y2 = 95, 680, 1005, 920
    draw.rectangle((x1, y1, x2, y2), outline="#334155", width=2)
    draw.rectangle((x1, y1, x2, y1 + 58), fill="#e2e8f0", outline="#334155", width=2)

    headers = ["Item", "Date", "Amount", "Status"]
    xs = [120, 420, 660, 850]
    for x, header in zip(xs, headers):
        draw.text((x, y1 + 15), header, fill="#0f172a", font=fonts["section"])

    rows = [
        ("Base service", "2026-07-20", "$12,400", "Approved"),
        ("Archive fee", "2026-07-24", "$1,850", "Approved"),
        ("Total due", "2026-07-30", "$14,250", "Pending"),
    ]
    y = y1 + 78
    for row in rows:
        for x, value in zip(xs, row):
            draw.text((x, y), value, fill="#111827", font=fonts["body"])
        draw.line((x1, y + 47, x2, y + 47), fill="#cbd5e1", width=1)
        y += 68


def _draw_signature_area(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont]) -> None:
    draw.line((95, 1110, 485, 1110), fill="#111827", width=2)
    draw.text((95, 1128), "Authorized Signature", fill="#64748b", font=fonts["small"])
    draw.text((125, 1044), "M. Han", fill="#111827", font=fonts["signature"])
    draw.text((95, 1220), "Signed on 2026-07-15", fill="#111827", font=fonts["body"])

    draw.ellipse((745, 1030, 965, 1250), outline="#b91c1c", width=8)
    draw.ellipse((785, 1070, 925, 1210), outline="#b91c1c", width=4)
    draw.text((812, 1122), "APPROVED", fill="#b91c1c", font=fonts["body"])
    draw.text((810, 1160), "DOCUGUARD", fill="#b91c1c", font=fonts["small"])


def _tamper_date_amount_signature(image: Image.Image, fonts: dict[str, ImageFont.ImageFont]) -> None:
    _paste_compressed_patch(
        image,
        size=(210, 54),
        position=(410, 888),
        text="2026-08-05",
        font=fonts["body"],
        fill="#111827",
        quality=15,
        blur=0.8,
    )
    _paste_compressed_patch(
        image,
        size=(190, 54),
        position=(650, 888),
        text="$24,950",
        font=fonts["body"],
        fill="#0f172a",
        quality=12,
        sharpen=True,
    )
    _paste_compressed_patch(
        image,
        size=(235, 74),
        position=(105, 1022),
        text="D. Kim",
        font=fonts["signature"],
        fill="#111827",
        quality=10,
        blur=0.5,
    )


def _paste_compressed_patch(
    image: Image.Image,
    size: tuple[int, int],
    position: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
    quality: int,
    blur: float = 0.0,
    sharpen: bool = False,
) -> None:
    patch = Image.new("RGB", size, "#fff9e8")
    patch_draw = ImageDraw.Draw(patch)

    for x in range(0, size[0], 5):
        patch_draw.line((x, 0, x, size[1]), fill="#e7dac1")
    for y in range(0, size[1], 6):
        patch_draw.line((0, y, size[0], y), fill="#f0e5cc")
    for y in range(size[1]):
        for x in range(size[0]):
            if (x * 19 + y * 31) % 17 == 0:
                patch_draw.point((x, y), fill="#8f8068")
            if (x // 4 + y // 4) % 9 == 0:
                patch_draw.point((x, y), fill="#ffffff")

    patch_draw.text((4, 2), text, fill=fill, font=font)
    patch_draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline="#d1b98f", width=2)
    if blur:
        patch = patch.filter(ImageFilter.GaussianBlur(radius=blur))
    if sharpen:
        patch = patch.filter(ImageFilter.UnsharpMask(radius=1.5, percent=190, threshold=2))

    buffer = BytesIO()
    patch.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    image.paste(Image.open(buffer).convert("RGB"), position)
