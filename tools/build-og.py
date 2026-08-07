#!/usr/bin/env python3
"""
Генерирует og-картинку 1200x630 для превью ссылок в соцсетях и мессенджерах.

Запуск:  python3 tools/build-og.py
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "img" / "_src" / "hero-rover.jpg"
OUT_DIR = ROOT / "assets" / "og"

W, H = 1200, 630
ACCENT = (255, 181, 71)
ACCENT_2 = (255, 122, 61)
TEXT = (232, 237, 244)
DIM = (163, 177, 198)

FONTS = {
    "bold": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "regular": "/System/Library/Fonts/Supplemental/Arial.ttf",
    "mono": "/System/Library/Fonts/Menlo.ttc",
}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONTS[kind], size)
    except OSError:
        return ImageFont.load_default()


def main() -> int:
    if not SRC.exists():
        print(f"Нет исходника: {SRC}", file=sys.stderr)
        return 1

    # Кадрируем фон по центру под 1200x630
    with Image.open(SRC) as im:
        im = im.convert("RGB")
        scale = max(W / im.width, H / im.height)
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        left = (im.width - W) // 2
        top = (im.height - H) // 2
        bg = im.crop((left, top, left + W, top + H))

    bg = bg.filter(ImageFilter.GaussianBlur(1.2))

    # Затемняющий градиент слева направо — текст ложится на плотную часть
    overlay = Image.new("RGBA", (W, H))
    od = ImageDraw.Draw(overlay)
    for x in range(W):
        t = x / W
        alpha = int(242 - 150 * min(t / 0.72, 1.0))
        od.line([(x, 0), (x, H)], fill=(5, 7, 12, max(alpha, 78)))
    canvas = Image.alpha_composite(bg.convert("RGBA"), overlay)

    d = ImageDraw.Draw(canvas)

    # Орбитальная марка
    cx, cy = 74, 74
    d.ellipse([cx - 21, cy - 21, cx + 21, cy + 21], outline=ACCENT, width=3)
    d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=ACCENT)

    d.text((112, 58), "SALES", font=font("bold", 27), fill=TEXT)
    d.text((196, 58), "HUB", font=font("bold", 27), fill=ACCENT)

    # Заголовок
    d.text((72, 214), "Выводим ваш бизнес", font=font("bold", 68), fill=TEXT)
    d.text((72, 292), "на орбиту роста", font=font("bold", 68), fill=TEXT)

    # Подзаголовок
    d.text(
        (72, 396),
        "Агентство интернет-рекламы полного цикла",
        font=font("regular", 29),
        fill=DIM,
    )

    # Акцентная линия
    d.rounded_rectangle([72, 452, 232, 458], radius=3, fill=ACCENT_2)

    # Нижняя строка
    d.text((72, 512), "PPC · SEO · SMM · TELEGRAM ADS · АНАЛИТИКА", font=font("mono", 21), fill=ACCENT)
    d.text((72, 552), "sales-hub.uz  ·  Ташкент, Узбекистан", font=font("mono", 21), fill=DIM)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "og-default.jpg"
    canvas.convert("RGB").save(out, format="JPEG", quality=86, optimize=True, progressive=True)
    print(f"  ✓ {out.relative_to(ROOT)}  {W}x{H}  {out.stat().st_size // 1024} КБ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
