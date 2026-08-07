// ===========================
// Sales Hub — interactions
// ===========================

// Куда уходят заявки. Пока пусто — форма работает в режиме заглушки и честно
// предлагает написать в Telegram. Подставьте сюда URL обработчика
// (Formspree, Web3Forms, свой бэкенд или Telegram-бот) — остальной код готов.
const FORM_ENDPOINT = '';

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
});

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

    // Обработчик ещё не подключён: не делаем вид, что заявка ушла.
    if (!FORM_ENDPOINT) {
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
      const response = await fetch(FORM_ENDPOINT, {
        method: 'POST',
        headers: { 'Accept': 'application/json' },
        body: new FormData(form),
      });
      if (!response.ok) throw new Error('HTTP ' + response.status);

      form.reset();
      buttonText.textContent = 'Отправлено ✓';
      note.className = 'form-note success';
      note.textContent = 'Заявка принята. Свяжемся с вами в течение рабочего дня.';
    } catch (error) {
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
