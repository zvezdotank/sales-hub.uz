#!/usr/bin/env python3
"""
Скачивает шрифты с Google Fonts и раскладывает их локально.

Зачем локально, а не ссылкой на Google:
  • два лишних домена в критическом пути загрузки (googleapis + gstatic),
    каждый со своим DNS и TLS-рукопожатием;
  • сайт перестаёт зависеть от доступности Google;
  • Google не получает данные о каждом посетителе.

Наборы символов ограничены латиницей и кириллицей — греческий и вьетнамский
на сайте не нужны и только утяжелили бы загрузку.

Запуск:  python3 tools/build-fonts.py
"""

from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "fonts"
CSS_OUT = ROOT / "css" / "fonts.css"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Что качаем. Michroma остаётся: она нужна только для латиницы и цифр
# (логотип, счётчики, названия клиентов) — кириллицы там нет.
FONTS = [
    ("Manrope", "Manrope:wght@400..700", "manrope"),
    ("JetBrains Mono", "JetBrains+Mono:wght@400..500", "jetbrains-mono"),
    ("Michroma", "Michroma", "michroma"),
]

# Нужные наборы символов определяем по характерным точкам диапазонов.
WANTED = {
    "latin": "U+0000-00FF",
    "latin-ext": "U+0100-02BA",
    "cyrillic": "U+0400-045F",
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def subset_name(unicode_range: str) -> str | None:
    for name, marker in WANTED.items():
        if marker in unicode_range:
            return name
    return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    blocks: list[str] = []
    total = 0

    for family, query, slug in FONTS:
        css = fetch(f"https://fonts.googleapis.com/css2?family={query}&display=swap")
        faces = re.findall(r"@font-face\s*\{(.*?)\}", css, re.S)
        print(f"{family}: получено начертаний — {len(faces)}")

        for face in faces:
            rng = re.search(r"unicode-range:\s*([^;]+);", face)
            url = re.search(r"url\((https://[^)]+\.woff2)\)", face)
            weight = re.search(r"font-weight:\s*([^;]+);", face)
            style = re.search(r"font-style:\s*([^;]+);", face)
            if not rng or not url:
                continue

            subset = subset_name(rng.group(1))
            if subset is None:
                continue  # греческий, вьетнамский и прочее — пропускаем

            w = (weight.group(1) if weight else "400").strip()
            s = (style.group(1) if style else "normal").strip()
            filename = f"{slug}-{subset}-{w.replace(' ', '_')}.woff2"
            dst = OUT / filename

            if not dst.exists():
                req = urllib.request.Request(url.group(1), headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=30) as r:
                    dst.write_bytes(r.read())
            size = dst.stat().st_size
            total += size
            print(f"    → {filename:44s} {size // 1024:>3} КБ")

            blocks.append(
                "@font-face {\n"
                f"  font-family: '{family}';\n"
                f"  font-style: {s};\n"
                f"  font-weight: {w};\n"
                "  font-display: swap;\n"
                f"  src: url('../assets/fonts/{filename}') format('woff2');\n"
                f"  unicode-range: {rng.group(1).strip()};\n"
                "}"
            )

    header = (
        "/* Шрифты с собственного домена.\n"
        "   Сгенерировано tools/build-fonts.py — не редактируйте вручную.\n"
        "   Только латиница и кириллица: остальные наборы на сайте не нужны. */\n\n"
    )
    CSS_OUT.write_text(header + "\n\n".join(blocks) + "\n", encoding="utf-8")

    print(f"\nВсего: {total // 1024} КБ в {len(blocks)} файлах")
    print(f"CSS: {CSS_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
