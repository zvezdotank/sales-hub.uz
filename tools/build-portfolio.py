#!/usr/bin/env python3
"""
Снимает сайты из портфолио целиком — одним длинным кадром — и готовит их
для блока «Работы» на странице web-dev.html.

Почему так сложно. Простой способ (`chrome --headless --screenshot` с окном
высотой в несколько тысяч пикселей) не годится: на сайтах, где секции заданы
в единицах `vh`, страница растягивается вслед за окном и кадр получается
бесконечным. Поэтому окно оставляем нормальным — 1280×800, — а снимок за
пределами видимой области заказываем через протокол DevTools
(`Page.captureScreenshot` с `captureBeyondViewport`). Заодно перед съёмкой
прокручиваем страницу сверху донизу: так подгружаются ленивые картинки и
срабатывают блоки с появлением по скроллу.

Готовых библиотек для этого протокола в системе нет, а тянуть зависимость
ради одной задачи не хочется — поэтому ниже лежит минимальный клиент
WebSocket на стандартной библиотеке. Он умеет ровно то, что нужно: соединиться,
отправить команду, дождаться ответа.

Список сайтов берётся из site.json: услуга с блоком "portfolio", массив items.
Результат — AVIF + WebP в assets/img/portfolio/ и manifest.json с размерами,
из которого build-site.py подставляет width/height и длительность прокрутки.

Запуск:  python3 tools/build-portfolio.py            — все сайты
         python3 tools/build-portfolio.py dosug      — только совпавшие по slug
"""

from __future__ import annotations

import base64
import io
import json
import os
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site.json"
OUT = ROOT / "assets" / "img" / "portfolio"

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

VIEWPORT = (1280, 800)   # обычное десктопное окно: vh-секции нормального размера
MAX_SHOT_HEIGHT = 16000  # выше браузер снимать отказывается (предел текстуры)

OUT_WIDTH = 640          # ширина готовой картинки (карточка ~370px, запас на 2x)

# Кадры показываются в карточке шириной 220–420px, то есть уменьшенными вдвое
# и более. Сравнение в реальном масштабе показало, что между качеством 48 и 36
# разницы не видно, а вес падает почти на треть. Портфолио — самая тяжёлая
# страница сайта, и здесь это решает.
QUALITY = {"avif": 36, "webp": 58}


# ------------------------------------------------------- минимальный WebSocket


