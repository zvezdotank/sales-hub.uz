#!/usr/bin/env python3
"""
Проверяет собранные страницы: битые ссылки, несуществующие якоря,
незаменённые шаблонные теги.

Запуск:  python3 tools/check-links.py
Код возврата 1, если что-то найдено — удобно для CI.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTERNAL = ("http://", "https://", "mailto:", "tel:", "data:", "//")


def main() -> int:
    pages = sorted(ROOT.glob("*.html"))
    if not pages:
        print("Нет собранных .html — сначала запустите tools/build-site.py", file=sys.stderr)
        return 1

    problems: list[str] = []

    for page in pages:
        text = page.read_text(encoding="utf-8")

        for leftover in re.findall(r"\{\{[^}]*\}\}", text):
            problems.append(f"{page.name}: незаменённый тег {leftover}")

        for ref in re.findall(r'(?:href|src|srcset)="([^"]+)"', text):
            if ref.startswith(EXTERNAL):
                continue

            path, _, fragment = ref.partition("#")
            path = path.split("?")[0]

            # Ведущий слэш — корень сайта, а не корень файловой системы.
            # 404.html использует абсолютные пути: она отдаётся по любому
            # адресу, в том числе вложенному.
            if path.startswith("/"):
                path = path.lstrip("/") or "index.html"

            if path:
                target = ROOT / path
                if not target.exists():
                    problems.append(f"{page.name}: нет файла → {path}")
                elif fragment and target.suffix == ".html":
                    if f'id="{fragment}"' not in target.read_text(encoding="utf-8"):
                        problems.append(f"{page.name}: в {path} нет якоря #{fragment}")
            elif fragment and f'id="{fragment}"' not in text:
                problems.append(f"{page.name}: якорь #{fragment} никуда не ведёт")

    print(f"Проверено страниц: {len(pages)}")
    if problems:
        print(f"Проблем: {len(problems)}")
        for item in sorted(set(problems)):
            print("  ✗", item)
        return 1

    print("✓ Битых ссылок, якорей и незаменённых тегов нет.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
