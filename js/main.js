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
  initWorksFilter();
  initNavSubmenu();
  initBriefForm();
});

// --- Список услуг в шапке ---------------------------------------------------
// Мышкой список раскрывается наведением, это делает CSS. Здесь — то, чего
// наведением не сделать: клавиатура и касание.

function initNavSubmenu() {
  const item = document.querySelector('.nav-item');
  const toggle = item && item.querySelector('.nav-sub-toggle');
  if (!toggle) return;

  const setOpen = (open) => {
    toggle.setAttribute('aria-expanded', String(open));
    item.classList.toggle('is-open', open);
  };

  toggle.addEventListener('click', () => {
    setOpen(toggle.getAttribute('aria-expanded') !== 'true');
  });

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape' || toggle.getAttribute('aria-expanded') !== 'true') return;
    setOpen(false);
    toggle.focus();
  });

  document.addEventListener('click', (e) => {
    if (!item.contains(e.target)) setOpen(false);
  });

  // Уход фокуса за пределы пункта закрывает список — иначе он оставался бы
  // раскрытым, пока человек табом уже ушёл дальше по странице.
  item.addEventListener('focusout', (e) => {
    if (!item.contains(e.relatedTarget)) setOpen(false);
  });
}

// --- Фильтр работ по направлению --------------------------------------------

function initWorksFilter() {
  const bar = document.querySelector('.works-filter');
  const grid = document.querySelector('.works-grid');
  if (!bar || !grid) return;

  const cards = [...grid.querySelectorAll('.work')];
  const buttons = [...bar.querySelectorAll('.works-filter-btn')];
  const status = document.getElementById('works-count');

  // Кнопки отрисованы скрытыми: без скрипта они бы ничего не делали.
  bar.hidden = false;
  // С этого момента ступенчатым сдвигом карточек управляет скрипт, а не CSS.
  grid.classList.add('js');

  const apply = (value) => {
    let shown = 0;
    cards.forEach((card) => {
      const visible = !value || card.dataset.category === value;
      card.hidden = !visible;
      // Считаем по видимым, иначе после отбора зигзаг сбивается.
      card.classList.toggle('is-low', visible && shown % 2 === 1);
      if (visible) shown += 1;
    });
    if (status) {
      status.textContent = value
        ? `${value}: показано работ — ${shown}`
        : `Показаны все работы — ${shown}`;
    }
  };

  bar.addEventListener('click', (e) => {
    const btn = e.target.closest('.works-filter-btn');
    if (!btn) return;
    buttons.forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));
    apply(btn.dataset.filter);
    track('portfolio_filter', { category: btn.dataset.filter || 'all' });
  });

  apply('');
}

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
  if (prefersReducedMotion) return;

  const targets = [...document.querySelectorAll(
    '.service-card, .route-step, .why-stat-card, .client-item, .faq-item, .contact-panel, .section-head'
  )];
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

// --- Отправка форм ----------------------------------------------------------

const TELEGRAM_LINK =
  '<a href="' + TELEGRAM_URL + '" target="_blank" rel="noopener">Telegram</a>';

async function postLead(endpoint, payload) {
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error('HTTP ' + response.status);
}

// --- Бриф на странице услуги ------------------------------------------------

