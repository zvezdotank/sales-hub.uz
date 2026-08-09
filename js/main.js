// ===========================
// Sales Hub — interactions
// ===========================

// Адрес обработчика заявок берётся из data-endpoint на форме, а он — из
// site.json. Пока адрес пуст, форма честно предлагает написать в Telegram
// вместо того, чтобы делать вид, что заявка ушла.
const TELEGRAM_URL = 'https://t.me/Saleshubuzb';

const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

document.addEventListener('DOMContentLoaded', () => {
  initStars();
  initHeaderScroll();
  initMobileNav();
  initReveal();
  initStatBars();
  initRouteLine();
  initCounters();
  initScrollTop();
  initContactForm();
  initSchedule();
  initAnalytics();
  initFaq();
});

// --- Вопросы и ответы -------------------------------------------------------

function initFaq() {
  document.querySelectorAll('.faq-list').forEach((list) => {
    const items = [...list.querySelectorAll('.faq-item')];

    // Открытым остаётся только один ответ: когда раскрывают следующий,
    // предыдущий закрывается сам. Иначе список расползается и теряется
    // ощущение, что вопросов немного.
    items.forEach((item) => {
      item.addEventListener('toggle', () => {
        if (!item.open) return;
        items.forEach((other) => {
          if (other !== item) other.open = false;
        });
      });
    });
  });
}

// --- Аналитика --------------------------------------------------------------
// Просмотры страниц GA4 считает сам. Здесь — обращения: без них в отчёте видно
// трафик, но не видно, во что он превращается.

function track(event, params) {
  if (typeof window.gtag === 'function') window.gtag('event', event, params || {});
}

function initAnalytics() {
  // Делегирование на документ: один обработчик вместо десятка, и он
  // продолжит работать для элементов, добавленных позже.
  document.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (!link) return;

    const href = link.getAttribute('href') || '';
    const where = link.closest('.mobile-dock') ? 'mobile_dock'
      : link.closest('.site-header') ? 'header'
      : link.closest('.cta-contact') ? 'contacts'
      : link.closest('.site-footer') ? 'footer'
      : 'page';

    if (href.startsWith('tel:')) track('click_phone', { location: where });
    else if (href.includes('t.me/')) track('click_telegram', { location: where });
    else if (href.startsWith('mailto:')) track('click_email', { location: where });
  });
}

// --- Звёздный фон -----------------------------------------------------------

function initStars() {
  const container = document.getElementById('stars');
  if (!container || prefersReducedMotion) return;

  const count = window.innerWidth < 700 ? 50 : 120;
  const frag = document.createDocumentFragment();

  for (let i = 0; i < count; i++) {
    const star = document.createElement('span');
    const size = Math.random() * 1.6 + 0.6;
    star.style.top = Math.random() * 100 + '%';
    star.style.left = Math.random() * 100 + '%';
    star.style.width = size + 'px';
    star.style.height = size + 'px';
    star.style.animationDelay = Math.random() * 4 + 's';
    star.style.animationDuration = 3 + Math.random() * 3 + 's';
    frag.appendChild(star);
  }
  container.appendChild(frag);
}

// --- Шапка ------------------------------------------------------------------

function initHeaderScroll() {
  const header = document.getElementById('siteHeader');
  if (!header) return;

  const toggle = () => header.classList.toggle('scrolled', window.scrollY > 20);
  toggle();
  window.addEventListener('scroll', toggle, { passive: true });
}

function initMobileNav() {
  const toggle = document.getElementById('navToggle');
  const nav = document.getElementById('mainNav');
  if (!toggle || !nav) return;

  const setOpen = (open) => {
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    nav.classList.toggle('open', open);
  };

  toggle.addEventListener('click', () => {
    setOpen(toggle.getAttribute('aria-expanded') !== 'true');
  });

  nav.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => setOpen(false));
  });

  // Закрытие по Escape и по клику вне меню — иначе меню оставалось висеть.
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
      setOpen(false);
      toggle.focus();
    }
  });

  document.addEventListener('click', (e) => {
    if (toggle.getAttribute('aria-expanded') !== 'true') return;
    if (!nav.contains(e.target) && !toggle.contains(e.target)) setOpen(false);
  });
}

// --- Появление блоков при скролле -------------------------------------------

