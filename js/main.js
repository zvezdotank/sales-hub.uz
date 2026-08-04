// ===========================
// Sales Hub — interactions
// ===========================

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
  document.getElementById('year').textContent = new Date().getFullYear();
});

// Starfield
function initStars() {
  const container = document.getElementById('stars');
  const count = window.innerWidth < 700 ? 60 : 130;
  const frag = document.createDocumentFragment();
  for (let i = 0; i < count; i++) {
    const star = document.createElement('span');
    const size = Math.random() * 1.6 + 0.6;
    star.style.top = Math.random() * 100 + '%';
    star.style.left = Math.random() * 100 + '%';
    star.style.width = size + 'px';
    star.style.height = size + 'px';
    star.style.animationDelay = (Math.random() * 4) + 's';
    star.style.animationDuration = (3 + Math.random() * 3) + 's';
    frag.appendChild(star);
  }
  container.appendChild(frag);
}

// Header background on scroll
function initHeaderScroll() {
  const header = document.getElementById('siteHeader');
  const toggle = () => {
    header.classList.toggle('scrolled', window.scrollY > 20);
  };
  toggle();
  window.addEventListener('scroll', toggle, { passive: true });
}

// Mobile nav
function initMobileNav() {
  const toggle = document.getElementById('navToggle');
  const nav = document.getElementById('mainNav');
  toggle.addEventListener('click', () => {
    toggle.classList.toggle('open');
    nav.classList.toggle('open');
  });
  nav.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      toggle.classList.remove('open');
      nav.classList.remove('open');
    });
  });
}

// Reveal-on-scroll for sections
function initReveal() {
  const targets = document.querySelectorAll(
    '.service-card, .route-step, .why-stat-card, .contact-panel, .section-head'
  );
  targets.forEach(el => el.classList.add('reveal'));

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });

  targets.forEach(el => observer.observe(el));
}

// Animate hero stat bars once visible
function initStatBars() {
  const rows = document.querySelectorAll('.stat-row');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const row = entry.target;
        const value = row.getAttribute('data-value');
        const fill = row.querySelector('.stat-fill');
        requestAnimationFrame(() => {
          fill.style.width = value + '%';
        });
        observer.unobserve(row);
      }
    });
  }, { threshold: 0.3 });
  rows.forEach(row => observer.observe(row));
}

// Draw the process route line when in view
function initRouteLine() {
  const line = document.querySelector('.route-line-fill');
  if (!line) return;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.4 });
  observer.observe(line);
}

// Count-up numbers in "why" section
function initCounters() {
  const nums = document.querySelectorAll('.why-stat-num');
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCount(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });
  nums.forEach(n => observer.observe(n));
}

function animateCount(el) {
  const target = parseInt(el.getAttribute('data-count'), 10);
  const suffix = el.getAttribute('data-suffix') || '';
  const isDecimalX = suffix === 'x';
  const duration = 1400;
  const start = performance.now();

  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    let value = target * eased;
    if (isDecimalX) {
      el.textContent = (value / 10).toFixed(1) + 'x';
    } else {
      el.textContent = Math.round(value) + suffix;
    }
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

// Scroll-to-top button
function initScrollTop() {
  const btn = document.getElementById('scrollTop');
  window.addEventListener('scroll', () => {
    btn.classList.toggle('visible', window.scrollY > 600);
  }, { passive: true });
  btn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

// Contact form (client-side only placeholder)
function initContactForm() {
  const form = document.getElementById('contactForm');
  const note = document.getElementById('formNote');
  if (!form) return;

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const submitBtn = form.querySelector('button[type="submit"] .btn-text');
    submitBtn.textContent = 'Отправлено ✓';
    note.textContent = 'Заявка принята. Мы свяжемся с вами в течение рабочего дня.';
    note.classList.add('success');
    form.reset();
    setTimeout(() => {
      submitBtn.textContent = 'Отправить заявку';
    }, 3000);
  });
}
