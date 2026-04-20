// Quick Reference - Dashboard Animation & Icon System

// ═══════════════════════════════════════════════════════════════════════════════
// SVG ICONS
// ═══════════════════════════════════════════════════════════════════════════════

// Icons are AUTOMATICALLY replaced on page load!
// All emoji are converted to SVG icons by icons.js

// Manual icon creation:
const homeIcon = createSVGIcon('home', { size: '24px' });
container.appendChild(homeIcon);

// Available icons:
// Navigation: home, processes, search, chart, bulb, crosshair
// Status: signal, alertTriangle, alertCircle, checkCircle, info
// Metrics: cpu, memory, disk, network, activity, trending, downTrend
// Actions: play, pause, stop, refresh, settings, zap, x, menu, clock

// ═══════════════════════════════════════════════════════════════════════════════
// ANIMATION FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

// SMOOTH VALUE UPDATES (Replaces setText for numbers)
animateValueChange(element, newValue, { duration: 800 });
// Example: animateValueChange(cpuElement, 65.5, { duration: 600 });

// PROGRESS BAR FILL
animateProgressBar(barElement, percentage, duration);
// Example: animateProgressBar(memoryBar, 82, 800);

// BADGE UPDATES (With glow pulse)
updateBadgeWithAnimation(badge, 'CRITICAL', '#ef4444');
// Example: updateBadgeWithAnimation(riskBadge, 'HIGH', '#f59e0b');

// TABLE ROW HIGHLIGHT
highlightTableRow(row, color, duration);
// Example: highlightTableRow(processRow, 'rgba(59, 130, 246, 0.2)', 1500);

// HIGHLIGHT NEW DATA
highlightNewData(tableBody);
// Highlights first row (newest data)

// TOAST NOTIFICATIONS
showToast(message, type, duration);
// Types: 'success', 'error', 'warning', 'info'
// Example: showToast('Process restarted!', 'success', 3000);

// LOADING STATE MANAGEMENT
const removeLoading = addLoadingState(container);
// Do async work...
setTimeout(removeLoading, 2000); // Remove when done

// ═══════════════════════════════════════════════════════════════════════════════
// ENHANCED CHART.JS HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

// These are already enhanced with animations!

// Animate a single-dataset chart
updateChart(chart, labels, data);
// Numbers smoothly update, animation plays automatically

// Animate a two-dataset chart (network send/recv)
updateNetChart(chart, labels, recvData, sendData);

// Set badge with animation
setBadge(id, value);
// Example: setBadge('pred-badge', 'CRITICAL');
// Automatically pulses red with glow effect

// Color card by value
colorCard(id, value, highThreshold, midThreshold);
// Example: colorCard('card-cpu', 85, 80, 50);

// ═════════════════════════════════════════════════════════════════════════════════
// CSS ANIMATION CLASSES (Add these directly to HTML)
// ═════════════════════════════════════════════════════════════════════════════════

// Spinner (rotating circle)
<div class="spinner"></div>

// Small spinner for buttons
<span class="spinner-sm"></span>Loading...

// Skeleton loader (shimmer effect)
<div class="skeleton" style="width: 100%; height: 20px;"></div>

// ═════════════════════════════════════════════════════════════════════════════════
// COMMON USE CASES IN YOUR DASHBOARD
// ═════════════════════════════════════════════════════════════════════════════════

// 1. UPDATE KPI VALUE WITH ANIMATION
function updateKPI(id, newValue) {
  const element = document.getElementById(id);
  animateValueChange(element, newValue, { duration: 600 });
}

// 2. UPDATE PROGRESS BAR
function updateMetric(barId, percent) {
  const bar = document.getElementById(barId);
  animateProgressBar(bar, percent, 800);
}

