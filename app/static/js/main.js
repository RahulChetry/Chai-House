/* ============================================================
   CHAI HOUSE AI — main.js
   UI interactions, utilities, Chart.js theme
   ============================================================ */

'use strict';

/* ════════════════════════════════════════════════
   1.  SIDEBAR TOGGLE (Mobile)
════════════════════════════════════════════════ */
(function initSidebar() {
  const sidebar   = document.getElementById('sidebar');
  const overlay   = document.getElementById('sidebarOverlay');
  const hamburger = document.getElementById('hamburgerBtn');

  if (!sidebar) return;

  function openSidebar() {
    sidebar.classList.add('open');
    if (overlay) overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  if (hamburger) hamburger.addEventListener('click', openSidebar);
  if (overlay)   overlay.addEventListener('click', closeSidebar);

  // Close on resize to desktop
  window.addEventListener('resize', () => {
    if (window.innerWidth > 768) closeSidebar();
  });
})();

/* ════════════════════════════════════════════════
   2.  ACTIVE NAV LINK HIGHLIGHTING
════════════════════════════════════════════════ */
(function highlightActiveNav() {
  const links = document.querySelectorAll('.nav-link-item');
  const current = window.location.pathname;

  links.forEach(link => {
    const href = link.getAttribute('href');
    if (!href) return;

    // Exact or prefix match
    if (href === current || (href !== '/' && current.startsWith(href))) {
      link.classList.add('active');
    }
  });
})();

/* ════════════════════════════════════════════════
   3.  LIVE DATE/TIME DISPLAY
════════════════════════════════════════════════ */
(function liveClock() {
  const el = document.getElementById('liveDatetime');
  if (!el) return;

  function update() {
    const now = new Date();
    const dateStr = now.toLocaleDateString('en-IN', {
      weekday: 'short', day: '2-digit', month: 'short', year: 'numeric'
    });
    const timeStr = now.toLocaleTimeString('en-IN', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
    el.innerHTML = `<span>${dateStr}</span><br><strong>${timeStr}</strong>`;
  }

  update();
  setInterval(update, 1000);
})();

/* ════════════════════════════════════════════════
   4.  TOAST NOTIFICATION SYSTEM
════════════════════════════════════════════════ */
const Toast = (() => {
  let container = null;

  function getContainer() {
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  const icons = {
    success: '✅',
    error:   '❌',
    warning: '⚠️',
    info:    'ℹ️',
  };

  function show(title, message = '', type = 'info', duration = 4000) {
    const c    = getContainer();
    const item = document.createElement('div');
    item.className = `toast-item ${type}`;
    item.innerHTML = `
      <span class="toast-icon">${icons[type] || icons.info}</span>
      <div class="toast-body">
        <div class="toast-title">${title}</div>
        ${message ? `<div class="toast-msg">${message}</div>` : ''}
      </div>
      <button class="toast-close" aria-label="Close">✕</button>
    `;

    item.querySelector('.toast-close').addEventListener('click', () => dismiss(item));
    c.appendChild(item);

    if (duration > 0) {
      setTimeout(() => dismiss(item), duration);
    }
    return item;
  }

  function dismiss(item) {
    if (!item || !item.parentNode) return;
    item.classList.add('hiding');
    setTimeout(() => item.remove(), 350);
  }

  return { show, dismiss, success: (t,m,d) => show(t,m,'success',d), error: (t,m,d) => show(t,m,'error',d), warning: (t,m,d) => show(t,m,'warning',d), info: (t,m,d) => show(t,m,'info',d) };
})();

window.Toast = Toast;   // expose globally

/* ════════════════════════════════════════════════
   5.  AUTO-DISMISS FLASH MESSAGES
════════════════════════════════════════════════ */
(function autoFlash() {
  document.querySelectorAll('.flash-alert').forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity .4s ease, margin .4s ease';
      alert.style.opacity = '0';
      alert.style.marginTop = `-${alert.offsetHeight}px`;
      setTimeout(() => alert.remove(), 450);
    }, 5000);
  });
})();

/* ════════════════════════════════════════════════
   6.  CONFIRM DELETE DIALOGS
════════════════════════════════════════════════ */
document.addEventListener('click', e => {
  const btn = e.target.closest('[data-confirm]');
  if (!btn) return;
  const msg = btn.dataset.confirm || 'Are you sure you want to delete this?';
  if (!confirm(msg)) {
    e.preventDefault();
    e.stopPropagation();
  }
});

