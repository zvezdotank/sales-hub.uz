#!/usr/bin/env python3
"""
Вырезает из кадра героя светящиеся тёплые области — свет изнутри модуля.

Слой накладывается поверх исходной фотографии тем же <img> с теми же
object-fit / object-position, поэтому совмещается идеально при любом размере
экрана. Режим наложения screen плюс анимация прозрачности дают пульсацию
свечения без подгонки координат под каждый брейкпоинт.

Запуск:  python3 tools/build-hero-glow.py
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "img" / "_src" / "hero-rover.jpg"
OUT = ROOT / "assets" / "img"
WIDTH = 1920


def main() -> int:
    if not SRC.exists():
        print(f"Нет исходника: {SRC}", file=sys.stderr)
        return 1

    img = Image.open(SRC).convert("RGB")
    if img.width > WIDTH:
        h = round(img.height * WIDTH / img.width)
        img = img.resize((WIDTH, h), Image.LANCZOS)

    a = np.asarray(img).astype(np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b

    # Свечение = яркий И тёплый пиксель. Холодные блики на корпусе и звёзды
    # отсекаются по разнице красного и синего.
    warmth = np.clip((r - b) * 2.6, 0, 1)
    bright = np.clip((lum - 0.34) * 2.4, 0, 1)
    mask = np.clip(warmth * bright, 0, 1) ** 1.15

    # Ореол вокруг источника: свет не обрывается по кромке люка.
    soft = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(9))
    mask = np.maximum(mask, np.asarray(soft, dtype=np.float32) / 255.0 * 0.75)

    # Цвет берём из самого кадра, слегка усиливая насыщенность свечения.
    glow = a * mask[..., None]
    glow[..., 0] *= 1.12
    glow[..., 1] *= 0.96
    glow[..., 2] *= 0.72

    rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
    rgba[..., :3] = np.clip(glow * 255, 0, 255).astype(np.uint8)
    rgba[..., 3] = np.clip(mask * 255, 0, 255).astype(np.uint8)

    out = Image.fromarray(rgba)
    total = 0
    for fmt, quality in (("webp", 72), ("avif", 55)):
        dst = OUT / f"hero-rover-glow.{fmt}"
        out.save(dst, format=fmt.upper(), quality=quality)
        total += dst.stat().st_size
        print(f"  ✓ {dst.name:26s} {out.width}x{out.height}  {dst.stat().st_size // 1024} КБ")

    covered = (mask > 0.05).mean() * 100
    print(f"\nСветящаяся площадь: {covered:.1f}% кадра, слой весит {total // 1024} КБ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