function observeOnce(elements, onEnter, threshold) {
  if (!('IntersectionObserver' in window)) {
    elements.forEach(onEnter);
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      onEnter(entry.target);
      observer.unobserve(entry.target);
    });
  }, { threshold });
  elements.forEach((el) => observer.observe(el));
}

function initReveal() {
  const targets = [...document.querySelectorAll(
    '.service-card, .route-step, .why-stat-card, .client-item, .faq-item, .contact-panel, .section-head'
  )];
  if (prefersReducedMotion) return;

  targets.forEach((el) => el.classList.add('reveal'));
  observeOnce(targets, (el) => el.classList.add('in-view'), 0.15);
}

function initStatBars() {
  const rows = [...document.querySelectorAll('.stat-row')];
  observeOnce(rows, (row) => {
    const fill = row.querySelector('.stat-fill');
    if (fill) requestAnimationFrame(() => { fill.style.width = row.dataset.value + '%'; });
  }, 0.3);
}

function initRouteLine() {
  const lines = [...document.querySelectorAll('.route-line-fill')];
  observeOnce(lines, (el) => el.classList.add('in-view'), 0.4);
}

// --- Счётчики ---------------------------------------------------------------

function initCounters() {
  const nums = [...document.querySelectorAll('.why-stat-num')];
  observeOnce(nums, animateCount, 0.5);
}

function animateCount(el) {
  const target = parseInt(el.dataset.count, 10);
  const suffix = el.dataset.suffix || '';
  const divide = parseInt(el.dataset.divide, 10) || 1;
  const decimals = divide > 1 ? 1 : 0;

  const format = (v) => (v / divide).toFixed(decimals) + suffix;

  if (prefersReducedMotion || Number.isNaN(target)) {
    el.textContent = format(target);
    return;
  }

  const duration = 1400;
  const start = performance.now();

  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = format(target * eased);
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

// --- Кнопка «наверх» --------------------------------------------------------

function initScrollTop() {
  const btn = document.getElementById('scrollTop');
  if (!btn) return;

  btn.hidden = false;
  const toggle = () => btn.classList.toggle('visible', window.scrollY > 600);
  toggle();
  window.addEventListener('scroll', toggle, { passive: true });

  btn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: prefersReducedMotion ? 'auto' : 'smooth' });
  });
}

// --- Часы приёма ------------------------------------------------------------
// Считаем по времени Ташкента, а не по часам устройства: иначе клиент из
// другого пояса увидел бы, что связь открыта, когда на самом деле уже ночь.

