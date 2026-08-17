#!/usr/bin/env python3
"""
Проверяет собранные страницы: структуру разметки, метатеги, заголовки,
доступность, микроразметку и карту сайта.

Зачем этот файл существует. Раньше такие проверки я писал одноразовыми
скриптами вне проекта. Из-за этого на страницу портфолио уехал разрыв в
структуре заголовков — h1, а сразу за ним h3: проверка иерархии осталась в
другом, уже удалённом скрипте, а новая страница появилась после аудита и
полный набор проверок не проходила. Ошибку нашёл клиент, а не я. Теперь
проверки лежат в репозитории и запускаются после каждой сборки.

Запуск:  python3 tools/check-seo.py

Возвращает код 1, если нашлись ошибки, — значит результат нельзя публиковать.
Замечания на код выхода не влияют: это то, на что стоит посмотреть глазами.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site.json"

# Служебный файл подтверждения владения доменом — не наша страница.
IGNORE = {"googled3544b816083e618.html"}

# Страницы, закрытые от индексации: к ним не предъявляем требований по
# метатегам и объёму текста.
NOINDEX = {"privacy.html", "404.html"}

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}

TITLE_LIMITS = (30, 65)      # короче — недоиспользуем выдачу, длиннее — обрежется
DESCR_LIMITS = (70, 160)
MIN_WORDS = 300              # ниже этого страница для поиска «тонкая»
MIN_INLINKS = 3              # сколько внутренних ссылок должно вести на страницу


class Page(HTMLParser):
    """Разбирает страницу и складывает всё, что нужно проверкам."""

    def __init__(self, name: str):
        super().__init__(convert_charrefs=True)
        self.name = name
        self.title = ""
        self.meta: dict[str, str] = {}
        self.ids: Counter = Counter()
        self.aria_refs: list[tuple[str, str]] = []
        self.labels_for: list[str] = []
        self.fields: list[tuple[str, dict]] = []
        self.headings: list[int] = []
        self.imgs: list[dict] = []
        self.links: list[dict] = []
        self.ld: list[str] = []
        self.text: list[str] = []
        self.tag_errors: list[str] = []

        self._stack: list[tuple[str, int]] = []
        self._in_title = False
        self._in_ld = False
        self._in_heading = False
        self._mute = 0          # внутри script/style/svg текст не собираем
        self._hidden = 0        # глубина внутри aria-hidden
        self._in_label = 0      # поле внутри <label> подписано и без for

    # --- разбор -------------------------------------------------------------

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag not in VOID:
            self._stack.append((tag, self.getpos()[0]))
        if a.get("aria-hidden") == "true":
            self._hidden += 1

        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta[key] = a.get("content", "")
        elif tag == "link" and a.get("rel") == "canonical":
            self.meta["canonical"] = a.get("href", "")
        elif tag == "html":
            self.meta["lang"] = a.get("lang", "")
        elif tag == "a":
            self.links.append(a)
        elif tag == "img":
            self.imgs.append({**a, "decorative": self._hidden > 0})
        elif tag == "label":
            self._in_label += 1
            if "for" in a:
                self.labels_for.append(a["for"])
        elif tag in ("input", "textarea", "select"):
            self.fields.append((tag, {**a, "wrapped": self._in_label > 0}))
        elif re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
            self._in_heading = True
        elif tag in ("script", "style", "svg"):
            self._mute += 1
            if tag == "script" and a.get("type") == "application/ld+json":
                self._in_ld = True

        if "id" in a:
            self.ids[a["id"]] += 1
        for key in ("aria-labelledby", "aria-describedby", "aria-controls"):
            if key in a:
                self.aria_refs += [(key, tok) for tok in a[key].split()]

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "label":
            self._in_label = max(0, self._in_label - 1)
        elif re.fullmatch(r"h[1-6]", tag):
            self._in_heading = False
        elif tag in ("script", "style", "svg"):
            self._mute = max(0, self._mute - 1)
            self._in_ld = False

        if tag in VOID:
            return
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                for unclosed, line in self._stack[i + 1:]:
                    self.tag_errors.append(f"не закрыт <{unclosed}>, строка {line}")
                del self._stack[i:]
                if self._hidden:
                    self._hidden -= 1
                return
        self.tag_errors.append(f"закрывающий </{tag}> без открывающего, строка {self.getpos()[0]}")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._in_ld:
            self.ld.append(data)
        elif not self._mute and not self._in_heading:
            self.text.append(data)

    def finish(self):
        for tag, line in self._stack:
            self.tag_errors.append(f"не закрыт <{tag}>, строка {line}")
        return self


# --------------------------------------------------------------------- отчёт

errors: dict[str, list[str]] = defaultdict(list)
warnings: dict[str, list[str]] = defaultdict(list)


def err(page: str, msg: str) -> None:
    errors[page].append(msg)


def warn(page: str, msg: str) -> None:
    warnings[page].append(msg)


# ------------------------------------------------------------------ проверки


def schema_types(page: Page, name: str) -> list[str]:
    """Типы из микроразметки. Понимает и @graph, где узлы вложены в список."""
    types: list[str] = []
    for block in page.ld:
        try:
            data = json.loads(block)
        except json.JSONDecodeError as e:
            err(name, f"микроразметка: невалидный JSON — {e}")
            continue
        for node in (data if isinstance(data, list) else [data]):
            if "@graph" in node:
                if "@context" not in node:
                    err(name, "микроразметка: у @graph нет @context")
                nodes = node["@graph"]
            else:
                if "@context" not in node:
                    err(name, f"микроразметка: у {node.get('@type')} нет @context")
                nodes = [node]
            for n in nodes:
                types.append(n.get("@type"))
                if n.get("@type") == "FAQPage" and not n.get("mainEntity"):
                    err(name, "микроразметка: FAQPage без вопросов")
                if n.get("@type") == "BreadcrumbList":
                    items = n.get("itemListElement", [])
                    for it in items[:-1]:
                        if "item" not in it:
                            err(name, f"микроразметка: крошка без ссылки — {it.get('name')}")
    return types


def check_page(page: Page, name: str, origin: str) -> None:
    for msg in page.tag_errors:
        err(name, f"разметка: {msg}")

    if page.meta.get("lang") != "ru":
        err(name, "разметка: у <html> не указан lang=ru")
    if not page.meta.get("viewport"):
        err(name, "разметка: нет метатега viewport")

    for i, n in page.ids.items():
        if n > 1:
            err(name, f"разметка: id «{i}» встречается {n} раза")
    for key, tok in page.aria_refs:
        if tok not in page.ids:
            err(name, f"доступность: {key} ссылается на несуществующий id «{tok}»")
    for f in page.labels_for:
        if f not in page.ids:
            err(name, f"формы: <label for=«{f}»> без такого поля")
    for tag, a in page.fields:
        if a.get("type") in ("hidden", "submit", "button"):
            continue
        labelled = (a.get("wrapped")
                    or a.get("id") in page.labels_for
                    or a.get("aria-label")
                    or a.get("aria-labelledby"))
        if not labelled:
            err(name, f"формы: <{tag} name={a.get('name')}> без подписи")

    # Заголовки: ровно один h1 и без разрывов уровней.
    if page.headings.count(1) != 1:
        err(name, f"заголовки: h1 на странице {page.headings.count(1)} шт., должен быть один")
    for prev, cur in zip(page.headings, page.headings[1:]):
        if cur > prev + 1:
            err(name, f"заголовки: разрыв структуры — h{prev}, а следом сразу h{cur}")

    # Картинки. Пустой alt у декоративной картинки — это норма, а вот
    # отсутствие атрибута и отсутствие размеров — нет.
    for a in page.imgs:
        src = (a.get("src") or "?").split("/")[-1]
        if "alt" not in a:
            err(name, f"картинки: нет атрибута alt — {src}")
        elif not a["alt"].strip() and not a["decorative"]:
            warn(name, f"картинки: пустой alt вне декоративного блока — {src}")
        if not (a.get("width") and a.get("height")):
            err(name, f"картинки: нет width/height, вёрстка прыгнет при загрузке — {src}")

    for a in page.links:
        href = a.get("href", "")
        if a.get("target") == "_blank" and "noopener" not in a.get("rel", ""):
            err(name, f"ссылки: target=_blank без rel=noopener — {href}")
        if href in ("", "#"):
            err(name, "ссылки: пустой href")

    types = schema_types(page, name)

    if name in NOINDEX:
        if page.meta.get("robots", "").find("noindex") < 0:
            warn(name, "страница задумана закрытой от индексации, но noindex не стоит")
        return

    title = " ".join(page.title.split())
    descr = " ".join(page.meta.get("description", "").split())
    lo, hi = TITLE_LIMITS
    if not title:
        err(name, "метатеги: нет заголовка страницы")
    elif len(title) > hi:
        err(name, f"метатеги: title {len(title)} симв. — в выдаче обрежется (до {hi})")
    elif len(title) < lo:
        warn(name, f"метатеги: title короткий, {len(title)} симв.")

    lo, hi = DESCR_LIMITS
    if not descr:
        err(name, "метатеги: нет description")
    elif len(descr) > hi:
        err(name, f"метатеги: description {len(descr)} симв. — обрежется (до {hi})")
    elif len(descr) < lo:
        warn(name, f"метатеги: description короткий, {len(descr)} симв.")

    canon = page.meta.get("canonical", "")
    expected = origin + "/" if name == "index.html" else f"{origin}/{name}"
    if not canon:
        err(name, "метатеги: нет canonical")
    elif canon != expected:
        err(name, f"метатеги: canonical ведёт не на себя — {canon}, ожидался {expected}")

    for key in ("og:title", "og:description", "og:image", "og:url"):
        if not page.meta.get(key):
            err(name, f"соцсети: нет {key}")

    if "BreadcrumbList" not in types and name != "index.html":
        warn(name, "микроразметка: нет хлебных крошек")

    words = len(" ".join(page.text).split())
    if words < MIN_WORDS:
        warn(name, f"контент: {words} слов — для поиска это тонкая страница")


# --------------------------------------------------------------------- запуск


def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    origin = data["site"]["origin"]

    pages: dict[str, Page] = {}
    for path in sorted(ROOT.glob("*.html")):
        if path.name in IGNORE:
            continue
        pages[path.name] = Page(path.name)
        pages[path.name].feed(path.read_text(encoding="utf-8"))
        pages[path.name].finish()

    if not pages:
        print("Страниц не найдено. Сначала запустите tools/build-site.py", file=sys.stderr)
        return 1

    for name, page in pages.items():
        check_page(page, name, origin)

    # Одинаковые метатеги на разных страницах — поиск считает их дублями.
    for label, values in (
        ("title", {n: " ".join(p.title.split()) for n, p in pages.items() if n not in NOINDEX}),
        ("description", {n: p.meta.get("description", "") for n, p in pages.items() if n not in NOINDEX}),
    ):
        seen: dict[str, list[str]] = defaultdict(list)
        for n, v in values.items():
            if v:
                seen[v].append(n)
        for v, names in seen.items():
            if len(names) > 1:
                err(names[0], f"метатеги: одинаковый {label} с {', '.join(names[1:])}")

    # Перелинковка: на каждую страницу должно вести несколько внутренних ссылок.
    incoming: Counter = Counter()
    for page in pages.values():
        for a in page.links:
            href = a.get("href", "")
            if href.startswith(("http", "tel:", "mailto:", "#")):
                continue
            target = href.split("#")[0].lstrip("/")
            if target.endswith(".html"):
                incoming[target] += 1
    for name in pages:
        if name in NOINDEX or name == "index.html":
            continue
        if incoming[name] < MIN_INLINKS:
            warn(name, f"перелинковка: всего {incoming[name]} внутренних ссылок на страницу")

    # Карта сайта: все открытые страницы должны быть в ней, и наоборот.
    sitemap = ROOT / "sitemap.xml"
    if sitemap.exists():
        locs = {u.rsplit("/", 1)[-1] or "index.html"
                for u in re.findall(r"<loc>([^<]+)</loc>", sitemap.read_text(encoding="utf-8"))}
        for name in pages:
            if name in NOINDEX:
                if name in locs:
                    err(name, "карта сайта: закрытая от индексации страница попала в sitemap.xml")
            elif name not in locs:
                err(name, "карта сайта: страницы нет в sitemap.xml")
        for loc in locs - set(pages):
            err("sitemap.xml", f"карта сайта: адрес без страницы — {loc}")

    # ---- вывод
    print(f"Проверено страниц: {len(pages)}\n")
    n_err = sum(len(v) for v in errors.values())
    n_warn = sum(len(v) for v in warnings.values())

    for title, bag in (("ОШИБКИ", errors), ("замечания", warnings)):
        if not bag:
            continue
        print(f"── {title}")
        for name in sorted(bag):
            for msg in bag[name]:
                print(f"   {name:<18} {msg}")
        print()

    if n_err:
        print(f"Ошибок: {n_err}. Публиковать нельзя, пока не исправлены.")
    elif n_warn:
        print(f"Ошибок нет. Замечаний: {n_warn} — посмотрите глазами, но это не блокирует.")
    else:
        print("Ошибок и замечаний нет.")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
