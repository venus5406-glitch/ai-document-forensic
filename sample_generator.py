from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from io import BytesIO

from PIL import Image, ImageDraw, ImageFilter, ImageFont


PAGE_SIZE = (1100, 1500)


@dataclass
class ContractData:
    contract_no: str
    seller: str
    buyer: str
    subject: str
    effective_date: str
    payment_due: str
    base_amount: int
    fee_amount: int
    total_amount: int
    signer: str
    tampered_date: str
    tampered_amount: int
    tampered_signer: str


def create_contract_sample(tampered: bool = False, seed: int | None = None) -> Image.Image:
    rng = random.Random(seed if seed is not None else random.SystemRandom().randint(1, 10_000_000))
    data = _random_contract_data(rng)
    image = Image.new("RGB", PAGE_SIZE, "#faf8f1")
    draw = ImageDraw.Draw(image)
    fonts = _load_fonts()

    _draw_paper_texture(image, rng)
    _draw_header(draw, fonts, data)
    _draw_parties(draw, fonts, data)
    _draw_payment_table(draw, fonts, data)
    _draw_signature_area(draw, fonts, data)

    if tampered:
        _tamper_date_amount_signature(image, fonts, data, rng)

    return image


def _random_contract_data(rng: random.Random) -> ContractData:
    sellers = [
        "Blue Harbor Logistics Co., Ltd.",
        "Aurora Medical Supply Inc.",
        "Greenline Archive Systems",
        "Northstar Digital Office",
        "Hanseo Risk Management",
    ]
    buyers = [
        "Northline Insurance & Risk Office",
        "Mirae Claims Review Center",
        "Han River Public Records Team",
        "Seoul Asset Verification Unit",
        "PrimeCare Contract Desk",
    ]
    subjects = [
        "Document inspection and archive service",
        "Insurance claim document review",
        "Medical equipment transport coverage",
        "Contract evidence verification service",
        "Official notice digitization project",
    ]
    signers = ["M. Han", "J. Park", "S. Lee", "H. Choi", "Y. Kim"]
    tampered_signers = ["D. Kim", "K. Yoon", "A. Shin", "P. Moon", "R. Jang"]

    start = date(2026, 1, 1) + timedelta(days=rng.randint(0, 260))
    due = start + timedelta(days=rng.randint(10, 35))
    base_amount = rng.randrange(8_000, 29_000, 100)
    fee_amount = rng.randrange(900, 4_800, 50)
    total_amount = base_amount + fee_amount
    tampered_amount = total_amount + rng.randrange(3_000, 18_000, 100)
    tampered_date = due + timedelta(days=rng.randint(5, 28))

    return ContractData(
        contract_no=f"DG-{start.year}-{rng.randint(1000, 9999)}-{rng.choice('ABCDEFGH')}{rng.randint(10, 99)}",
        seller=rng.choice(sellers),
        buyer=rng.choice(buyers),
        subject=rng.choice(subjects),
        effective_date=start.isoformat(),
        payment_due=due.isoformat(),
        base_amount=base_amount,
        fee_amount=fee_amount,
        total_amount=total_amount,
        signer=rng.choice(signers),
        tampered_date=tampered_date.isoformat(),
        tampered_amount=tampered_amount,
        tampered_signer=rng.choice(tampered_signers),
    )


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


def _draw_paper_texture(image: Image.Image, rng: random.Random) -> None:
    pixels = image.load()
    width, height = image.size
    offset = rng.randint(1, 99)
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            shade = 246 + ((x * 13 + y * 7 + offset) % 8)
            pixels[x, y] = (shade, shade - 1, shade - 6)


def _draw_header(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont], data: ContractData) -> None:
    draw.rectangle((70, 70, 1030, 190), outline="#1f2937", width=3)
    draw.text((95, 96), "SERVICE SUPPLY CONTRACT", fill="#111827", font=fonts["title"])
    draw.text((98, 157), f"Contract No. {data.contract_no}", fill="#475569", font=fonts["small"])
    draw.line((70, 230, 1030, 230), fill="#94a3b8", width=2)