/* ════════════════════════════════════════════════
   7.  FORM VALIDATION HELPERS
════════════════════════════════════════════════ */
const FormHelper = {
  /**
   * Mark a field as invalid with a message.
   */
  setError(field, message) {
    field.classList.add('is-invalid');
    field.classList.remove('is-valid');
    let fb = field.nextElementSibling;
    if (!fb || !fb.classList.contains('invalid-feedback')) {
      fb = document.createElement('div');
      fb.className = 'invalid-feedback';
      field.parentNode.insertBefore(fb, field.nextSibling);
    }
    fb.textContent = message;
  },

  setValid(field) {
    field.classList.remove('is-invalid');
    field.classList.add('is-valid');
    const fb = field.nextElementSibling;
    if (fb && fb.classList.contains('invalid-feedback')) fb.remove();
  },

  clearAll(form) {
    form.querySelectorAll('.is-invalid, .is-valid').forEach(el => {
      el.classList.remove('is-invalid', 'is-valid');
    });
    form.querySelectorAll('.invalid-feedback').forEach(el => el.remove());
  },

  validateRequired(form) {
    let valid = true;
    form.querySelectorAll('[required]').forEach(field => {
      if (!field.value.trim()) {
        this.setError(field, 'This field is required.');
        valid = false;
      } else {
        this.setValid(field);
      }
    });
    return valid;
  }
};

window.FormHelper = FormHelper;

/* ════════════════════════════════════════════════
   8.  DATE FORMATTING UTILITIES
════════════════════════════════════════════════ */
const DateUtils = {
  format(dateStr, options = {}) {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric', ...options
    });
  },

  today() {
    return new Date().toISOString().split('T')[0];
  },

  relative(dateStr) {
    const d   = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now - d) / 864e5);
    if (diff === 0) return 'Today';
    if (diff === 1) return 'Yesterday';
    return `${diff} days ago`;
  }
};

window.DateUtils = DateUtils;

/* ════════════════════════════════════════════════
   9.  CURRENCY FORMATTING
════════════════════════════════════════════════ */
const Currency = {
  format(amount, decimals = 2) {
    const n = parseFloat(amount) || 0;
    return '₹' + n.toLocaleString('en-IN', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  },

  parse(str) {
    return parseFloat(str.replace(/[₹,\s]/g, '')) || 0;
  }
};

window.Currency = Currency;

/* ════════════════════════════════════════════════
   10.  CHART.JS DEFAULT THEME (Brand Colors)
════════════════════════════════════════════════ */
(function configureChartDefaults() {
  if (typeof Chart === 'undefined') return;

  const brandColors = [
    '#3D1A08', '#C47B3D', '#D4A843', '#6B3A2A',
    '#F5E6C4', '#8B4513', '#A0522D', '#CD853F',
    '#DEB887', '#D2691E'
  ];

  Chart.defaults.font.family  = "'Poppins', sans-serif";
  Chart.defaults.font.size    = 12;
  Chart.defaults.color        = '#7D5A4A';

  Chart.defaults.plugins.legend.position = 'bottom';
  Chart.defaults.plugins.legend.labels.boxWidth  = 12;
  Chart.defaults.plugins.legend.labels.padding   = 16;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;

  Chart.defaults.plugins.tooltip.backgroundColor = '#3D1A08';
  Chart.defaults.plugins.tooltip.titleColor      = '#D4A843';
  Chart.defaults.plugins.tooltip.bodyColor       = '#FDF6EC';
  Chart.defaults.plugins.tooltip.borderColor     = '#C47B3D';
  Chart.defaults.plugins.tooltip.borderWidth     = 1;
  Chart.defaults.plugins.tooltip.cornerRadius    = 8;
  Chart.defaults.plugins.tooltip.padding         = 10;

  Chart.defaults.scale.grid.color  = 'rgba(61,26,8,.07)';
  Chart.defaults.scale.ticks.color = '#7D5A4A';

  // Expose brand palette
  window.ChartBrandColors = brandColors;
})();

/* ════════════════════════════════════════════════
   11.  TABLE SEARCH/FILTER
════════════════════════════════════════════════ */
(function initTableSearch() {
  document.querySelectorAll('[data-table-search]').forEach(input => {
    const targetId = input.dataset.tableSearch;
    const table    = document.getElementById(targetId);
    if (!table) return;

    input.addEventListener('input', () => {
      const q = input.value.toLowerCase().trim();
      table.querySelectorAll('tbody tr').forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(q) ? '' : 'none';
      });

      // Show/hide "no results" row
      let visibleRows = [...table.querySelectorAll('tbody tr')].filter(r => r.style.display !== 'none');
      let noResult    = table.querySelector('.no-search-result');
      if (visibleRows.length === 0) {
        if (!noResult) {
          const colspan = table.querySelector('thead tr')?.children.length || 6;
          const tr = document.createElement('tr');
          tr.className = 'no-search-result';
          tr.innerHTML = `<td colspan="${colspan}" class="text-center py-4 text-muted-chai">
            <i class="fa fa-search me-2"></i>No results found for "<strong>${input.value}</strong>"
          </td>`;
          table.querySelector('tbody').appendChild(tr);
        }
      } else {
        if (noResult) noResult.remove();
      }
    });
  });
})();

