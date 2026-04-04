/**
 * Environmental Sentinel — Frontend Interactivity
 * Scroll animations, counters, FAQ, mobile menu, live API data
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Lucide icons
  if (window.lucide) lucide.createIcons();

  initNavbar();
  initScrollAnimations();
  initCounters();
  initFAQ();
  initMobileMenu();
  fetchLiveData();
});

// ── Navbar scroll effect ──
function initNavbar() {
  const navbar = document.getElementById('navbar');
  if (!navbar) return;

  window.addEventListener('scroll', () => {
    navbar.classList.toggle('scrolled', window.scrollY > 60);
  }, { passive: true });

  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
      const id = link.getAttribute('href');
      if (id === '#') return;
      const target = document.querySelector(id);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        document.getElementById('nav-links')?.classList.remove('active');
        document.getElementById('hamburger')?.classList.remove('active');
      }
    });
  });
}

// ── Scroll animations ──
function initScrollAnimations() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.animate-on-scroll').forEach(el => observer.observe(el));
}

// ── Counter animation ──
function initCounters() {
  const counters = document.querySelectorAll('.stat-number[data-target]');
  if (!counters.length) return;
  let animated = false;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !animated) {
        animated = true;
        counters.forEach(el => {
          const target = parseInt(el.dataset.target);
          const suffix = el.dataset.suffix || '';
          const start = performance.now();
          const duration = 1400;
          (function update(now) {
            const p = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - p, 3);
            el.textContent = Math.round(target * eased) + suffix;
            if (p < 1) requestAnimationFrame(update);
          })(start);
        });
        observer.disconnect();
      }
    });
  }, { threshold: 0.3 });

  const stats = document.getElementById('stats');
  if (stats) observer.observe(stats);
}

// ── FAQ accordion ──
function initFAQ() {
  document.querySelectorAll('.faq-item').forEach(item => {
    item.querySelector('.faq-question')?.addEventListener('click', () => {
      const isActive = item.classList.contains('active');
      document.querySelectorAll('.faq-item').forEach(o => {
        o.classList.remove('active');
        const a = o.querySelector('.faq-answer');
        if (a) a.style.maxHeight = '0';
      });
      if (!isActive) {
        item.classList.add('active');
        const answer = item.querySelector('.faq-answer');
        if (answer) answer.style.maxHeight = answer.scrollHeight + 'px';
      }
    });
  });
}

// ── Mobile menu ──
function initMobileMenu() {
  const hamburger = document.getElementById('hamburger');
  const navLinks = document.getElementById('nav-links');
  if (!hamburger || !navLinks) return;
  hamburger.addEventListener('click', () => {
    hamburger.classList.toggle('active');
    navLinks.classList.toggle('active');
  });
}

// ── Live API data fetch ──
const API = window.location.origin;

async function fetchLiveData() {
  try {
    const res = await fetch(`${API}/api/system/health`, { signal: AbortSignal.timeout(4000) });
    if (!res.ok) return;
    const h = await res.json();

    const sync = document.getElementById('live-sync');
    if (sync) {
      const s = h.uptime_seconds;
      sync.textContent = s < 60 ? 'Just now' : s < 3600 ? `${Math.floor(s/60)}m ago` : `${Math.floor(s/3600)}h ago`;
    }
  } catch (_) { /* backend offline — static fallback in HTML */ }

  try {
    const res = await fetch(`${API}/api/alerts?limit=5`, { signal: AbortSignal.timeout(4000) });
    if (!res.ok) return;
    const data = await res.json();
    if (data.alerts && data.alerts.length > 0) {
      const feed = document.getElementById('alert-feed');
      if (!feed) return;
      feed.innerHTML = '';
      data.alerts.slice(0, 4).forEach(a => {
        const sev = a.severity || 'medium';
        const row = document.createElement('div');
        row.className = `alert-row ${sev === 'critical' ? 'critical' : sev === 'high' ? 'high' : sev === 'medium' ? 'medium' : 'low-sev'}`;
        row.innerHTML = `
          <span class="alert-severity ${sev}">${sev}</span>
          <span class="alert-text">${a.title || a.description || ''}</span>
          <span class="alert-zone">${a.zone_name || a.zone_id || ''}</span>
          <span class="alert-time mono">${formatTime(a.timestamp)}</span>`;
        feed.appendChild(row);
      });
      // Re-init lucide for any new icons
      if (window.lucide) lucide.createIcons();
    }
  } catch (_) { /* use static fallback */ }
}

function formatTime(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    const diff = (Date.now() - d.getTime()) / 3600000;
    if (diff < 1) return `${Math.round(diff * 60)}m ago`;
    if (diff < 24) return `${Math.round(diff)}h ago`;
    return `${Math.round(diff / 24)}d ago`;
  } catch (_) { return ts; }
}
