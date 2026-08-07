#!/usr/bin/env python3
"""
Собирает статические HTML-страницы из site.json и templates/.

Зачем: шапка, подвал и блок контактов раньше были скопированы в каждый файл —
смена телефона требовала правок в девяти местах. Теперь данные лежат в
site.json, разметка — в templates/, а .html в корне собираются заново.

Запуск:  python3 tools/build-site.py
"""

import html
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "templates"
DATA = ROOT / "site.json"


# ---------------------------------------------------------------- шаблонизатор

TAG = re.compile(r"\{\{\s*([#?^/>&]?)\s*([\w.-]*)\s*\}\}")


def render(tpl: str, ctx: dict, depth: int = 0) -> str:
    """Мини-движок в духе mustache.

    {{ x }}   — значение с экранированием
    {{& x }}  — значение как есть (готовый HTML)
    {{> p }}  — вставить templates/p.html
    {{# x }}…{{/ x }} — цикл по списку либо блок с областью видимости словаря
    {{? x }}…{{/ x }} — если значение истинно
    {{^ x }}…{{/ x }} — если значение ложно
    """
    if depth > 12:
        raise RecursionError("слишком глубокая вложенность шаблонов")

    out = []
    pos = 0
    while True:
        m = TAG.search(tpl, pos)
        if not m:
            out.append(tpl[pos:])
            break

        out.append(tpl[pos : m.start()])
        sigil, name = m.group(1), m.group(2)

        if sigil in ("#", "?", "^"):
            body, pos = _block(tpl, name, m.end())
            value = lookup(ctx, name)

            if sigil == "^":
                if not value:
                    out.append(render(body, ctx, depth + 1))
            elif sigil == "?":
                if value:
                    out.append(render(body, ctx, depth + 1))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    scope = dict(ctx)
                    if isinstance(item, dict):
                        scope.update(item)
                    scope["."] = item
                    scope["index"] = i + 1
                    scope["index0"] = i
                    scope["index2"] = f"{i + 1:02d}"
                    scope["first"] = i == 0
                    scope["last"] = i == len(value) - 1
                    out.append(render(body, scope, depth + 1))
            elif isinstance(value, dict):
                scope = dict(ctx)
                scope.update(value)
                out.append(render(body, scope, depth + 1))
            elif value:
                out.append(render(body, ctx, depth + 1))
            continue

        if sigil == ">":
            part = (TPL / f"{name}.html").read_text(encoding="utf-8")
            out.append(render(part, ctx, depth + 1))
        elif sigil == "&":
            out.append(str(lookup(ctx, name) or ""))
        else:
            out.append(html.escape(str(lookup(ctx, name) or ""), quote=True))

        pos = m.end()

    return "".join(out)


def _block(tpl: str, name: str, start: int) -> tuple[str, int]:
    """Возвращает тело блока {{# name}}…{{/ name}} с учётом вложенности."""
    level, pos = 1, start
    while True:
        m = TAG.search(tpl, pos)
        if not m:
            raise SyntaxError(f"не закрыт блок {{{{# {name} }}}}")
        if m.group(2) == name:
            if m.group(1) in ("#", "?", "^"):
                level += 1
            elif m.group(1) == "/":
                level -= 1
                if level == 0:
                    return tpl[start : m.start()], m.end()
        pos = m.end()


def lookup(ctx: dict, path: str):
    if path == ".":
        return ctx.get(".")
    cur = ctx
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


# ---------------------------------------------------------------------- иконки