// 3. SHOW SOMETHING AND HIGHLIGHT IT (e.g., new row)
function addAndHighlightRow(tableBody, rowHTML) {
  const tr = document.createElement('tr');
  tr.innerHTML = rowHTML;
  tableBody.insertBefore(tr, tableBody.firstChild);
  
  // Highlight it
  highlightTableRow(tr, 'rgba(16, 185, 129, 0.2)', 2000);
}

// 4. SHOW WARNING WHEN CPU IS HIGH
function checkCPU(currentCPU) {
  if (currentCPU > 80) {
    showToast('⚠️ CPU usage is critical!', 'warning', 4000);
    const badge = document.getElementById('cpu-badge');
    updateBadgeWithAnimation(badge, 'CRITICAL', '#ef4444');
  }
}

// 5. LOADING DURING API CALL
async function refreshData() {
  const container = document.getElementById('chart-container');
  const removeLoading = addLoadingState(container);
  
  try {
    const response = await fetch('/api/data');
    const data = await response.json();
    // Update UI with data
    updateChart(chart, data.labels, data.values);
    showToast('Data refreshed!', 'success', 2000);
  } catch (error) {
    showToast('Error loading data', 'error', 3000);
  } finally {
    removeLoading();
  }
}

// ═════════════════════════════════════════════════════════════════════════════════
// COLOR PALETTE (USE THESE IN CSS)
// ═════════════════════════════════════════════════════════════════════════════════

:root {
  --accent-blue: #3b82f6;         /* Primary actions */
  --accent-green: #10b981;        /* Success/OK status */
  --accent-red: #ef4444;          /* Danger/Critical */
  --accent-amber: #f59e0b;        /* Warning/High */
  --accent-cyan: #06b6d4;         /* Secondary info */
  --accent-purple: #8b5cf6;       /* Alternative accent */
  
  --text-primary: #f1f5f9;        /* Main text */
  --text-secondary: #cbd5e1;      /* Secondary text */
  --text-muted: #94a3b8;          /* Disabled/Muted text */
  
  --bg-base: #0f1419;             /* Page background */
  --bg-surface: #1a1e2e;          /* Surface elements */
  --bg-elevated: #242d3d;         /* Elevated containers */
  --bg-card: #15191e;             /* Card backgrounds */
}

// ═════════════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═════════════════════════════════════════════════════════════════════════════════

// Debounce function for event handlers
const debouncedRefresh = debounce(() => {
  refresh();
}, 500);

// Throttle function for frequent events
const throttledScroll = throttle(() => {
  updatePosition();
}, 100);

// ═════════════════════════════════════════════════════════════════════════════════
// BEST PRACTICES
// ═════════════════════════════════════════════════════════════════════════════════

✅ DO:
  - Use animateValueChange() for number updates in KPI cards
  - Use showToast() for user feedback
  - Use highlightTableRow() when new data arrives
  - Use addLoadingState() during async operations
  - Use CSS variables for colors (--accent-blue, etc.)
  - Chain animations for complex sequences
  - Test animations on slow network (DevTools throttle)

❌ DON'T:
  - Use instant setText() for numeric values (use animate functions)
  - Trigger multiple animations on same element simultaneously
  - Use hardcoded colors instead of CSS variables
  - Ignore loading states (users should know when data is loading)
  - Over-animate simple operations
  - Forget to remove loading states after async ops
  - Use animations for performance-critical frequent updates

// ═════════════════════════════════════════════════════════════════════════════════
// DEBUGGING ANIMATIONS
// ═════════════════════════════════════════════════════════════════════════════════

// Slow down animations for inspection (in DevTools Console)
document.documentElement.style.setProperty('--transition', 'all 1s ease');

// Check if element has animation
console.log(window.getComputedStyle(element).animation);

// Verify icons are loaded
console.log(SVG_ICONS.home);

// Test showToast
showToast('Test notification', 'success');

// ═════════════════════════════════════════════════════════════════════════════════

// Need more help? Read STYLING_GUIDE.md for full documentation!
// Questions? Check MODERNIZATION_SUMMARY.md for complete overview