class WebSocket:
    """Клиентское соединение по RFC 6455 — ровно в объёме, нужном для CDP."""

    def __init__(self, url: str, timeout: float = 120.0):
        if not url.startswith("ws://"):
            raise ValueError(f"ожидался ws://, получено {url}")
        hostport, _, path = url[len("ws://"):].partition("/")
        host, _, port = hostport.partition(":")

        self.sock = socket.create_connection((host, int(port or 80)), timeout=timeout)
        self.sock.settimeout(timeout)
        self.buf = b""

        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall(
            f"GET /{path} HTTP/1.1\r\n"
            f"Host: {hostport}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n".encode()
        )
        while b"\r\n\r\n" not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("браузер закрыл соединение при рукопожатии")
            self.buf += chunk
        head, _, self.buf = self.buf.partition(b"\r\n\r\n")
        if b" 101" not in head.split(b"\r\n")[0]:
            raise ConnectionError(head.decode("utf-8", "replace"))

    def _read(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.sock.recv(max(65536, n - len(self.buf)))
            if not chunk:
                raise ConnectionError("соединение оборвалось")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text: str, opcode: int = 0x1) -> None:
        data = text.encode()
        header = bytes([0x80 | opcode])
        n = len(data)
        if n < 126:
            header += bytes([0x80 | n])
        elif n < 1 << 16:
            header += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(header + mask + masked)

    def recv(self) -> str:
        """Одно текстовое сообщение, собранное из всех его кадров."""
        parts: list[bytes] = []
        while True:
            b0, b1 = self._read(2)
            fin, opcode = b0 & 0x80, b0 & 0x0F
            length = b1 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._read(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(length)

            if opcode == 0x8:
                raise ConnectionError("браузер закрыл соединение")
            if opcode == 0x9:            # ping — отвечаем pong тем же телом
                self.send(payload.decode("utf-8", "replace"), opcode=0xA)
                continue
            if opcode == 0xA:
                continue

            parts.append(payload)
            if fin:
                return b"".join(parts).decode("utf-8", "replace")

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


class Browser:
    """Headless-Chrome со своим временным профилем и одной вкладкой."""

    def __init__(self, profile: Path):
        self.proc = subprocess.Popen(
            [
                CHROME,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--force-color-profile=srgb",
                "--remote-debugging-port=0",
                f"--user-data-dir={profile}",
                f"--window-size={VIEWPORT[0]},{VIEWPORT[1]}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-sync",
                "--mute-audio",
                "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        port_file = profile / "DevToolsActivePort"
        for _ in range(200):                       # ждём до 20 секунд
            if port_file.exists():
                text = port_file.read_text().splitlines()
                if text:
                    self.port = int(text[0])
                    break
            time.sleep(0.1)
        else:
            raise RuntimeError("Chrome не открыл порт отладки")

        target = self._page_target()
        self.ws = WebSocket(target)
        self.seq = 0

    def _page_target(self) -> str:
        for _ in range(50):
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list", timeout=5) as r:
                targets = json.load(r)
            for t in targets:
                if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                    return t["webSocketDebuggerUrl"]
            time.sleep(0.2)
        raise RuntimeError("Chrome не создал вкладку")

    def call(self, method: str, **params) -> dict:
        self.seq += 1
        self.ws.send(json.dumps({"id": self.seq, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") != self.seq:
                continue                            # события нам не нужны
            if "error" in msg:
                raise RuntimeError(f"{method}: {msg['error'].get('message')}")
            return msg.get("result", {})

    def evaluate(self, expression: str, await_promise: bool = True):
        res = self.call(
            "Runtime.evaluate",
            expression=expression,
            awaitPromise=await_promise,
            returnByValue=True,
        )
        if "exceptionDetails" in res:
            raise RuntimeError(res["exceptionDetails"].get("text", "ошибка в странице"))
        return res.get("result", {}).get("value")

    def close(self) -> None:
        self.ws.close()
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


# ------------------------------------------------------------------- съёмка

# Подготовка страницы к съёмке. По шагам:
#
# 1. Прокрутка сверху донизу и обратно — включает ленивую загрузку картинок и
#    анимации появления, которые иначе остались бы прозрачными.
# 2. YouTube-эмбеды заменяем на обложку ролика: встроенный плеер в headless
#    рисует вместо превью чёрный прямоугольник во всю секцию.
# 3. Плавающие виджеты (обратный звонок, чат, «наверх») убираем — они всплывают
#    через несколько секунд и в неподвижном кадре выглядят как мусор.
#    Шапку во всю ширину не трогаем: она и должна быть сверху кадра.
# 4. Ждём, пока все картинки, включая только что подставленные обложки,
#    досчитаются загруженными.
WARMUP_JS = """
(async () => {
  const pause = ms => new Promise(r => setTimeout(r, ms));
  const full = () => document.documentElement.scrollHeight;

  for (let y = 0; y < full() && y < 40000; y += window.innerHeight * 0.75) {
    window.scrollTo(0, y);
    await pause(110);
  }
  window.scrollTo(0, full());
  await pause(350);
  window.scrollTo(0, 0);
  await pause(450);

  const posters = [];
  for (const frame of document.querySelectorAll('iframe[src*="/embed/"]')) {
    const id = (frame.getAttribute('src') || '').match(/\\/embed\\/([\\w-]{6,})/);
    if (!id) continue;
    const box = frame.getBoundingClientRect();
    if (box.width < 80 || box.height < 60) continue;
    const poster = document.createElement('img');
    poster.style.cssText = 'display:block;width:' + box.width + 'px;height:'
      + box.height + 'px;object-fit:cover;background:#000';
    frame.replaceWith(poster);
    // maxres есть не у всех роликов. На отсутствующий размер YouTube отвечает
    // кодом 404, но с телом: серой заглушкой 120×90. Браузер считает такую
    // картинку успешно загруженной, поэтому судим по её ширине, а не по
    // событию onload.
    const sources = ['maxresdefault', 'sddefault', 'hqdefault']
      .map(n => 'https://i.ytimg.com/vi/' + id[1] + '/' + n + '.jpg');
    posters.push(new Promise(done => {
      let i = 0;
      const next = () => {
        if (i >= sources.length) return done();
        poster.onload = () => (poster.naturalWidth >= 320 ? done() : (i++, next()));
        poster.onerror = () => { i++; next(); };
        poster.src = sources[i];
      };
      next();
    }));
  }
  await Promise.all(posters);

  for (const el of document.querySelectorAll('body *')) {
    const cs = getComputedStyle(el);
    if (cs.position !== 'fixed') continue;
    const r = el.getBoundingClientRect();
    if (r.width < 40 || r.height < 24) continue;
    if (r.width >= window.innerWidth * 0.9 && r.top <= 1) continue;
    el.style.setProperty('display', 'none', 'important');
  }

  for (let i = 0; i < 60; i++) {
    if (Array.from(document.images).every(im => im.complete)) break;
    await pause(100);
  }
  await pause(300);
  return full();
})()
"""


def shot_url(item: dict) -> str:
    """Откуда снимать кадр.

    Обычно это публичный адрес сайта. Но если у сайта не выпущен сертификат
    или он ещё не опубликован, в site.json можно указать "shotUrl" — например
    локальный сервер с теми же файлами. Если он не отвечает, откатываемся на
    публичный адрес, чтобы сборка не падала на чужой машине.
    """
    public = item.get("url") or f"https://{item['domain']}"
    local = item.get("shotUrl")
    if not local:
        return public
    try:
        urllib.request.urlopen(local, timeout=3).close()
        return local
    except OSError:
        print(f"    ! {local} не отвечает, снимаю с {public}")
        return public


def shoot(browser: Browser, url: str) -> Image.Image:
    """Кадр во всю длину страницы."""
    browser.call("Page.enable")
    browser.call(
        "Emulation.setDeviceMetricsOverride",
        width=VIEWPORT[0], height=VIEWPORT[1], deviceScaleFactor=1, mobile=False,
    )
    # Режим «уменьшить движение». Аккуратно сделанные сайты — включая наш
    # kanalizaciya.uz — в нём сразу показывают блоки, которые обычно
    # проявляются по мере прокрутки. Без этого нижняя половина страницы
    # попадает в кадр прозрачной. Содержимое от этого не меняется, меняется
    # только то, анимировано ли его появление.
    browser.call(
        "Emulation.setEmulatedMedia",
        features=[{"name": "prefers-reduced-motion", "value": "reduce"}],
    )
    browser.call("Page.navigate", url=url)

    # Ждём, пока страница догрузится: событий не слушаем, просто опрашиваем.
    for _ in range(150):
        if browser.evaluate("document.readyState", await_promise=False) == "complete":
            break
        time.sleep(0.2)

    browser.evaluate(WARMUP_JS)

    metrics = browser.call("Page.getLayoutMetrics")
    size = metrics.get("cssContentSize") or metrics["contentSize"]
    height = min(round(size["height"]), MAX_SHOT_HEIGHT)
    if round(size["height"]) > MAX_SHOT_HEIGHT:
        print(f"    ! страница {round(size['height'])}px, снимаю первые {MAX_SHOT_HEIGHT}px", file=sys.stderr)

    shot = browser.call(
        "Page.captureScreenshot",
        format="png",
        captureBeyondViewport=True,
        clip={"x": 0, "y": 0, "width": VIEWPORT[0], "height": height, "scale": 1},
    )
    with Image.open(io.BytesIO(base64.b64decode(shot["data"]))) as raw:
        return raw.convert("RGB")


# -------------------------------------------------------------------- сборка


def main(argv: list[str]) -> int:
    if not Path(CHROME).exists():
        print(f"Нет Google Chrome: {CHROME}", file=sys.stderr)
        return 1

    data = json.loads(DATA.read_text(encoding="utf-8"))
    items = next(
        (sv["portfolio"]["items"] for sv in data["services"] if sv.get("portfolio")),
        [],
    )
    if not items:
        print("В site.json нет услуги с блоком portfolio", file=sys.stderr)
        return 1

    only = set(argv[1:])
    if only:
        items = [it for it in items if it["slug"] in only]
        if not items:
            print(f"Ни один slug не совпал: {', '.join(sorted(only))}", file=sys.stderr)
            return 1

    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.exists()
        else {}
    )

    with tempfile.TemporaryDirectory() as profile:
        browser = Browser(Path(profile))
        try:
            for it in items:
                print(f"{it['slug']}")
                url = shot_url(it)
                print(f"    источник {url}")

                im = shoot(browser, url)
                print(f"    снято  {im.width}x{im.height}")

                h = round(im.height * OUT_WIDTH / im.width)
                small = im.resize((OUT_WIDTH, h), Image.LANCZOS)
                manifest[it["slug"]] = [small.width, small.height]

                for fmt in ("avif", "webp"):
                    dst = OUT / f"{it['slug']}-shot.{fmt}"
                    small.save(dst, format=fmt.upper(), quality=QUALITY[fmt])
                    print(f"    → {dst.name:26s} {small.width}x{small.height}  {dst.stat().st_size // 1024} КБ")
        finally:
            browser.close()

    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"\nРазмеры записаны в {manifest_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
