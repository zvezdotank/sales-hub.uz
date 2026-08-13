/**
 * Cloudflare Worker: приём заявок с сайта и отправка их в Telegram.
 *
 * Зачем нужен посредник, а не запрос из браузера напрямую в Telegram:
 * токен бота нельзя класть в код сайта — его увидит любой, кто откроет
 * исходник страницы, и сможет писать в ваш чат от имени бота. Здесь токен
 * живёт в переменных Worker'а и наружу не попадает.
 *
 * Переменные окружения (задаются в настройках Worker'а как Secret):
 *   BOT_TOKEN — токен от @BotFather
 *   CHAT_ID   — ваш Telegram ID (узнать у @userinfobot)
 *
 * Инструкция по установке: README.md, раздел «Заявки в Telegram».
 */

const ALLOWED_ORIGINS = [
  'https://sales-hub.uz',
  'https://www.sales-hub.uz',
];

const cors = (origin) => ({
  'Access-Control-Allow-Origin': ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0],
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '86400',
});

const json = (data, status, origin) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...cors(origin) },
  });

// Телеграм ломается на несбалансированных тегах, поэтому экранируем всё,
// что пришло от пользователя.
const esc = (s) =>
  String(s || '').replace(/[<>&]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;' }[c]));

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors(origin) });
    }

    // Проверка вручную: откройте адрес воркера в браузере. Страница скажет,
    // жив ли он и заданы ли обе переменные. Сами значения не показываем.
    if (request.method === 'GET') {
      const ready = Boolean(env.BOT_TOKEN && env.CHAT_ID);
      return new Response(
        ready
          ? 'Воркер работает, токен и чат заданы. Можно подключать форму.'
          : 'Воркер работает, но не хватает переменных: '
            + [!env.BOT_TOKEN && 'BOT_TOKEN', !env.CHAT_ID && 'CHAT_ID'].filter(Boolean).join(', '),
        { status: ready ? 200 : 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } },
      );
    }

    if (request.method !== 'POST') {
      return json({ ok: false, error: 'method_not_allowed' }, 405, origin);
    }
    // Заявки принимаем только со своего сайта — иначе форму можно дёргать
    // откуда угодно и завалить чат мусором. Пустой Origin тоже отклоняем:
    // браузер на межсайтовый POST его всегда проставляет, а вот curl и
    // скрипты — нет, и проверку было бы достаточно обойти, просто не послав
    // заголовок.
    if (!ALLOWED_ORIGINS.includes(origin)) {
      return json({ ok: false, error: 'forbidden_origin' }, 403, origin);
    }
    if (!env.BOT_TOKEN || !env.CHAT_ID) {
      return json({ ok: false, error: 'not_configured' }, 500, origin);
    }

    let data = {};
    try {
      const ct = request.headers.get('Content-Type') || '';
      if (ct.includes('application/json')) {
        data = await request.json();
      } else {
        data = Object.fromEntries(await request.formData());
      }
    } catch {
      return json({ ok: false, error: 'bad_request' }, 400, origin);
    }

    // Honeypot: поле скрыто от людей, но видно ботам. Заполнено — молча
    // отвечаем успехом, чтобы спамер не понял, что его отсеяли.
    if (data.company) return json({ ok: true }, 200, origin);

    const name = String(data.name || '').trim().slice(0, 100);
    const contact = String(data.contact || '').trim().slice(0, 100);
    const message = String(data.message || '').trim().slice(0, 2000);
    if (!name || !contact) {
      return json({ ok: false, error: 'missing_fields' }, 422, origin);
    }

    const cf = request.cf || {};
    const text = [
      '🚀 <b>Новая заявка с сайта</b>',
      '',
      `<b>Имя:</b> ${esc(name)}`,
      `<b>Контакт:</b> ${esc(contact)}`,
      message ? `<b>Сообщение:</b> ${esc(message)}` : null,
      '',
      `<i>${esc(data.page || 'sales-hub.uz')} · ${esc(cf.city || '')} ${esc(cf.country || '')}</i>`,
    ]
      .filter(Boolean)
      .join('\n');

    const tg = await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: env.CHAT_ID,
        text,
        parse_mode: 'HTML',
        disable_web_page_preview: true,
      }),
    });

    if (!tg.ok) {
      const detail = await tg.text();
      console.error('Telegram error', tg.status, detail);
      return json({ ok: false, error: 'telegram_failed' }, 502, origin);
    }

    return json({ ok: true }, 200, origin);
  },
};
