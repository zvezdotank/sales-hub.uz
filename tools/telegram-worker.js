/**
 * Cloudflare Worker: receives site forms and posts them to a Telegram group.
 *
 * Why a relay instead of calling Telegram from the browser: the bot token
 * must never appear in the site source, which is public on GitHub Pages.
 * Here the token lives in the Worker secrets and never leaves it.
 *
 * Secrets to set in the Worker settings:
 *   BOT_TOKEN - from @BotFather
 *   CHAT_ID   - group id, starts with a minus. Open /setup to find it.
 *
 * NB: every Russian string below is written as \uXXXX escapes on purpose.
 * This file is pasted into the Cloudflare editor through the clipboard, and
 * that path has already mangled raw UTF-8 once in another project. ASCII-only
 * source cannot be corrupted that way. The file is generated - do not retype
 * the escapes by hand.
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

const text = (body, status) =>
  new Response(body, { status, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });

// Telegram chokes on unbalanced tags, so neutralise anything a visitor typed.
const esc = (v) =>
  String(v || '').replace(/[<>&]/g, (c) => ({ '<': '\u2039', '>': '\u203a', '&': '&amp;' }[c]));

// Field order in the message. A field missing from the payload is skipped,
// so one map serves both the short contact form and the long brief.
const TITLES = [
  ['_form',   '\u0424\u043e\u0440\u043c\u0430'],
  ['company', '\u041a\u043e\u043c\u043f\u0430\u043d\u0438\u044f'],
  ['name',    '\u0418\u043c\u044f'],
  ['contact', '\u041a\u043e\u043d\u0442\u0430\u043a\u0442'],
  ['goals',   '\u0426\u0435\u043b\u044c \u043a\u0430\u043c\u043f\u0430\u043d\u0438\u0438'],
  ['budget',  '\u0411\u044e\u0434\u0436\u0435\u0442 \u0432 \u043c\u0435\u0441\u044f\u0446'],
  ['geo',     '\u0413\u0435\u043e\u0433\u0440\u0430\u0444\u0438\u044f'],
  ['site',    '\u0421\u0430\u0439\u0442'],
  ['social',  '\u0421\u043e\u0446\u0441\u0435\u0442\u0438'],
  ['message', '\u0421\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435'],
];

const LIMITS = { message: 2000, goals: 500 };

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const origin = request.headers.get('Origin') || '';

    // One-off helper: lists the chats the bot can see, so the group id can be
    // found without ever typing the token into a browser address bar. Switches
    // itself off as soon as CHAT_ID is set.
    if (url.pathname === '/setup') {
      if (!env.BOT_TOKEN) return text('\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u0437\u0430\u0434\u0430\u0439\u0442\u0435 \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u0443\u044e BOT_TOKEN.', 503);
      if (env.CHAT_ID) return text('\u0423\u0436\u0435 \u043d\u0430\u0441\u0442\u0440\u043e\u0435\u043d\u043e: CHAT_ID \u0437\u0430\u0434\u0430\u043d.', 403);
      const r = await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/getUpdates`);
      const data = await r.json();
      if (!data.ok) return text('Telegram \u043d\u0435 \u043f\u0440\u0438\u043d\u044f\u043b \u0442\u043e\u043a\u0435\u043d. \u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 BOT_TOKEN.', 502);
      const chats = {};
      for (const u of data.result || []) {
        const c = (u.message && u.message.chat) || (u.my_chat_member && u.my_chat_member.chat);
        if (c) chats[c.id] = `${c.title || c.username || c.first_name || ''} (${c.type})`;
      }
      const found = Object.entries(chats).map(([id, t]) => `${id}   ${t}`).join('\n');
      return text(
        found
          ? '\u041d\u0430\u0439\u0434\u0435\u043d\u043d\u044b\u0435 \u0447\u0430\u0442\u044b:' + '\n\n' + found + '\n\n'
            + '\u0412\u043e\u0437\u044c\u043c\u0438\u0442\u0435 id \u0433\u0440\u0443\u043f\u043f\u044b \u2014 \u0442\u043e\u0442, \u0447\u0442\u043e \u0441 \u043c\u0438\u043d\u0443\u0441\u043e\u043c, \u2014 \u0438 \u0432\u043f\u0438\u0448\u0438\u0442\u0435 \u0435\u0433\u043e \u0432 \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u0443\u044e CHAT_ID.'
          : '\u0427\u0430\u0442\u043e\u0432 \u043f\u043e\u043a\u0430 \u043d\u0435 \u0432\u0438\u0434\u043d\u043e. \u0414\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u0431\u043e\u0442\u0430 \u0432 \u0433\u0440\u0443\u043f\u043f\u0443, \u043d\u0430\u043f\u0438\u0448\u0438\u0442\u0435 \u0442\u0430\u043c \u043b\u044e\u0431\u043e\u0435 \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u0438 \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u0435 \u0441\u0442\u0440\u0430\u043d\u0438\u0446\u0443.',
        200);
    }

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors(origin) });
    }

    // Manual check: open the worker address in a browser.
    if (request.method === 'GET') {
      const missing = [!env.BOT_TOKEN && 'BOT_TOKEN', !env.CHAT_ID && 'CHAT_ID'].filter(Boolean);
      return missing.length
        ? text('\u0412\u043e\u0440\u043a\u0435\u0440 \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442, \u043d\u043e \u043d\u0435 \u0445\u0432\u0430\u0442\u0430\u0435\u0442 \u043f\u0435\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0445: ' + missing.join(', '), 503)
        : text('\u0412\u043e\u0440\u043a\u0435\u0440 \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442, \u0442\u043e\u043a\u0435\u043d \u0438 \u0447\u0430\u0442 \u0437\u0430\u0434\u0430\u043d\u044b. \u041c\u043e\u0436\u043d\u043e \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0430\u0442\u044c \u0444\u043e\u0440\u043c\u0443.', 200);
    }

    if (request.method !== 'POST') {
      return json({ ok: false, error: 'method_not_allowed' }, 405, origin);
    }

    // Requests are accepted only from our own site. An empty Origin is
    // rejected too: a browser always sends it on a cross-site POST, while a
    // script does not, and the check would be trivial to skip.
    if (!ALLOWED_ORIGINS.includes(origin)) {
      return json({ ok: false, error: 'forbidden_origin' }, 403, origin);
    }
    if (!env.BOT_TOKEN || !env.CHAT_ID) {
      return json({ ok: false, error: 'not_configured' }, 500, origin);
    }

    let data = {};
    try {
      const ct = request.headers.get('Content-Type') || '';
      data = ct.includes('application/json')
        ? await request.json()
        : Object.fromEntries(await request.formData());
    } catch {
      return json({ ok: false, error: 'bad_request' }, 400, origin);
    }

    // Honeypot: the field is hidden from people but filled in by bots.
    // Answer with success so the spammer does not learn he was filtered.
    if (data.department) return json({ ok: true }, 200, origin);

    const contact = String(data.contact || '').trim();
    if (!contact) return json({ ok: false, error: 'missing_fields' }, 422, origin);

    const lines = ['\ud83d\ude80 \u0417\u0430\u044f\u0432\u043a\u0430 \u0441 \u0441\u0430\u0439\u0442\u0430', ''];
    for (const [key, title] of TITLES) {
      const value = String(data[key] || '').trim().slice(0, LIMITS[key] || 200);
      if (value) lines.push(`${title}: ${esc(value)}`);
    }
    const cf = request.cf || {};
    lines.push('', `${esc(data.page || '/')} - ${esc(cf.city || '')} ${esc(cf.country || '')}`);
    lines.push(new Date().toLocaleString('ru-RU', { timeZone: 'Asia/Tashkent' }));

    const sent = await fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: env.CHAT_ID,
        text: lines.join('\n'),
        disable_web_page_preview: true,
      }),
    });

    if (!sent.ok) {
      console.error('Telegram error', sent.status, await sent.text());
      return json({ ok: false, error: 'telegram_failed' }, 502, origin);
    }

    return json({ ok: true }, 200, origin);
  },
};
