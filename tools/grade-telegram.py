#!/usr/bin/env python3
"""
Приводит дневное фото антенны к ночной палитре остальных изображений сайта.

Исходник — единственная светлая документальная фотография среди тёмных
кинематографичных рендеров: голубое небо, белое солнце в зените. Скрипт делает
классический day-for-night: гасит небо до глубокого сине-фиолетового, оставляет
солнце тёплым источником света и подмешивает янтарь в света на земле.

Запуск:  python3 tools/grade-telegram.py
Результат: assets/img/_src/service-telegram-night.jpg
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "img" / "_src" / "service-telegram.jpg"
DST = ROOT / "assets" / "img" / "_src" / "service-telegram-night.jpg"

# Палитра сайта
SKY_DEEP = np.array([16, 21, 46], dtype=np.float32)     # зенит, глубокий синий
SKY_LOW = np.array([58, 60, 98], dtype=np.float32)      # у горизонта, чуть светлее
GROUND_TINT = np.array([46, 40, 44], dtype=np.float32)  # холодная земля
WARM = np.array([255, 181, 71], dtype=np.float32)       # --accent


def main() -> int:
    if not SRC.exists():
        print(f"Нет исходника: {SRC}", file=sys.stderr)
        return 1

    img = Image.open(SRC).convert("RGB")
    a = np.asarray(img).astype(np.float32) / 255.0
    h, w, _ = a.shape

    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b

    # --- маска неба: синева заметно выше красного, и пиксель светлый -------
    blueness = np.clip((b - r) * 3.2, 0, 1)
    sky = np.clip(blueness * np.clip((lum - 0.22) * 2.2, 0, 1), 0, 1)
    sky = np.asarray(
        Image.fromarray((sky * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)),
        dtype=np.float32,
    ) / 255.0

    # --- положение источника света: центр самого яркого пятна ---------------
    core = (lum > 0.92).astype(np.float32)
    if core.sum() > 0:
        ys, xs = np.nonzero(core)
        sun_y, sun_x = float(ys.mean()), float(xs.mean())
    else:
        sun_y, sun_x = h * 0.27, w * 0.65

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dist = np.sqrt((xx - sun_x) ** 2 + (yy - sun_y) ** 2)
    diag = np.sqrt(h * h + w * w)

    # --- база: гасим и обесцвечиваем ---------------------------------------
    grey = lum[..., None]
    out = (grey * 0.80 + a * 0.20) * 255.0          # почти монохром
    out = out * 0.46                                 # общее затемнение
    out += GROUND_TINT * np.clip(lum[..., None], 0, 1) * 0.62

    # --- небо: вертикальный градиент от зенита к горизонту ------------------
    grad = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    sky_col = SKY_DEEP + (SKY_LOW - SKY_DEEP) * grad
    # сохраняем немного исходной структуры (перистые облака, инверсионные следы)
    detail = np.clip((lum[..., None] - 0.55) * 1.6, 0, 1) * 22.0
    s = sky[..., None]
    out = out * (1 - s) + (sky_col + detail) * s

    # --- направленный свет: обращённые к источнику поверхности теплеют ------
    falloff = np.clip(1.0 - dist / (diag * 0.62), 0, 1) ** 1.8
    lit = (falloff * np.clip((lum - 0.30) * 1.7, 0, 1))[..., None] * (1 - s)
    out += WARM * lit * 1.15

    # --- тёплое зарево вокруг источника, включая небо -----------------------
    glow = np.clip(1.0 - dist / (diag * 0.30), 0, 1) ** 2.6
    out += WARM * glow[..., None] * 0.72

    # --- ядро источника: тёплое, не белое ----------------------------------
    disc = np.clip(1.0 - dist / 46.0, 0, 1) ** 0.75
    disc = np.asarray(
        Image.fromarray((disc * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(7)),
        dtype=np.float32,
    ) / 255.0
    d3 = disc[..., None]
    out = out * (1 - d3) + (WARM * 0.92 + 40.0) * d3

    out = np.clip(out, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(DST, quality=94, subsampling=0)

    print(f"  ✓ {DST.relative_to(ROOT)}  {img.width}x{img.height}  {DST.stat().st_size // 1024} КБ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