ICONS = {
    "rocket": "M3 11l18-8-8 18-2-8-8-2z",
    "pin": "M12 2a7 7 0 00-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 00-7-7zm0 9.5A2.5 2.5 0 1112 6a2.5 2.5 0 010 5.5z",
    "users": "M12 12c2.7 0 8 1.3 8 4v2H4v-2c0-2.7 5.3-4 8-4zm0-2a4 4 0 100-8 4 4 0 000 8z",
    "monitor": "M4 4h16v12H4zM2 20h20v-2H2z",
    "target": "M9.5 3a6.5 6.5 0 015.13 10.5l5.44 5.44-1.42 1.42-5.44-5.44A6.5 6.5 0 119.5 3zm0 2a4.5 4.5 0 100 9 4.5 4.5 0 000-9z",
    "bars": "M4 20V10h4v10H4zm6 0V4h4v16h-4zm6 0v-7h4v7h-4z",
    "lock": "M12 2a5 5 0 00-5 5v3H6a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2v-8a2 2 0 00-2-2h-1V7a5 5 0 00-5-5zm0 2a3 3 0 013 3v3H9V7a3 3 0 013-3zm0 10a2 2 0 110 4 2 2 0 010-4z",
    "send": "M21 4L2.5 11.4c-1.2.5-1.2 1.2-.2 1.5l4.8 1.5 1.8 5.6c.2.6.4.8.9.8.4 0 .6-.2.9-.5l2.1-2 4.4 3.2c.8.5 1.4.2 1.6-.7l3-14c.3-1.2-.4-1.7-1.4-1.3zM7.9 13.7l9-5.6c.4-.3.8-.1.5.2l-7.6 6.9-.3 3.2-1.6-4.7z",
    "play": "M8 5v14l11-7z",
    "spark": "M12 2l2.3 4.6L19 8l-3.5 3.4.8 4.8L12 14l-4.3 2.2.8-4.8L5 8l4.7-1.4z",
}


def icon(name: str, size: int = 24) -> str:
    return (
        f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" aria-hidden="true" focusable="false">'
        f'<path fill="currentColor" d="{ICONS[name]}"/></svg>'
    )


# ------------------------------------------------------------ логотипы клиентов
# Абстрактные монохромные марки в одной оптической сетке 32x32 — не репродукции
# товарных знаков. Заменяются на официальные SVG, когда клиенты их предоставят.

CLIENT_MARKS = {
    "hex": '<path fill="none" stroke="currentColor" stroke-width="1.6" d="M16 3l11 6.5v13L16 29 5 22.5v-13z"/><circle cx="16" cy="16" r="4" fill="currentColor"/>',
    "cross": '<path fill="none" stroke="currentColor" stroke-width="1.6" d="M16 4a12 12 0 110 24 12 12 0 010-24z"/><path fill="currentColor" d="M14.4 9h3.2v5.4H23v3.2h-5.4V23h-3.2v-5.4H9v-3.2h5.4z"/>',
    "drop": '<path fill="none" stroke="currentColor" stroke-width="1.6" d="M16 3.5c5 6.3 8 10.6 8 14a8 8 0 11-16 0c0-3.4 3-7.7 8-14z"/><path fill="currentColor" d="M16 12.5c2.4 3 3.6 5 3.6 6.4a3.6 3.6 0 11-7.2 0c0-1.4 1.2-3.4 3.6-6.4z"/>',
    "flame": '<path fill="none" stroke="currentColor" stroke-width="1.6" d="M16 3c1.5 5.2 7 7.4 7 13.2A7 7 0 0116 23a7 7 0 01-7-6.8C9 10.4 14.5 8.2 16 3z"/><path fill="currentColor" d="M16 13.5c.8 2.6 3 3.6 3 6a3 3 0 11-6 0c0-2.4 2.2-3.4 3-6z"/><path fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" d="M11 26h10"/>',
    # Растаможка — таможенное оформление. Грузовой контейнер с печатью:
    # та же геометрическая простота, что и у соседних марок.
    "container": (
        '<path fill="none" stroke="currentColor" stroke-width="1.7" d="M4.5 10h23v13.5h-23z"/>'
        '<path fill="none" stroke="currentColor" stroke-width="1.3" d="M11 10v13.5M21 10v13.5"/>'
        '<circle cx="16" cy="16.75" r="3" fill="currentColor"/>'
        '<path fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" d="M7 26.5h18"/>'
    ),
    # Picasso — арт-студия. Собственная марка: палитра с отверстием и мазком
    # кисти. Держит ту же геометрическую простоту, что и соседние марки, —
    # детальный линейный профиль в 30px превращался в неразборчивый росчерк.
    "picasso": (
        '<path fill="none" stroke="currentColor" stroke-width="1.7" '
        'd="M16 5.5c6.1 0 11 4.2 11 9.4 0 3.1-2.2 4.6-4.3 4.6h-2.3c-1.5 0-2.6 1.1-2.6 2.5 0 .7.3 1.2.6 1.7.3.5.5.9.5 1.5 0 1.2-1 2.3-2.6 2.3-5.9 0-11-5.1-11-11.4S9.9 5.5 16 5.5z"/>'
        '<circle cx="11.4" cy="12.2" r="1.9" fill="currentColor"/>'
        '<circle cx="19.4" cy="10.6" r="1.9" fill="currentColor"/>'
    ),
}

