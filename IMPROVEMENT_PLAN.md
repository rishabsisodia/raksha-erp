# Raksha ERP - UI/UX Modernization Plan

## Overview
Modernize the Raksha ERP interface based on patterns from Odoo, ERPNext, StockFlow, and Smart Inventory System repositories.

---

## Phase 1: UI/UX Modernization

### 1.1 Dashboard Redesign

#### Files to Modify:
- `frontend/index.html` (lines 72-116)
- `frontend/css/style.css` (append new styles)
- `frontend/js/app.js` (add new functions)

#### Changes:

**A. Add Quick Action Buttons (after dash-hero)**

```html
<!-- Insert after line 86 in index.html -->
<div class="quick-actions mb-6">
    <button onclick="showProformaOrderModal()" class="quick-action-btn">
        <i class="fas fa-plus-circle"></i>
        <span>Create PI</span>
    </button>
    <button onclick="showModal('m-product')" class="quick-action-btn">
        <i class="fas fa-box"></i>
        <span>Add Product</span>
    </button>
    <button onclick="showModal('m-sale')" class="quick-action-btn">
        <i class="fas fa-shopping-cart"></i>
        <span>New Sale</span>
    </button>
    <button onclick="go('reports', document.querySelector('[onclick*=reports]'))" class="quick-action-btn">
        <i class="fas fa-chart-line"></i>
        <span>Reports</span>
    </button>
</div>
```

**B. Add Activity Feed Panel (add to dashboard grid)**

```html
<!-- Add as 4th panel in dashboard grid -->
<div class="dash-panel activity-panel" style="grid-column: span 1;">
    <h3 class="dash-panel-title">
        <span class="panel-icon blue"><i class="fas fa-history"></i></span>
        Recent Activity
    </h3>
    <div id="dash-activity" class="activity-feed"></div>
</div>
```

---

### 1.2 CSS Additions (append to style.css)

