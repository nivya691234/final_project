/**
 * dashboard/static/js/animations.js
 * Enhanced animations and visual effects for data updates
 */

/** ═════════════════════════════════════════════════════════════════
    SMOOTH VALUE UPDATE ANIMATIONS
    ═════════════════════════════════════════════════════════════════ */

function animateValueChange(element, newValue, options = {}) {
  const oldValue = parseFloat(element.textContent) || 0;
  const duration = options.duration || 800;
  const startTime = performance.now();

  const animate = (currentTime) => {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);

    // Easing function
    const easeOutCubic = 1 - Math.pow(1 - progress, 3);

    let displayValue;
    if (typeof newValue === 'number') {
      displayValue = Math.round((oldValue + (newValue - oldValue) * easeOutCubic) * 10) / 10;
    } else {
      displayValue = newValue;
    }

    element.textContent = isNaN(displayValue) ? newValue : displayValue;

    if (progress < 1) {
      requestAnimationFrame(animate);
    }
  };

  requestAnimationFrame(animate);
}

/** ═════════════════════════════════════════════════════════════════
    CARD ENTRANCE ANIMATIONS
    ═════════════════════════════════════════════════════════════════ */

function animateCardEntrance(element, delay = 0) {
  element.style.opacity = '0';
  element.style.transform = 'translateY(20px)';
  element.style.transition = `all 0.6s cubic-bezier(0.4, 0, 0.2, 1) ${delay}ms`;

  setTimeout(() => {
    element.style.opacity = '1';
    element.style.transform = 'translateY(0)';
  }, 10);
}

function animateCardsGrid(container) {
  const cards = container.querySelectorAll('.kpi-card, .chart-card, .rec-card, .table-card');
  cards.forEach((card, index) => {
    animateCardEntrance(card, index * 50);
  });
}

/** ═════════════════════════════════════════════════════════════════
    LOADING INDICATORS
    ═════════════════════════════════════════════════════════════════ */

function createSpinner() {
  const spinner = document.createElement('div');
  spinner.className = 'spinner';
  return spinner;
}

function createSkeletonLoader(width = '100%', height = '20px') {
  const skeleton = document.createElement('div');
  skeleton.className = 'skeleton';
  skeleton.style.width = width;
  skeleton.style.height = height;
  skeleton.style.marginBottom = '10px';
  return skeleton;
}

function addLoadingState(container, duration = 1500) {
  container.style.opacity = '0.6';
  container.style.pointerEvents = 'none';

  const loader = createSpinner();
  loader.style.position = 'absolute';
  loader.style.top = '50%';
  loader.style.left = '50%';
  loader.style.transform = 'translate(-50%, -50%)';
  loader.style.zIndex = '10';

  container.parentElement.style.position = 'relative';
  container.parentElement.appendChild(loader);

  return () => {
    container.style.opacity = '1';
    container.style.pointerEvents = 'auto';
    loader.remove();
  };
}

/** ═════════════════════════════════════════════════════════════════
    PROGRESS BAR ANIMATIONS
    ═════════════════════════════════════════════════════════════════ */

function animateProgressBar(barElement, targetPercentage, duration = 1000) {
  const startPercentage = parseFloat(barElement.style.width) || 0;
  const startTime = performance.now();

  const animate = (currentTime) => {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);

    // Cubic easing
    const easeOutCubic = 1 - Math.pow(1 - progress, 3);
    const currentPercent = startPercentage + (targetPercentage - startPercentage) * easeOutCubic;

    barElement.style.width = Math.min(Math.max(currentPercent, 0), 100) + '%';

    if (progress < 1) {
      requestAnimationFrame(animate);
    }
  };

  requestAnimationFrame(animate);
}

/** ═════════════════════════════════════════════════════════════════
    BADGE STATUS ANIMATIONS
    ═════════════════════════════════════════════════════════════════ */

function pulseBadge(badgeElement, color = '#3b82f6') {
  badgeElement.style.animation = 'none';
  // Trigger reflow
  void badgeElement.offsetWidth;
  badgeElement.style.animation = `pulse-badge 0.5s ease`;
  badgeElement.style.boxShadow = `0 0 12px ${color}`;
}

function updateBadgeWithAnimation(badgeElement, newText, newColor) {
  badgeElement.style.animation = 'fadeOut 0.2s ease';

  setTimeout(() => {
    badgeElement.textContent = newText;
    badgeElement.style.animation = 'fadeIn 0.2s ease';
    pulseBadge(badgeElement, newColor);
  }, 100);
}

/** ═════════════════════════════════════════════════════════════════
    TABLE ROW HIGHLIGHTING
    ═════════════════════════════════════════════════════════════════ */

function highlightTableRow(row, color = 'rgba(59, 130, 246, 0.2)', duration = 1000) {
  const originalBg = row.style.backgroundColor;

  row.style.transition = `background-color 0.3s ease`;
  row.style.backgroundColor = color;

  setTimeout(() => {
    row.style.backgroundColor = originalBg;
  }, duration);
}