CLIENTS = [
    {"name": "Gedeon Richter", "mark": "hex", "sector": "Фармацевтика"},
    {"name": "Medice", "mark": "cross", "sector": "Фармацевтика"},
    {"name": "Lukoil", "mark": "drop", "sector": "Нефтегаз"},
    {"name": "Gazpromneft", "mark": "flame", "sector": "Нефтегаз"},
    {"name": "Picasso", "mark": "picasso", "sector": "Арт-студия"},
    # Латиницей, как в домене raztamojka.uz: Michroma не содержит кириллицы,
    # и написание «Растаможка.uz» выпало бы на запасной шрифт — ряд бы поехал.
    {"name": "Raztamojka.uz", "mark": "container", "sector": "Таможенное оформление"},
]


def client_mark(key: str) -> str:
    return (
        '<svg class="client-mark" viewBox="0 0 32 32" width="34" height="34" '
        f'aria-hidden="true" focusable="false">{CLIENT_MARKS[key]}</svg>'
    )


# --------------------------------------------------------------------- JSON-LD


def jsonld(obj) -> str:
    body = json.dumps(obj, ensure_ascii=False, indent=2)
    return f'<script type="application/ld+json">{body}</script>'


def organization_ld(s: dict) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "ProfessionalService",
        "@id": f"{s['origin']}/#organization",
        "name": s["name"],
        "description": f"{s['tagline']} полного цикла в {s['city']}е: контекстная реклама, SEO, SMM, Telegram Ads и веб-разработка.",
        "url": s["origin"] + "/",
        "logo": f"{s['origin']}/assets/icons/favicon-512.png",
        "image": f"{s['origin']}/assets/og/og-default.jpg",
        "telephone": s["phone"],
        "email": s["email"],
        "foundingDate": s["founded"],
        "priceRange": s["priceRange"],
        "address": {
            "@type": "PostalAddress",
            "addressLocality": s["city"],
            "addressRegion": s["region"],
            "addressCountry": s["countryCode"],
        },
        "geo": {"@type": "GeoCoordinates", "latitude": s["lat"], "longitude": s["lon"]},
        "areaServed": [
            {"@type": "Country", "name": "Узбекистан"},
            {"@type": "Place", "name": "СНГ"},
        ],
        "sameAs": [s["telegram"]],
        "knowsLanguage": ["ru", "uz", "en"],
    }


def services_ld(s: dict, services: list) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "Услуги Sales Hub",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "item": {
                    "@type": "Service",
                    "name": sv["title"],
                    "description": sv["lead"],
                    "url": f"{s['origin']}/{sv['slug']}.html",
                    "provider": {"@id": f"{s['origin']}/#organization"},
                    "areaServed": {"@type": "Country", "name": "Узбекистан"},
                },
            }
            for i, sv in enumerate(services)
        ],
    }


def service_page_ld(s: dict, sv: dict) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": sv["title"],
        "description": sv["metaDescription"],
        "url": f"{s['origin']}/{sv['slug']}.html",
        "serviceType": sv["title"],
        "provider": {
            "@type": "ProfessionalService",
            "@id": f"{s['origin']}/#organization",
            "name": s["name"],
            "telephone": s["phone"],
            "address": {
                "@type": "PostalAddress",
                "addressLocality": s["city"],
                "addressCountry": s["countryCode"],
            },
        },
        "areaServed": {"@type": "Country", "name": "Узбекистан"},
    }