```css
/* ============================================================
   QUICK ACTION BUTTONS
   ============================================================ */
.quick-actions {
    display: flex !important;
    gap: 12px !important;
    flex-wrap: wrap !important;
}

.quick-action-btn {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    padding: 12px 20px !important;
    background: white !important;
    border: 2px solid #e2e8f0 !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    color: #475569 !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    font-family: 'Inter', sans-serif !important;
}

.quick-action-btn:hover {
    border-color: #4f46e5 !important;
    color: #4f46e5 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15) !important;
}

.quick-action-btn i {
    font-size: 18px !important;
}

/* ============================================================
   ACTIVITY FEED
   ============================================================ */
.activity-feed {
    max-height: 300px !important;
    overflow-y: auto !important;
}

.activity-item {
    display: flex !important;
    gap: 12px !important;
    padding: 12px 0 !important;
    border-bottom: 1px solid #f1f5f9 !important;
}

.activity-item:last-child {
    border-bottom: none !important;
}

.activity-icon {
    width: 36px !important;
    height: 36px !important;
    border-radius: 10px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 14px !important;
    flex-shrink: 0 !important;
}

.activity-icon.order { background: #ede9fe !important; color: #7c3aed !important; }
.activity-icon.sale { background: #d1fae5 !important; color: #059669 !important; }
.activity-icon.product { background: #dbeafe !important; color: #2563eb !important; }
.activity-icon.customer { background: #fef3c7 !important; color: #d97706 !important; }

.activity-content {
    flex: 1 !important;
    min-width: 0 !important;
}

.activity-title {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #1e293b !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

.activity-time {
    font-size: 11px !important;
    color: #94a3b8 !important;
    margin-top: 2px !important;
}

/* ============================================================
   SKELETON LOADING
   ============================================================ */
@keyframes skeleton-loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}

.skeleton {
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%) !important;
    background-size: 200% 100% !important;
    animation: skeleton-loading 1.5s infinite !important;
    border-radius: 8px !important;
}

.skeleton-text {
    height: 14px !important;
    margin-bottom: 8px !important;
}

.skeleton-title {
    height: 20px !important;
    width: 60% !important;
    margin-bottom: 12px !important;
}

.table-skeleton td {
    padding: 12px !important;
}

.table-skeleton .skeleton-cell {
    height: 16px !important;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%) !important;
    background-size: 200% 100% !important;
    animation: skeleton-loading 1.5s infinite !important;
    border-radius: 4px !important;
}

/* ============================================================
   BUTTON SPINNER
   ============================================================ */
.btn-spinner {
    display: inline-block !important;
    width: 16px !important;
    height: 16px !important;
    border: 2px solid #ffffff !important;
    border-radius: 50% !important;
    border-top-color: transparent !important;
    animation: spin 0.8s linear infinite !important;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* ============================================================
   LOADING OVERLAY
   ============================================================ */
.loading-overlay {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    background: rgba(255, 255, 255, 0.8) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    z-index: 9999 !important;
}

.loading-spinner {
    width: 48px !important;
    height: 48px !important;
    border: 4px solid #e2e8f0 !important;
    border-top-color: #4f46e5 !important;
    border-radius: 50% !important;
    animation: spin 1s linear infinite !important;
}

/* ============================================================
   ENHANCED TOAST NOTIFICATIONS
   ============================================================ */
.toast-container {
    position: fixed !important;
    top: 20px !important;
    right: 20px !important;
    z-index: 10000 !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 8px !important;
}

.toast {
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
    padding: 14px 20px !important;
    background: white !important;
    border-radius: 12px !important;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15) !important;
    border-left: 4px solid !important;
    min-width: 300px !important;
    max-width: 450px !important;
    animation: toastSlideIn 0.3s ease !important;
    position: relative !important;
    overflow: hidden !important;
}

.toast.success { border-color: #10b981 !important; }
.toast.error { border-color: #ef4444 !important; }
.toast.warning { border-color: #f59e0b !important; }
.toast.info { border-color: #3b82f6 !important; }

.toast-icon {
    width: 24px !important;
    height: 24px !important;
    border-radius: 50% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 12px !important;
    flex-shrink: 0 !important;
}

.toast.success .toast-icon { background: #d1fae5 !important; color: #059669 !important; }
.toast.error .toast-icon { background: #fee2e2 !important; color: #dc2626 !important; }
.toast.warning .toast-icon { background: #fef3c7 !important; color: #d97706 !important; }
.toast.info .toast-icon { background: #dbeafe !important; color: #2563eb !important; }

.toast-content {
    flex: 1 !important;
}

.toast-title {
    font-weight: 600 !important;
    font-size: 14px !important;
    color: #1e293b !important;
}

.toast-message {
    font-size: 13px !important;
    color: #64748b !important;
    margin-top: 2px !important;
}

.toast-close {
    background: none !important;
    border: none !important;
    color: #94a3b8 !important;
    cursor: pointer !important;
    padding: 4px !important;
    font-size: 16px !important;
}

.toast-close:hover {
    color: #64748b !important;
}

.toast-progress {
    position: absolute !important;
    bottom: 0 !important;
    left: 0 !important;
    height: 3px !important;
    background: currentColor !important;
    animation: toastProgress 3s linear forwards !important;
}

@keyframes toastSlideIn {
    from {
        transform: translateX(100%) !important;
        opacity: 0 !important;
    }
    to {
        transform: translateX(0) !important;
        opacity: 1 !important;
    }
}

@keyframes toastSlideOut {
    from {
        transform: translateX(0) !important;
        opacity: 1 !important;
    }
    to {
        transform: translateX(100%) !important;
        opacity: 0 !important;
    }
}

@keyframes toastProgress {
    from { width: 100%; }
    to { width: 0%; }
}

.toast-actions {
    display: flex !important;
    gap: 8px !important;
    margin-top: 8px !important;
}

.toast-action {
    padding: 4px 12px !important;
    border-radius: 6px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    border: none !important;
    transition: all 0.2s !important;
}

.toast-action.primary {
    background: #4f46e5 !important;
    color: white !important;
}

.toast-action.primary:hover {
    background: #4338ca !important;
}

.toast-action.secondary {
    background: #f1f5f9 !important;
    color: #475569 !important;
}

.toast-action.secondary:hover {
    background: #e2e8f0 !important;
}

/* ============================================================
   ANIMATIONS
   ============================================================ */
.page-transition {
    animation: fadeIn 0.3s ease !important;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.content-card {
    transition: all 0.3s ease !important;
}

.content-card:hover {
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08) !important;
}

button:active {
    transform: scale(0.98) !important;
}

.modal-bg {
    animation: fadeIn 0.2s ease !important;
}

.modal-content {
    animation: modalSlideIn 0.3s ease !important;
}

@keyframes modalSlideIn {
    from {
        opacity: 0;
        transform: scale(0.95) translateY(-20px);
    }
    to {
        opacity: 1;
        transform: scale(1) translateY(0);
    }
}

table tbody tr {
    transition: background-color 0.15s ease !important;
}

table tbody tr:hover {
    background-color: #f8fafc !important;
}

.nav-btn {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

input, select, textarea {
    transition: all 0.2s ease !important;
}

input:focus, select:focus, textarea:focus {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.1) !important;
}

/* ============================================================
   STAT CARD TREND INDICATORS
   ============================================================ */
.stat-trend {
    font-size: 12px !important;
    font-weight: 600 !important;
    padding: 4px 8px !important;
    border-radius: 20px !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 4px !important;
}

.stat-trend.up {
    background: #ecfdf5 !important;
    color: #059669 !important;
}

.stat-trend.down {
    background: #fef2f2 !important;
    color: #dc2626 !important;
}

.stat-card:hover .stat-value {
    transform: scale(1.05) !important;
}

.stat-value {
    transition: all 0.3s ease !important;
}

/* ============================================================
   BADGE PULSE ANIMATION
   ============================================================ */
@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
}

.badge-pulse {
    animation: pulse 2s infinite !important;
}
```