def _draw_parties(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont], data: ContractData) -> None:
    rows = [
        ("Seller", data.seller),
        ("Buyer", data.buyer),
        ("Subject", data.subject),
        ("Effective Date", data.effective_date),
        ("Payment Due", data.payment_due),
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


def _draw_payment_table(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont], data: ContractData) -> None:
    x1, y1, x2, y2 = 95, 680, 1005, 920
    draw.rectangle((x1, y1, x2, y2), outline="#334155", width=2)
    draw.rectangle((x1, y1, x2, y1 + 58), fill="#e2e8f0", outline="#334155", width=2)

    headers = ["Item", "Date", "Amount", "Status"]
    xs = [120, 420, 660, 850]
    for x, header in zip(xs, headers):
        draw.text((x, y1 + 15), header, fill="#0f172a", font=fonts["section"])

    rows = [
        ("Base service", data.effective_date, _money(data.base_amount), "Approved"),
        ("Archive fee", data.payment_due, _money(data.fee_amount), "Approved"),
        ("Total due", data.payment_due, _money(data.total_amount), "Pending"),
    ]
    y = y1 + 78
    for row in rows:
        for x, value in zip(xs, row):
            draw.text((x, y), value, fill="#111827", font=fonts["body"])
        draw.line((x1, y + 47, x2, y + 47), fill="#cbd5e1", width=1)
        y += 68


def _draw_signature_area(draw: ImageDraw.ImageDraw, fonts: dict[str, ImageFont.ImageFont], data: ContractData) -> None:
    draw.line((95, 1110, 485, 1110), fill="#111827", width=2)
    draw.text((95, 1128), "Authorized Signature", fill="#64748b", font=fonts["small"])
    draw.text((125, 1044), data.signer, fill="#111827", font=fonts["signature"])
    draw.text((95, 1220), f"Signed on {data.effective_date}", fill="#111827", font=fonts["body"])

    draw.ellipse((745, 1030, 965, 1250), outline="#b91c1c", width=8)
    draw.ellipse((785, 1070, 925, 1210), outline="#b91c1c", width=4)
    draw.text((812, 1122), "APPROVED", fill="#b91c1c", font=fonts["body"])
    draw.text((810, 1160), "DOCUGUARD", fill="#b91c1c", font=fonts["small"])


def _tamper_date_amount_signature(
    image: Image.Image,
    fonts: dict[str, ImageFont.ImageFont],
    data: ContractData,
    rng: random.Random,
) -> None:
    jitter_x = rng.randint(-8, 8)
    jitter_y = rng.randint(-4, 4)
    _paste_compressed_patch(
        image,
        size=(210, 54),
        position=(410 + jitter_x, 888 + jitter_y),
        text=data.tampered_date,
        font=fonts["body"],
        fill="#111827",
        quality=rng.randint(12, 25),
        blur=rng.choice([0.4, 0.7, 1.0]),
        rng=rng,
    )
    _paste_compressed_patch(
        image,
        size=(190, 54),
        position=(650 + rng.randint(-8, 8), 888 + rng.randint(-4, 4)),
        text=_money(data.tampered_amount),
        font=fonts["body"],
        fill="#0f172a",
        quality=rng.randint(10, 22),
        sharpen=True,
        rng=rng,
    )
    _paste_compressed_patch(
        image,
        size=(235, 74),
        position=(105 + rng.randint(-10, 10), 1022 + rng.randint(-6, 6)),
        text=data.tampered_signer,
        font=fonts["signature"],
        fill="#111827",
        quality=rng.randint(10, 20),
        blur=rng.choice([0.2, 0.5, 0.8]),
        rng=rng,
    )


def _paste_compressed_patch(
    image: Image.Image,
    size: tuple[int, int],
    position: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
    quality: int,
    rng: random.Random,
    blur: float = 0.0,
    sharpen: bool = False,
) -> None:
    patch = Image.new("RGB", size, rng.choice(["#fff9e8", "#f8f0dc", "#fff7e2"]))
    patch_draw = ImageDraw.Draw(patch)

    line_a = rng.choice(["#e7dac1", "#e1d2b8", "#eadfc8"])
    line_b = rng.choice(["#f0e5cc", "#eadfc9", "#f4ead4"])
    for x in range(0, size[0], rng.randint(4, 7)):
        patch_draw.line((x, 0, x, size[1]), fill=line_a)
    for y in range(0, size[1], rng.randint(5, 8)):
        patch_draw.line((0, y, size[0], y), fill=line_b)
    for y in range(size[1]):
        for x in range(size[0]):
            if (x * rng.randint(13, 23) + y * rng.randint(23, 37)) % rng.randint(13, 21) == 0:
                patch_draw.point((x, y), fill=rng.choice(["#8f8068", "#b7a78d", "#ffffff"]))

    patch_draw.text((4 + rng.randint(0, 4), 2 + rng.randint(0, 3)), text, fill=fill, font=font)
    patch_draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline="#d1b98f", width=2)
    if blur:
        patch = patch.filter(ImageFilter.GaussianBlur(radius=blur))
    if sharpen:
        patch = patch.filter(ImageFilter.UnsharpMask(radius=1.5, percent=190, threshold=2))

    buffer = BytesIO()
    patch.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    image.paste(Image.open(buffer).convert("RGB"), position)


def _money(amount: int) -> str:
    return f"${amount:,.0f}"
