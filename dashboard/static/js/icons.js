/**
 * dashboard/static/js/icons.js
 * SVG Icon definitions and utilities
 */

const SVG_ICONS = {
    // Navigation & Large Icons
    home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    
    processes: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/><path d="M12 5v14M5 9l14 6M5 15l14-6"/></svg>',
    
    search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>',
    
    chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>',
    
    bulb: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
    
    crosshair: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="1"/><path d="M12 8v-3m0 14v-3m-4-4h-3m14 0h-3"/></svg>',
    
    // Status Indicators
    signal: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 20h10M4 16h16M1 12h22M6 8h12M9 4h6"/></svg>',
    
    alertTriangle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3.05h16.94a2 2 0 0 0 1.71-3.05l-8.47-14.14a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    
    alertCircle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    
    checkCircle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    
    // System Metrics
    cpu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="5" x2="9" y2="4"/><line x1="15" y1="5" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="19"/><line x1="15" y1="20" x2="15" y2="19"/><line x1="20" y1="9" x2="19" y2="9"/><line x1="20" y1="15" x2="19" y2="15"/><line x1="4" y1="9" x2="5" y2="9"/><line x1="4" y1="15" x2="5" y2="15"/></svg>',
    
    memory: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M6 3v4M10 3v4M14 3v4M18 3v4"/></svg>',
    
    disk: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="1"/><path d="M12 1a11 11 0 0 1 11 11 11 11 0 0 1-11 11A11 11 0 0 1 1 12 11 11 0 0 1 12 1z" fill="none"/><path d="M12 5v6m0 4v2"/></svg>',
    
    network: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>',
    
    // Actions & Control
    play: '<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
    
    pause: '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>',
    
    stop: '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="5" y="5" width="14" height="14"/></svg>',
    
    refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36M20.49 15a9 9 0 0 1-14.85 3.36"/></svg>',
    
    settings: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 6v6M4.22 4.22l4.24 4.24m5.08 5.08l4.24 4.24M1 12h6m6 0h6M4.22 19.78l4.24-4.24m5.08-5.08l4.24-4.24M19.78 19.78l-4.24-4.24m-5.08-5.08l-4.24-4.24"/></svg>',
    
    // Pain points
    zap: '<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
    
    x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
    
    menu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>',
    
    // Extras for better UX
    activity: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
    
    trending: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.46 15.54 8 10.08 1 17"/><polyline points="23 6 23 12 17 12"/></svg>',
    
    downTrend: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 18 13.46 8.46 8 13.92 1 7"/><polyline points="23 18 23 12 17 12"/></svg>',
    
    info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    
    clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
};

/**
 * Create an SVG element from icon definition
 * @param {string} iconName - Key from SVG_ICONS
 * @param {Object} options - { size: '24px', class: 'icon-class', color: 'currentColor' }
 */
function createSVGIcon(iconName, options = {}) {
    const svg = SVG_ICONS[iconName];
    if (!svg) {
        console.warn(`Icon "${iconName}" not found`);
        return null;
    }
    
    const container = document.createElement('div');
    container.innerHTML = svg;
    const el = container.firstChild;
    
    const size = options.size || '20px';
    el.setAttribute('width', size);
    el.setAttribute('height', size);
    
    if (options.class) el.setAttribute('class', options.class);
    if (options.color) el.setAttribute('color', options.color);
    
    return el;
}

/**
 * Batch replace emoji with SVG icons in DOM
 * Maps emoji to icon names
 */
const EMOJI_TO_ICON = {
    '🏠': 'home',
    '🔄': 'processes',
    '🔍': 'search',
    '📈': 'chart',
    '💡': 'bulb',
    '⚡': 'zap',
    '💥': 'alertTriangle',
    '⚙️': 'settings',
    '🖥️': 'cpu',
    '💾': 'memory',
    '💿': 'disk',
    '🌐': 'network',
    '✨': 'zap',
    '🔴': 'alertTriangle',
    '🟠': 'alertTriangle',
    '🟡': 'alertTriangle',
    '⚠️': 'alertTriangle',
    '🔬': 'search',
    '📊': 'chart',
    '📋': 'activity',
    '❤️': 'activity',
    '✖': 'x',
};

/**
 * Replace all nav icons with SVG versions
 */
function replaceNavIconsWithSVG() {
    document.querySelectorAll('.nav-icon, .kpi-icon, .icon-emoji').forEach(el => {
        const emoji = el.textContent.trim();
        const iconName = EMOJI_TO_ICON[emoji];
        if (iconName) {
            el.innerHTML = '';
            const svgEl = createSVGIcon(iconName, { size: '20px' });
            if (svgEl) el.appendChild(svgEl);
        }
    });
}

/**
 * Smooth icon animation helpers
 */
function animateIcon(element, animationName = 'pulse', duration = 1000) {
    element.style.animation = `${animationName} ${duration}ms ease-in-out`;
    setTimeout(() => {
        element.style.animation = '';
    }, duration);
}

// Run on DOM content loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', replaceNavIconsWithSVG);
} else {
    replaceNavIconsWithSVG();
}