---

### 1.3 JavaScript Additions (append to app.js)

```javascript
/* ============================================================
   LOADING FUNCTIONS
   ============================================================ */

// Show skeleton loading in table
function showTableSkeleton(tableId, rows) {
    rows = rows || 5;
    var tbody = document.getElementById(tableId);
    if (!tbody) return;
    var cols = tbody.closest('table').querySelectorAll('thead th').length;
    var html = '';
    for (var i = 0; i < rows; i++) {
        html += '<tr class="table-skeleton">';
        for (var j = 0; j < cols; j++) {
            html += '<td><div class="skeleton-cell" style="width: ' + (Math.random() * 40 + 60) + '%"></div></td>';
        }
        html += '</tr>';
    }
    tbody.innerHTML = html;
}

// Show loading overlay
function showLoading() {
    var overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = '<div class="loading-spinner"></div>';
    document.body.appendChild(overlay);
}

function hideLoading() {
    var overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.remove();
}

// Add spinner to button
function addBtnSpinner(btn) {
    btn.disabled = true;
    btn.dataset.originalHtml = btn.innerHTML;
    btn.innerHTML = '<span class="btn-spinner"></span> Loading...';
}

function removeBtnSpinner(btn) {
    btn.disabled = false;
    if (btn.dataset.originalHtml) {
        btn.innerHTML = btn.dataset.originalHtml;
    }
}

/* ============================================================
   ENHANCED TOAST NOTIFICATION
   ============================================================ */

var toastContainer = null;

function initToastContainer() {
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
}

function toast(message, isError, options) {
    isError = isError || false;
    options = options || {};
    initToastContainer();
    
    var type = isError ? 'error' : (options.type || 'success');
    var title = options.title || (isError ? 'Error' : 'Success');
    var duration = options.duration || 3000;
    var actions = options.actions || [];
    
    var icons = {
        success: 'fas fa-check',
        error: 'fas fa-times',
        warning: 'fas fa-exclamation',
        info: 'fas fa-info'
    };
    
    var toastEl = document.createElement('div');
    toastEl.className = 'toast ' + type;
    toastEl.innerHTML = '<div class="toast-icon"><i class="' + icons[type] + '"></i></div>' +
        '<div class="toast-content">' +
            '<div class="toast-title">' + title + '</div>' +
            '<div class="toast-message">' + message + '</div>' +
            (actions.length ? '<div class="toast-actions">' + 
                actions.map(function(a) { 
                    return '<button class="toast-action ' + (a.primary ? 'primary' : 'secondary') + '" ' +
                        'onclick="' + a.onclick + '">' + a.label + '</button>';
                }).join('') + '</div>' : '') +
        '</div>' +
        '<button class="toast-close" onclick="this.parentElement.remove()">&times;</button>' +
        '<div class="toast-progress" style="animation-duration: ' + duration + 'ms"></div>';
    
    toastContainer.appendChild(toastEl);
    
    // Auto remove
    setTimeout(function() {
        if (toastEl.parentElement) {
            toastEl.style.animation = 'toastSlideOut 0.3s ease forwards';
            setTimeout(function() { if (toastEl.parentElement) toastEl.remove(); }, 300);
        }
    }, duration);
    
    // Pause on hover
    toastEl.addEventListener('mouseenter', function() {
        var progress = toastEl.querySelector('.toast-progress');
        if (progress) progress.style.animationPlayState = 'paused';
    });
    
    toastEl.addEventListener('mouseleave', function() {
        var progress = toastEl.querySelector('.toast-progress');
        if (progress) progress.style.animationPlayState = 'running';
    });
}

/* ============================================================
   ACTIVITY FEED
   ============================================================ */

var _activityLog = [];

function logActivity(type, title, details) {
    _activityLog.unshift({
        type: type,
        title: title,
        details: details || '',
        time: new Date()
    });
    // Keep only last 20 activities
    if (_activityLog.length > 20) _activityLog.pop();
    renderActivityFeed();
}

function renderActivityFeed() {
    var container = document.getElementById('dash-activity');
    if (!container) return;
    
    if (_activityLog.length === 0) {
        container.innerHTML = '<div style="text-align:center;padding:20px;color:#94a3b8;font-size:13px;">No recent activity</div>';
        return;
    }
    
    var html = '';
    _activityLog.slice(0, 10).forEach(function(item) {
        var iconClass = 'product';
        var iconBg = 'background:#dbeafe;color:#2563eb;';
        if (item.type === 'order') { iconClass = 'order'; iconBg = 'background:#ede9fe;color:#7c3aed;'; }
        else if (item.type === 'sale') { iconClass = 'sale'; iconBg = 'background:#d1fae5;color:#059669;'; }
        else if (item.type === 'customer') { iconClass = 'customer'; iconBg = 'background:#fef3c7;color:#d97706;'; }
        
        var timeAgo = getTimeAgo(item.time);
        
        html += '<div class="activity-item">' +
            '<div class="activity-icon ' + iconClass + '" style="' + iconBg + '">' +
                '<i class="fas fa-' + (item.type === 'order' ? 'clipboard-list' : item.type === 'sale' ? 'shopping-cart' : item.type === 'customer' ? 'users' : 'box') + '"></i>' +
            '</div>' +
            '<div class="activity-content">' +
                '<div class="activity-title">' + escapeHtml(item.title) + '</div>' +
                '<div class="activity-time">' + timeAgo + '</div>' +
            '</div>' +
        '</div>';
    });
    
    container.innerHTML = html;
}

function getTimeAgo(date) {
    var seconds = Math.floor((new Date() - date) / 1000);
    if (seconds < 60) return 'Just now';
    var minutes = Math.floor(seconds / 60);
    if (minutes < 60) return minutes + 'm ago';
    var hours = Math.floor(minutes / 60);
    if (hours < 24) return hours + 'h ago';
    var days = Math.floor(hours / 24);
    return days + 'd ago';
}

/* ============================================================
   KEYBOARD SHORTCUTS
   ============================================================ */

document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K: Command palette (future)
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        // TODO: Open command palette
    }
    
    // Ctrl/Cmd + N: New order
    if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
        e.preventDefault();
        showProformaOrderModal();
    }
    
    // Escape: Close modal
    if (e.key === 'Escape') {
        var modals = document.querySelectorAll('.modal-bg:not(.hidden)');
        modals.forEach(function(modal) {
            modal.classList.add('hidden');
        });
    }
    
    // ?: Show shortcuts help
    if (e.key === '?' && !e.target.matches('input, textarea, select')) {
        e.preventDefault();
        showShortcutsHelp();
    }
});

function showShortcutsHelp() {
    var helpHtml = '<div style="padding:20px;">' +
        '<h3 style="font-weight:700;margin-bottom:16px;">Keyboard Shortcuts</h3>' +
        '<table style="width:100%;font-size:14px;">' +
        '<tr><td style="padding:8px;border-bottom:1px solid #f1f5f9;"><kbd style="background:#f1f5f9;padding:4px 8px;border-radius:4px;font-size:12px;">Ctrl + N</kbd></td><td style="padding:8px;border-bottom:1px solid #f1f5f9;">New PI/PO Order</td></tr>' +
        '<tr><td style="padding:8px;border-bottom:1px solid #f1f5f9;"><kbd style="background:#f1f5f9;padding:4px 8px;border-radius:4px;font-size:12px;">Ctrl + K</kbd></td><td style="padding:8px;border-bottom:1px solid #f1f5f9;">Command Palette (coming soon)</td></tr>' +
        '<tr><td style="padding:8px;border-bottom:1px solid #f1f5f9;"><kbd style="background:#f1f5f9;padding:4px 8px;border-radius:4px;font-size:12px;">Escape</kbd></td><td style="padding:8px;border-bottom:1px solid #f1f5f9;">Close Modal</td></tr>' +
        '<tr><td style="padding:8px;"><kbd style="background:#f1f5f9;padding:4px 8px;border-radius:4px;font-size:12px;">?</kbd></td><td style="padding:8px;">Show This Help</td></tr>' +
        '</table></div>';
    
    // Create modal for shortcuts
    var modal = document.createElement('div');
    modal.className = 'modal-bg';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:10001;';
    modal.innerHTML = '<div style="background:white;border-radius:16px;max-width:400px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,0.3);">' +
        '<div style="padding:20px;border-bottom:1px solid #f1f5f9;display:flex;justify-content:space-between;align-items:center;">' +
            '<h3 style="font-weight:700;font-size:18px;">Keyboard Shortcuts</h3>' +
            '<button onclick="this.closest(\'.modal-bg\').remove()" style="background:none;border:none;font-size:20px;cursor:pointer;color:#94a3b8;">&times;</button>' +
        '</div>' +
        helpHtml +
    '</div>';
    modal.addEventListener('click', function(e) { if (e.target === modal) modal.remove(); });
    document.body.appendChild(modal);
}
```