function initBriefForm() {
  const form = document.getElementById('briefForm');
  const note = document.getElementById('briefNote');
  if (!form || !note) return;

  const defaultNote = note.innerHTML;
  const button = form.querySelector('button[type="submit"]');
  const buttonText = button.querySelector('.btn-text');
  const otherBox = form.querySelector('#brief-goal-other');
  const otherText = form.querySelector('#brief-goal-other-text');
  const goals = [...form.querySelectorAll('input[name="goals"]')];

  // Поле для своей формулировки появляется, только когда отмечено «Другое».
  const syncOther = () => {
    otherText.hidden = !otherBox.checked;
    if (!otherBox.checked) otherText.value = '';
  };
  otherBox.addEventListener('change', syncOther);
  syncOther();

  const setError = (key, input, message) => {
    const box = document.getElementById('err-' + key);
    if (box) {
      box.textContent = message || '';
      box.hidden = !message;
    }
    if (input) input.setAttribute('aria-invalid', message ? 'true' : 'false');
  };

  const required = [
    ['company', 'Укажите название компании'],
    ['budget', 'Укажите месячный бюджет'],
    ['geo', 'Укажите город или регион'],
    ['contact', 'Оставьте телефон или Telegram для связи'],
  ];

  const validate = () => {
    let firstInvalid = null;

    required.forEach(([name, message]) => {
      const input = form.elements[name];
      const empty = !input.value.trim();
      setError(name, input, empty ? message : '');
      if (empty) firstInvalid = firstInvalid || input;
    });

    const chosen = goals.filter((g) => g.checked);
    // «Другое» без пояснения ничего не сообщает, поэтому требуем текст.
    const otherEmpty = otherBox.checked && !otherText.value.trim();
    const goalsError = !chosen.length
      ? 'Выберите хотя бы одну цель'
      : otherEmpty ? 'Опишите цель в поле «Другое»' : '';
    setError('goals', null, goalsError);
    if (goalsError) firstInvalid = firstInvalid || (otherEmpty ? otherText : goals[0]);

    return firstInvalid;
  };

  // До первой попытки отправить форму молчим: человек только начал заполнять,
  // и красные подписи под всеми полями сразу — это придирка, а не помощь.
  // После первой отправки проверяем на каждый ввод, чтобы ошибки гасли сразу.
  let submitted = false;
  const recheck = () => { if (submitted) validate(); };
  form.addEventListener('input', recheck);
  form.addEventListener('change', recheck);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    submitted = true;
    const invalid = validate();
    if (invalid) {
      invalid.focus();
      note.className = 'form-note error';
      note.textContent = 'Проверьте отмеченные поля.';
      return;
    }

    const chosen = goals.filter((g) => g.checked).map((g) => g.value);
    const other = otherText.value.trim();
    const payload = {
      _form: form.elements._form.value,
      company: form.elements.company.value.trim(),
      goals: chosen.map((g) => (g === 'Другое' && other ? 'Другое: ' + other : g)).join(', '),
      budget: form.elements.budget.value.trim(),
      geo: form.elements.geo.value.trim(),
      site: form.elements.site.value.trim(),
      social: form.elements.social.value.trim(),
      contact: form.elements.contact.value.trim(),
      department: form.elements.department.value,
      page: location.pathname,
    };

    const endpoint = form.dataset.endpoint || '';
    if (!endpoint) {
      track('form_blocked', { form: 'brief' });
      note.className = 'form-note error';
      note.innerHTML = 'Отправка брифа пока не подключена. Напишите нам в '
        + TELEGRAM_LINK + ' — ответим сразу.';
      return;
    }

    button.disabled = true;
    buttonText.textContent = 'Отправляем…';
    note.className = 'form-note';
    note.textContent = 'Отправляем бриф…';

    try {
      await postLead(endpoint, payload);
      form.reset();
      syncOther();
      track('generate_lead', { method: 'brief' });
      buttonText.textContent = 'Отправлено ✓';
      note.className = 'form-note success';
      note.textContent = 'Бриф принят. Вернёмся с предложением в течение рабочего дня.';
    } catch (error) {
      track('form_error', { form: 'brief' });
      buttonText.textContent = 'Отправить бриф';
      note.className = 'form-note error';
      note.innerHTML = 'Не удалось отправить бриф. Напишите в ' + TELEGRAM_LINK
        + ' или позвоните нам.';
    } finally {
      button.disabled = false;
      setTimeout(() => {
        buttonText.textContent = 'Отправить бриф';
        note.className = 'form-note';
        note.innerHTML = defaultNote;
      }, 8000);
    }
  });
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
        'Отправка формы пока не подключена. Напишите нам в '
        + TELEGRAM_LINK + ' — ответим сразу.';
      return;
    }

    button.disabled = true;
    buttonText.textContent = 'Отправляем…';
    note.className = 'form-note';
    note.textContent = 'Отправляем заявку…';

    try {
      const payload = Object.fromEntries(new FormData(form));
      payload.page = location.pathname; // видно, с какой страницы пришла заявка

      await postLead(endpoint, payload);

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
        'Не удалось отправить заявку. Напишите в ' + TELEGRAM_LINK
        + ' или позвоните нам.';
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