function highlightNewData(tbody) {
  const rows = tbody.querySelectorAll('tr');
  if (rows.length > 0) {
    highlightTableRow(rows[0], 'rgba(16, 185, 129, 0.15)', 1500);
  }
}

/** ═════════════════════════════════════════════════════════════════
    TOAST NOTIFICATIONS
    ═════════════════════════════════════════════════════════════════ */

function showToast(message, type = 'info', duration = 3000) {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  toast.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    padding: 14px 20px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.9rem;
    z-index: 3000;
    animation: slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    border-left: 4px solid;
    max-width: 400px;
  `;

  const colorMap = {
    success: { bg: '#15b98118', text: '#10b981', border: '#10b981' },
    error: { bg: '#ef444418', text: '#ef4444', border: '#ef4444' },
    warning: { bg: '#f59e0b18', text: '#f59e0b', border: '#f59e0b' },
    info: { bg: '#06b6d418', text: '#06b6d4', border: '#06b6d4' }
  };

  const colors = colorMap[type] || colorMap.info;
  toast.style.backgroundColor = colors.bg;
  toast.style.color = colors.text;
  toast.style.borderLeftColor = colors.border;

  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'slideOutRight 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards';
    setTimeout(() => toast.remove(), 400);
  }, duration);
}

/** ═════════════════════════════════════════════════════════════════
    RIPPLE EFFECT ON CLICK
    ═════════════════════════════════════════════════════════════════ */

function addRippleEffect(event) {
  const button = event.currentTarget;
  const rect = button.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height);
  const x = event.clientX - rect.left - size / 2;
  const y = event.clientY - rect.top - size / 2;

  const ripple = document.createElement('span');
  ripple.style.cssText = `
    position: absolute;
    width: ${size}px;
    height: ${size}px;
    background: rgba(255, 255, 255, 0.5);
    border-radius: 50%;
    left: ${x}px;
    top: ${y}px;
    pointer-events: none;
    animation: ripple-expand 0.6s ease-out;
  `;

  button.style.position = 'relative';
  button.style.overflow = 'hidden';
  button.appendChild(ripple);

  setTimeout(() => ripple.remove(), 600);
}

/** ═════════════════════════════════════════════════════════════════
    CHART VALUE ANIMATIONS
    ═════════════════════════════════════════════════════════════════ */

function animateChartUpdate(chart, duration = 500) {
  if (!chart) return;

  // Add animation effect
  const canvas = chart.canvas;
  if (!canvas) return;

  canvas.style.animation = 'fadeIn 0.5s ease';
  canvas.style.opacity = '1';
}

/** ═════════════════════════════════════════════════════════════════
    KEYFRAME ANIMATIONS (CSS)
    ═════════════════════════════════════════════════════════════════ */

const animationStyles = `
  @keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-3px); }
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes fadeOut {
    from { opacity: 1; }
    to { opacity: 0; }
  }

  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes slideInRight {
    from {
      opacity: 0;
      transform: translateX(30px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  @keyframes slideOutRight {
    from {
      opacity: 1;
      transform: translateX(0);
    }
    to {
      opacity: 0;
      transform: translateX(30px);
    }
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(-20px) scale(0.95);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  @keyframes shimmer {
    0% { background-position: -1000px 0; }
    100% { background-position: 1000px 0; }
  }

  @keyframes pulse-badge {
    0% {
      box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
    }
    70% {
      box-shadow: 0 0 0 10px rgba(59, 130, 246, 0);
    }
    100% {
      box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
    }
  }

  @keyframes ripple-expand {
    to {
      transform: scale(4);
      opacity: 0;
    }
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 3px solid var(--border);
    border-top-color: var(--accent-blue);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .spinner-sm {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    display: inline-block;
    margin-right: 6px;
  }

  .skeleton {
    background: linear-gradient(90deg, var(--bg-elevated) 0%, var(--border) 50%, var(--bg-elevated) 100%);
    background-size: 1000px 100%;
    animation: shimmer 1.5s infinite;
    border-radius: var(--radius-sm);
  }

  .toast {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .toast::before {
    content: '';
    width: 4px;
    height: 100%;
    border-radius: 2px;
  }
`;

// Inject animation styles
if (!document.getElementById('animation-styles')) {
  const style = document.createElement('style');
  style.id = 'animation-styles';
  style.textContent = animationStyles;
  document.head.appendChild(style);
}

/** ═════════════════════════════════════════════════════════════════
    UTILITY HELPERS
    ═════════════════════════════════════════════════════════════════ */

function debounce(func, delay) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), delay);
  };
}

function throttle(func, limit) {
  let inThrottle;
  return function (...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    animateValueChange,
    animateCardEntrance,
    animateCardsGrid,
    createSpinner,
    createSkeletonLoader,
    addLoadingState,
    animateProgressBar,
    pulseBadge,
    updateBadgeWithAnimation,
    highlightTableRow,
    highlightNewData,
    showToast,
    addRippleEffect,
    animateChartUpdate,
    debounce,
    throttle
  };
}
