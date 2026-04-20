/**
 * dashboard/static/js/charts.js
 * Shared utility helpers used by all dashboard pages.
 * Enhanced with smooth animations and visual effects.
 * Chart.js instances are created per-page in their own <script> blocks.
 */

/* ── Countdown / auto-refresh ─────────────────────────────── */
function startRefreshCountdown(seconds, refreshFn) {
  let remaining = seconds;
  const badge = document.getElementById('refresh-countdown');
  const tick = () => {
    if (badge) badge.textContent = `Auto-refresh: ${remaining}s`;
    if (remaining <= 0) {
      remaining = seconds;
      refreshFn();
    } else {
      remaining--;
    }
  };
  tick();
  setInterval(tick, 1000);
}

/* ── Status dot ───────────────────────────────────────────── */
function updateStatusDot(online) {
  const dot  = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  if (!dot) return;
  if (online) {
    dot.classList.remove('offline');
    if (text) text.textContent = 'Connected';
  } else {
    dot.classList.add('offline');
    if (text) text.textContent = 'Disconnected';
  }
}

/* ── Generic DOM helpers ──────────────────────────────────── */
function setText(id, value) {
  const el = document.getElementById(id);
  if (el) {
    // Animate value change
    if (typeof value === 'number' && el.textContent && el.textContent !== '—') {
      animateValueChange(el, value, { duration: 600 });
    } else {
      el.textContent = value;
    }
  }
}

function setBar(id, pct) {
  const el = document.getElementById(id);
  if (el) {
    animateProgressBar(el, Math.min(Math.max(pct, 0), 100), 800);
  }
}

/**
 * Set the text and colour class of a kpi-badge element with animation.
 * @param {string} id   - element ID
 * @param {string} val  - CRITICAL | HIGH | MEDIUM | LOW | NORMAL
 */
function setBadge(id, val) {
  const el = document.getElementById(id);
  if (!el) return;
  
  const map = {
    CRITICAL: 'badge-danger',
    HIGH:     'badge-warning',
    MEDIUM:   'badge-info',
    LOW:      'badge-ok',
    NORMAL:   'badge-normal',
  };

  const oldClass = Array.from(el.classList).find(c => c.startsWith('badge-'));
  const newClass = map[val] || 'badge-normal';
  
  // Only animate if class changed
  if (oldClass !== newClass) {
    el.textContent = val;
    el.className   = 'kpi-badge';
    el.classList.add(newClass);
    pulseBadge(el);
  }
}

/**
 * Colour a kpi-card based on a percentage value with smooth transition.
 * @param {string} id    - card element ID
 * @param {number} value - current percentage
 * @param {number} high  - danger threshold
 * @param {number} mid   - warning threshold
 */
function colorCard(id, value, high, mid) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('alert-danger', 'alert-warning', 'alert-ok');
  if (value >= high)      el.classList.add('alert-danger');
  else if (value >= mid)  el.classList.add('alert-warning');
  else                    el.classList.add('alert-ok');
}

/* ── Chart update helpers ─────────────────────────────────── */

/**
 * Update a single-dataset Chart.js line chart with smooth animation.
 */
function updateChart(chart, labels, data) {
  if (!chart) return;
  chart.data.labels            = labels;
  chart.data.datasets[0].data = data;
  animateChartUpdate(chart, 500);
  chart.update('none');
}

/**
 * Update a two-dataset Chart.js network chart with smooth animation.
 */
function updateNetChart(chart, labels, recv, send) {
  if (!chart) return;
  chart.data.labels            = labels;
  chart.data.datasets[0].data = recv;
  chart.data.datasets[1].data = send;
  animateChartUpdate(chart, 500);
  chart.update('none');
}

/* ── Chart defaults ───────────────────────────────────────── */
if (window.Chart) {
  Chart.defaults.color            = '#cbd5e1';
  Chart.defaults.font.family      = 'Inter, sans-serif';
  Chart.defaults.font.size        = 11;
  Chart.defaults.plugins.tooltip.backgroundColor = '#242d3d';
  Chart.defaults.plugins.tooltip.borderColor      = '#3c4556';
  Chart.defaults.plugins.tooltip.borderWidth      = 1;
  Chart.defaults.plugins.tooltip.padding          = 12;
  Chart.defaults.plugins.tooltip.titleFont.weight = '700';
  Chart.defaults.plugins.legend.display           = false;
}