/* ════════════════════════════════════════════════
   12.  REVENUE / PROFIT LIVE PREVIEW (Sale Form)
════════════════════════════════════════════════ */
(function saleFormPreview() {
  const qtyInput   = document.getElementById('quantity');
  const priceInput = document.getElementById('unit_price');
  const costInput  = document.getElementById('unit_cost');
  const revEl      = document.getElementById('revenuePreview');
  const profitEl   = document.getElementById('profitPreview');

  if (!qtyInput || !priceInput || !revEl) return;

  function update() {
    const qty    = parseFloat(qtyInput.value)   || 0;
    const price  = parseFloat(priceInput.value) || 0;
    const cost   = costInput ? (parseFloat(costInput.value) || 0) : 0;
    const revenue = qty * price;
    const profit  = revenue - (qty * cost);

    revEl.textContent = Currency.format(revenue);
    if (profitEl) {
      profitEl.textContent = Currency.format(profit);
      profitEl.style.color = profit >= 0 ? '#2E7D32' : '#C62828';
    }
  }

  [qtyInput, priceInput, costInput].forEach(el => {
    if (el) el.addEventListener('input', update);
  });

  update();
})();

/* ════════════════════════════════════════════════
   13.  PRODUCT PRICE AUTO-FILL (Sale Form)
════════════════════════════════════════════════ */
(function productAutoFill() {
  const productSelect = document.getElementById('product_id');
  if (!productSelect) return;

  const priceInput = document.getElementById('unit_price');
  const costInput  = document.getElementById('unit_cost');

  // Products data injected via data-products attribute on select
  let products = {};
  try {
    const raw = productSelect.dataset.products;
    if (raw) products = JSON.parse(raw);
  } catch(_) {}

  productSelect.addEventListener('change', () => {
    const pid = productSelect.value;
    if (products[pid]) {
      if (priceInput) priceInput.value = products[pid].price || '';
      if (costInput)  costInput.value  = products[pid].cost  || '';

      // Trigger preview recalc
      priceInput && priceInput.dispatchEvent(new Event('input'));
    }
  });
})();

/* ════════════════════════════════════════════════
   14.  LOAD DEMO DATA (Dashboard empty state)
════════════════════════════════════════════════ */
(function loadDemoData() {
  const btn = document.getElementById('loadDemoBtn');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-chai" style="width:16px;height:16px;border-width:2px;"></span> Loading…';

    try {
      const res = await fetch('/api/load-demo', { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      const data = await res.json();
      if (data.success) {
        Toast.success('Demo Data Loaded!', 'Page will refresh in a moment…');
        setTimeout(() => location.reload(), 1500);
      } else {
        throw new Error(data.message || 'Failed to load demo data');
      }
    } catch (err) {
      Toast.error('Error', err.message);
      btn.disabled = false;
      btn.innerHTML = '<i class="fa fa-database me-2"></i>Load Demo Data';
    }
  });
})();

/* ════════════════════════════════════════════════
   15.  ML TRAINING PROGRESS INDICATOR
════════════════════════════════════════════════ */
(function mlTrainButton() {
  const form = document.getElementById('trainModelsForm');
  if (!form) return;

  form.addEventListener('submit', () => {
    const btn = form.querySelector('[type=submit]');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner-chai" style="width:18px;height:18px;border-width:2px;"></span> Training Models… This may take a moment`;
    }

    // Show overlay
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
      <div class="loading-content">
        <div class="spinner-chai" style="width:56px;height:56px;border-width:4px;"></div>
        <div class="loading-text">🧠 Training ML Models…<br><small class="text-muted-chai">Please don't close this page</small></div>
      </div>`;
    document.body.appendChild(overlay);
  });
})();

/* ════════════════════════════════════════════════
   16.  SET TODAY AS DEFAULT DATE
════════════════════════════════════════════════ */
(function defaultDates() {
  document.querySelectorAll('input[type="date"][data-default-today]').forEach(input => {
    if (!input.value) input.value = DateUtils.today();
  });
})();

/* ════════════════════════════════════════════════
   17.  INVENTORY INLINE STOCK UPDATE MODAL HELPER
════════════════════════════════════════════════ */
(function inventoryStockUpdate() {
  document.querySelectorAll('[data-update-stock]').forEach(btn => {
    btn.addEventListener('click', () => {
      const id   = btn.dataset.updateStock;
      const name = btn.dataset.name || 'Ingredient';
      const modalEl = document.getElementById('updateStockModal');
      if (!modalEl) return;

      modalEl.querySelector('#stockIngredientId').value = id;
      modalEl.querySelector('#stockIngredientName').textContent = name;
      modalEl.querySelector('#stockQtyInput').value = '';
    });
  });
})();

/* ════════════════════════════════════════════════
   18.  SMOOTH PAGE TRANSITIONS
════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  document.body.style.opacity = '0';
  document.body.style.transition = 'opacity .25s ease';
  requestAnimationFrame(() => { document.body.style.opacity = '1'; });
});