---

### 1.4 Dashboard Loading Integration

Update the `loadDashboard` function in app.js to use new features:

```javascript
// Add at the start of loadDashboard function
function loadDashboard() {
    // Show skeleton loading
    showTableSkeleton('dash-cards', 1);
    
    // Log activity
    logActivity('info', 'Dashboard loaded', 'User viewed dashboard');
    
    // ... existing code ...
}
```

---

### 1.5 Testing Checklist

- [ ] Quick action buttons appear on dashboard
- [ ] Quick action buttons navigate correctly
- [ ] Activity feed panel appears
- [ ] Activity items display with correct icons
- [ ] Skeleton screens show while data loads
- [ ] Toast notifications show with correct colors
- [ ] Toast auto-dismisses after timeout
- [ ] Toast pause on hover works
- [ ] Page transitions are smooth
- [ ] Modal animations work
- [ ] Button press effects work
- [ ] Keyboard shortcuts work (Ctrl+N, Escape, ?)
- [ ] Shortcuts help modal displays

---

## Summary of Changes

| File | Changes |
|------|---------|
| `frontend/index.html` | Add quick actions div, activity feed panel |
| `frontend/css/style.css` | Append ~400 lines of new styles |
| `frontend/js/app.js` | Append ~200 lines of new functions |

## Estimated Impact

- **User Experience**: Significantly improved with modern UI patterns
- **Performance**: Minimal impact (CSS animations are GPU-accelerated)
- **Code Size**: +600 lines total (400 CSS + 200 JS)
- **Browser Support**: Modern browsers (Chrome, Firefox, Edge, Safari)