function initSchedule() {
  const el = document.getElementById('dockStatus');
  const out = el && el.querySelector('.dock-status-text');
  if (!out) return;

  const openHour = +el.dataset.open;
  const closeHour = +el.dataset.close;
  const tzOffset = +el.dataset.tz;
  const workdays = el.dataset.workdays.split(',').map(Number);

  // «Сейчас» в часовом поясе агентства, независимо от настроек устройства.
  const nowThere = () => {
    const now = new Date();
    return new Date(now.getTime() + now.getTimezoneOffset() * 60000 + tzOffset * 3600000);
  };

  const pad = (n) => String(n).padStart(2, '0');

  const format = (ms) => {
    const total = Math.max(0, Math.floor(ms / 1000));
    const days = Math.floor(total / 86400);
    const h = Math.floor((total % 86400) / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    return days > 0
      ? `${days} дн ${pad(h)}:${pad(m)}`
      : `${h}:${pad(m)}:${pad(s)}`;
  };

  // Ближайший момент открытия начиная с указанной даты.
  const nextOpening = (from) => {
    const d = new Date(from);
    for (let i = 0; i < 8; i++) {
      const candidate = new Date(d);
      candidate.setDate(d.getDate() + i);
      candidate.setHours(openHour, 0, 0, 0);
      if (candidate > from && workdays.includes(candidate.getDay())) return candidate;
    }
    return null;
  };

  const tick = () => {
    const now = nowThere();
    const isWorkday = workdays.includes(now.getDay());
    const closing = new Date(now);
    closing.setHours(closeHour, 0, 0, 0);

    const open = isWorkday && now.getHours() >= openHour && now < closing;

    if (open) {
      el.classList.remove('is-closed');
      out.textContent = `КАНАЛ СВЯЗИ · ОТКРЫТ ${format(closing - now)}`;
    } else {
      el.classList.add('is-closed');
      const next = nextOpening(now);
      out.textContent = next
        ? `КАНАЛ СВЯЗИ · ЧЕРЕЗ ${format(next - now)}`
        : 'КАНАЛ СВЯЗИ · НАПИШИТЕ В TELEGRAM';
    }
  };

  // Одна секунда — незаметная нагрузка, но в фоновой вкладке таймер
  // останавливаем, чтобы не будить процессор впустую.
  let timer = null;
  const start = () => {
    if (timer) return;
    tick();
    timer = setInterval(tick, 1000);
  };
  const stop = () => {
    clearInterval(timer);
    timer = null;
  };

  document.addEventListener('visibilitychange', () => {
    document.hidden ? stop() : start();
  });
  start();
}

// --- Форма заявки -----------------------------------------------------------

function initContactForm() {
  const form = document.getElementById('contactForm');
  const note = document.getElementById('formNote');
  if (!form || !note) return;

  const defaultNote = note.innerHTML;
  const button = form.querySelector('button[type="submit"]');
  const buttonText = button.querySelector('.btn-text');

  const setError = (input, message) => {
    const box = document.getElementById('err-' + input.name);
    if (!box) return;
    box.textContent = message || '';
    box.hidden = !message;
    input.setAttribute('aria-invalid', message ? 'true' : 'false');
  };

  const validate = () => {
    let firstInvalid = null;

    const name = form.elements.name;
    const contact = form.elements.contact;

    if (!name.value.trim()) {
      setError(name, 'Укажите, как к вам обращаться');
      firstInvalid = firstInvalid || name;
    } else {
      setError(name, '');
    }

    const value = contact.value.trim();
    const isPhone = /^\+?[\d\s()-]{7,}$/.test(value);
    const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value);

    if (!value) {
      setError(contact, 'Оставьте телефон или email для связи');
      firstInvalid = firstInvalid || contact;
    } else if (!isPhone && !isEmail) {
      setError(contact, 'Похоже на опечатку — проверьте номер или email');
      firstInvalid = firstInvalid || contact;
    } else {
      setError(contact, '');
    }

    return firstInvalid;
  };

  form.querySelectorAll('input').forEach((input) => {
    input.addEventListener('input', () => {
      if (input.getAttribute('aria-invalid') === 'true') validate();
    });
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const invalid = validate();
    if (invalid) {
      invalid.focus();
      note.className = 'form-note error';
      note.textContent = 'Проверьте отмеченные поля.';
      return;
    }

    const endpoint = form.dataset.endpoint || '';

    // Обработчик ещё не подключён: не делаем вид, что заявка ушла.
    if (!endpoint) {
      track('form_blocked');
      note.className = 'form-note error';
      note.innerHTML =
        'Отправка формы пока не подключена. Напишите нам в ' +
        '<a href="' + TELEGRAM_URL + '" target="_blank" rel="noopener">Telegram</a> — ответим сразу.';
      return;
    }

    button.disabled = true;
    buttonText.textContent = 'Отправляем…';
    note.className = 'form-note';
    note.textContent = 'Отправляем заявку…';

    try {
      const payload = Object.fromEntries(new FormData(form));
      payload.page = location.pathname; // видно, с какой страницы пришла заявка

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error('HTTP ' + response.status);

      form.reset();
      track('generate_lead', { method: 'form' });
      buttonText.textContent = 'Отправлено ✓';
      note.className = 'form-note success';
      note.textContent = 'Заявка принята. Свяжемся с вами в течение рабочего дня.';
    } catch (error) {
      track('form_error');
      buttonText.textContent = 'Отправить заявку';
      note.className = 'form-note error';
      note.innerHTML =
        'Не удалось отправить заявку. Напишите в ' +
        '<a href="' + TELEGRAM_URL + '" target="_blank" rel="noopener">Telegram</a> ' +
        'или позвоните нам.';
    } finally {
      button.disabled = false;
      setTimeout(() => {
        buttonText.textContent = 'Отправить заявку';
        note.className = 'form-note';
        note.innerHTML = defaultNote;
      }, 6000);
    }
  });
}