def breadcrumb_ld(s: dict, sv: dict) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Главная", "item": s["origin"] + "/"},
            {"@type": "ListItem", "position": 2, "name": "Услуги", "item": f"{s['origin']}/#services"},
            {"@type": "ListItem", "position": 3, "name": sv["title"], "item": f"{s['origin']}/{sv['slug']}.html"},
        ],
    }


def faq_ld(faq: list) -> dict:
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q["q"],
                "acceptedAnswer": {"@type": "Answer", "text": q["a"]},
            }
            for q in faq
        ],
    }


# ------------------------------------------------------------------ картинки

MANIFEST = json.loads((ROOT / "assets" / "img" / "manifest.json").read_text(encoding="utf-8"))


def picture(stem: str, preset: str, alt: str, cls: str, *, eager: bool = False, sizes: str = "") -> str:
    """<picture> с AVIF + WebP, точными размерами и правильным приоритетом."""
    w, h = MANIFEST[stem][preset]
    loading = "" if eager else ' loading="lazy" decoding="async"'
    priority = ' fetchpriority="high" decoding="async"' if eager else ""
    sizes_attr = f' sizes="{sizes}"' if sizes else ""
    return (
        "<picture>"
        f'<source type="image/avif" srcset="assets/img/{stem}-{preset}.avif"{sizes_attr}>'
        f'<source type="image/webp" srcset="assets/img/{stem}-{preset}.webp"{sizes_attr}>'
        f'<img src="assets/img/{stem}-{preset}.webp" alt="{html.escape(alt, quote=True)}" '
        f'width="{w}" height="{h}" class="{cls}"{loading}{priority}>'
        "</picture>"
    )


# --------------------------------------------------------------------- сборка


