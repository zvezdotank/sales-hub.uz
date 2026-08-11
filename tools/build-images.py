#!/usr/bin/env python3
"""
Пересобирает адаптивные изображения из оригиналов в assets/img/_src.

Для каждого исходника генерирует AVIF + WebP в тех размерах, в которых
картинка реально используется на сайте (карточка, баннер, hero-фон).
Оригиналы в _src остаются нетронутыми — их можно перегенерировать заново.

Запуск:  python3 tools/build-images.py
"""

import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "img" / "_src"
OUT = ROOT / "assets" / "img"

# Ширины под конкретные места вёрстки (с запасом на 2x-экраны).
PRESETS = {
    "card": 800,     # карточка услуги, высота 160px
    "banner": 1400,  # process-banner, высота 280px
    "photo": 900,    # why-photo
    "hero": 1920,    # полноэкранный фон hero / page-hero
    "bg": 1200,      # декоративный фон секции контактов
}

# Какие размеры нужны каждому исходнику.
PLAN = {
    "hero-rover":            ["hero"],
    "service-context":       ["card", "hero"],
    "service-seo":           ["card", "hero"],
    # Только card: шапку страницы SMM рисует другой кадр, service-smm-cabin.
    # Пока здесь стоял и "hero", скрипт исправно генерировал самый тяжёлый
    # файл в репозитории (157 КБ), на который никто не ссылался.
    "service-smm":           ["card"],
    "service-smm-cabin":     ["hero"],
    "service-webdev":        ["card", "hero"],
    "service-analytics":     ["card", "hero"],
    "service-adaccess":      ["card", "hero"],
    "service-telegram-night": ["card", "hero"],  # см. tools/grade-telegram.py
    "process-missioncontrol": ["card", "banner", "hero"],
    "why-earthnight":        ["photo"],
    "contact-mars":          ["bg"],
}

QUALITY = {"avif": 55, "webp": 74}

# Эти картинки в вёрстке сильно затемнены и/или лежат под маской — качество
# на них всё равно не читается, поэтому жмём заметно сильнее.
QUALITY_OVERRIDE = {
    "bg": {"avif": 32, "webp": 50},
    "banner": {"avif": 42, "webp": 62},
}


def resize(img: Image.Image, target_w: int) -> Image.Image:
    """Ужимает до целевой ширины. Апскейл не делаем — только уменьшение."""
    if img.width <= target_w:
        return img.copy()
    h = round(img.height * target_w / img.width)
    return img.resize((target_w, h), Image.LANCZOS)


def main() -> int:
    if not SRC.is_dir():
        print(f"Нет папки с оригиналами: {SRC}", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict[str, list[int]]] = {}
    total = 0

    for stem, presets in sorted(PLAN.items()):
        src_path = SRC / f"{stem}.jpg"
        if not src_path.exists():
            print(f"  ! пропуск {stem}: нет {src_path.name}", file=sys.stderr)
            continue

        with Image.open(src_path) as im:
            im = im.convert("RGB")
            print(f"{stem}.jpg  {im.width}x{im.height}  {src_path.stat().st_size // 1024} КБ")

            for preset in presets:
                out = resize(im, PRESETS[preset])
                manifest.setdefault(stem, {})[preset] = [out.width, out.height]

                quality = QUALITY_OVERRIDE.get(preset, QUALITY)
                for fmt in ("avif", "webp"):
                    dst = OUT / f"{stem}-{preset}.{fmt}"
                    out.save(dst, format=fmt.upper(), quality=quality[fmt])
                    size = dst.stat().st_size
                    total += size
                    print(f"    → {dst.name:38s} {out.width}x{out.height}  {size // 1024} КБ")

    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"\nИтого сгенерировано: {total // 1024} КБ")
    print(f"Размеры записаны в {OUT.relative_to(ROOT)}/manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