def main() -> int:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    s = data["site"]
    services = data["services"]

    # производные поля
    for sv in services:
        sv["url"] = f"{sv['slug']}.html"
        sv["iconSvg"] = icon(sv["icon"], 26)
        sv["iconSvgSm"] = icon(sv["icon"], 18)
        sv["heroImg"] = sv.get("imgHero", sv["img"])
        sv["cardPicture"] = picture(
            sv["img"], "card", sv.get("alt", sv["title"]), "service-card-img",
            sizes="(max-width: 860px) 100vw, (max-width: 1240px) 50vw, 400px",
        )

    # «Другие услуги» — следующие три по кругу, чтобы страницы не ссылались
    # все на один и тот же набор.
    n = len(services)
    for i, sv in enumerate(services):
        sv["related"] = [services[(i + k) % n] for k in range(1, 4)]

    base = {
        "site": s,
        "services": services,
        "year": date.today().year,
        "buildDate": date.today().isoformat(),
        "phoneHref": "tel:" + s["phone"],
        "contactsHref": "#contacts",
        "emailHref": "mailto:" + s["email"],
    }

    written = []

    # ---- главная
    index_ctx = dict(base)
    index_ctx.update(
        {
            "pageTitle": f"{s['name']} — {s['tagline'].lower()} в {s['city']}е",
            "metaTitle": data["metaTitle"],
            "metaDescription": data["metaDescription"],
            "hero": data["hero"],
            "canonical": s["origin"] + "/",
            "ogImage": f"{s['origin']}/assets/og/og-default.jpg",
            "isIndex": True,
            "homeHref": "#hero",
            "navPrefix": "",
            "ctaTitle": "Готовы к запуску?",
            "heroStats": data["heroStats"],
            "heroBar": data["heroBar"],
            "resultStats": data["resultStats"],
            "whyList": data["whyList"],
            "process": data["process"],
            "faq": data["faq"],
            "clients": data["clients"],
            "clientList": [
                {**c, "markSvg": client_mark(c["mark"])} for c in CLIENTS
            ],
            "heroPicture": picture(
                "hero-rover", "hero", "", "hero-photo-img", eager=True, sizes="100vw"
            ),
            # Слой со свечением изнутри модуля: тот же кадр, те же правила
            # object-fit, поэтому совмещается при любом размере экрана.
            "heroGlow": (
                '<picture>'
                '<source type="image/avif" srcset="assets/img/hero-rover-glow.avif">'
                '<source type="image/webp" srcset="assets/img/hero-rover-glow.webp">'
                '<img src="assets/img/hero-rover-glow.webp" alt="" aria-hidden="true" '
                'width="1920" height="1175" class="hero-glow-img" decoding="async">'
                '</picture>'
            ),
            "processPicture": picture(
                "process-missioncontrol", "banner",
                "Центр управления кампаниями Sales Hub", "process-banner-img",
                sizes="(max-width: 1240px) 100vw, 1176px",
            ),
            "whyPicture": picture(
                "why-earthnight", "photo",
                "Рабочее место команды Sales Hub", "why-photo-img",
                sizes="(max-width: 1080px) 100vw, 360px",
            ),
            "contactPicture": picture(
                "contact-mars", "bg", "", "contact-bg-img", sizes="100vw"
            ),
            "structuredData": "\n".join(
                [
                    jsonld(organization_ld(s)),
                    jsonld(services_ld(s, services)),
                    jsonld(faq_ld(data["faq"])),
                ]
            ),
        }
    )
    written.append(("index.html", render((TPL / "index.html").read_text(encoding="utf-8"), index_ctx)))

    # ---- страницы услуг
    tpl_service = (TPL / "service.html").read_text(encoding="utf-8")
    for sv in services:
        ctx = dict(base)
        ctx.update(sv)
        ctx.update(
            {
                "service": sv,
                "pageTitle": sv["h1"],
                "metaTitle": sv["metaTitle"],
                "metaDescription": sv["metaDescription"],
                "canonical": f"{s['origin']}/{sv['slug']}.html",
                "ogImage": f"{s['origin']}/assets/img/{sv['heroImg']}-hero.webp",
                "isIndex": False,
                "homeHref": "index.html",
                "navPrefix": "index.html",
                "heroPicture": picture(
                    sv["heroImg"], "hero", "", "page-hero-img", eager=True, sizes="100vw"
                ),
                "contactPicture": picture(
                    "contact-mars", "bg", "", "contact-bg-img", sizes="100vw"
                ),
                "isCpa": sv.get("custom") == "cpa",
                "structuredData": "\n".join(
                    [jsonld(service_page_ld(s, sv)), jsonld(breadcrumb_ld(s, sv))]
                    + ([jsonld(faq_ld(sv["faq"]))] if sv.get("faq") else [])
                ),
            }
        )
        written.append((f"{sv['slug']}.html", render(tpl_service, ctx)))

    # ---- политика конфиденциальности
    priv = dict(base)
    priv.update(
        {
            "pageTitle": "Политика конфиденциальности",
            "metaTitle": f"Политика конфиденциальности — {s['name']}",
            "metaDescription": "Как Sales Hub обрабатывает и защищает персональные данные, оставленные через форму заявки на сайте.",
            "canonical": f"{s['origin']}/privacy.html",
            "ogImage": f"{s['origin']}/assets/og/og-default.jpg",
            "isIndex": False,
            "homeHref": "index.html",
            "navPrefix": "index.html",
            "noindex": True,
            "contactsHref": "index.html#contacts",
            "structuredData": "",
        }
    )
    written.append(("privacy.html", render((TPL / "privacy.html").read_text(encoding="utf-8"), priv)))

    # ---- запись
    for name, content in written:
        (ROOT / name).write_text(content, encoding="utf-8")
        print(f"  ✓ {name:22s} {len(content.encode()) // 1024:>3} КБ")

    # ---- robots.txt и sitemap.xml
    (ROOT / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nDisallow: /privacy.html\n\n"
        f"Sitemap: {s['origin']}/sitemap.xml\n",
        encoding="utf-8",
    )

    urls = [(s["origin"] + "/", "1.0", "weekly")] + [
        (f"{s['origin']}/{sv['slug']}.html", "0.8", "monthly") for sv in services
    ]
    today = date.today().isoformat()
    body = "\n".join(
        f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{today}</lastmod>\n"
        f"    <changefreq>{cf}</changefreq>\n    <priority>{p}</priority>\n  </url>"
        for u, p, cf in urls
    )
    (ROOT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n",
        encoding="utf-8",
    )
    print(f"  ✓ robots.txt, sitemap.xml ({len(urls)} URL)")
    print(f"\nСобрано страниц: {len(written)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
