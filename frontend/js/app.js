var INR = '\u20B9';
var _products = [];
var _customers = [];
var _billingSites = [];
var _selectedBillingSite = null;
var _proformaItems = [];
var _saleItems = [];
var _editingProformaId = null;
var _sortState = {};
var _tableData = {};
var _currentUser = null;

function $(id) { return document.getElementById(id); }

function escapeHtml(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

async function downloadExport(url) {
    var token = localStorage.getItem('access_token');
    if (!token) { showLogin(); return; }
    try {
        var resp = await fetch(url, { headers: { 'Authorization': 'Bearer ' + token } });
        if (resp.status === 401) { localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token'); localStorage.removeItem('user'); showLogin(); return; }
        if (!resp.ok) { toast('Export failed'); return; }
        var blob = await resp.blob();
        var disposition = resp.headers.get('content-disposition') || '';
        var filename = 'export';
        var match = disposition.match(/filename=([^;]+)/);
        if (match) filename = match[1].replace(/"/g, '');
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(a.href);
    } catch(e) { toast('Export failed'); }
}

async function viewFileAuth(url) {
    var token = localStorage.getItem('access_token');
    if (!token) { showLogin(); return; }
    try {
        var resp = await fetch('/api/view-file?url=' + encodeURIComponent(url), { headers: { 'Authorization': 'Bearer ' + token } });
        if (resp.status === 401) { localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token'); localStorage.removeItem('user'); showLogin(); return; }
        if (!resp.ok) { toast('Failed to load file'); return; }
        var blob = await resp.blob();
        var ct = resp.headers.get('content-type') || 'application/octet-stream';
        var ext = url.split('.').pop().toLowerCase();
        var mimeMap = {pdf:'application/pdf',jpg:'image/jpeg',jpeg:'image/jpeg',png:'image/png',gif:'image/gif'};
        var mime = mimeMap[ext] || ct;
        var newBlob = new Blob([await blob.arrayBuffer()], {type: mime});
        var blobUrl = URL.createObjectURL(newBlob);
        if (mime.startsWith('image/') || mime === 'application/pdf') {
            window.open(blobUrl, '_blank');
        } else {
            var a = document.createElement('a');
            a.href = blobUrl;
            a.download = url.split('/').pop();
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    } catch(e) { toast('Failed to load file'); }
}

function showLogin() {
    var el = document.getElementById('login-overlay');
    if (el) { el.style.display = 'flex'; document.getElementById('login-username').focus(); }
}

function hideLogin() {
    var el = document.getElementById('login-overlay');
    if (el) el.style.display = 'none';
}

async function handleLogin(e) {
    e.preventDefault();
    var btn = document.getElementById('login-btn');
    var errEl = document.getElementById('login-error');
    btn.textContent = 'Signing in...';
    btn.disabled = true;
    errEl.style.display = 'none';
    try {
        var res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                username: document.getElementById('login-username').value,
                password: document.getElementById('login-password').value,
            })
        });
        var data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Invalid credentials');
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        _currentUser = data.user;
        hideLogin();
        applyRoleUI();
        go('dashboard');
        toast('Welcome, ' + (data.user.full_name || data.user.username) + '!');
    } catch(err) {
        errEl.textContent = err.message || 'Invalid credentials';
        errEl.style.display = 'block';
    }
    btn.textContent = 'Sign In';
    btn.disabled = false;
}

function handleLogout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    _currentUser = null;
    showLogin();
}

function getUser() {
    if (!_currentUser) {
        var stored = localStorage.getItem('user');
        if (stored) _currentUser = JSON.parse(stored);
    }
    return _currentUser;
}

function hasPermission(module, action) {
    var user = getUser();
    if (!user) return false;
    var perms = {
        admin: {dashboard:['view'],products:['view','create','edit','delete','import','export'],orders:['view','create','edit','delete','import','export'],proforma_orders:['view','create','edit','delete','export'],customers:['view','create','edit','delete','import'],transporters:['view','create','edit','delete','import'],sales:['view','create','edit','delete','import','export','bulk_edit'],expenses:['view','create','edit','delete','import'],reports:['view','export'],settings:['view','edit'],users:['view','create','edit','delete']},
        manager: {dashboard:['view'],products:['view','create','edit'],orders:['view','create','edit'],proforma_orders:['view','create','edit'],customers:['view','create','edit'],transporters:['view','create','edit'],sales:['view','create','edit'],expenses:['view','create','edit'],reports:['view'],settings:['view'],users:[]},
        viewer: {dashboard:['view'],products:['view'],orders:['view'],proforma_orders:['view'],customers:['view'],transporters:['view'],sales:['view'],expenses:['view'],reports:['view'],settings:['view'],users:[]}
    };
    return ((perms[user.role] || {})[module] || []).indexOf(action) !== -1;
}

function applyRoleUI() {
    var user = getUser();
    if (!user) return;
    var ud = document.getElementById('user-display');
    var rb = document.getElementById('role-badge');
    if (ud) ud.textContent = user.full_name || user.username;
    if (rb) {
        rb.textContent = user.role.toUpperCase();
        var colors = {admin:'background:#fef2f2;color:#dc2626;', manager:'background:#eff6ff;color:#2563eb;', viewer:'background:#f0fdf4;color:#16a34a;'};
        rb.style.cssText = 'font-size:11px;padding:2px 8px;border-radius:6px;font-weight:600;' + (colors[user.role] || '');
    }
    var navItems = document.querySelectorAll('.nav-btn');
    var navMap = ['dashboard','products','orders','customers','transporters','sales','expenses','reports','settings'];
    navItems.forEach(function(item, i) {
        var module = navMap[i];
        if (module && !hasPermission(module, 'view')) {
            item.style.display = 'none';
        } else {
            item.style.display = '';
        }
    });
}

document.addEventListener('input', function(e) {
    if (e.target.type === 'number' && e.target.min === '0' && parseFloat(e.target.value) < 0) {
        e.target.value = 0;
    }
});

function go(page, el) {
    document.querySelectorAll('[id^="p-"]').forEach(function(p) { p.classList.add('hidden'); });
    document.querySelectorAll('.nav-btn').forEach(function(b) { b.classList.remove('bg-indigo-700'); });
    $('p-' + page).classList.remove('hidden');
    if (el) el.classList.add('bg-indigo-700');
    var t = {dashboard:'Dashboard',products:'Products',orders:'Orders',customers:'Customers',transporters:'Transporters','purchase-rates':'Purchase Rates',sales:'Sales',expenses:'Expenses',reports:'Reports',settings:'Settings'};
    $('pg-title').textContent = t[page] || page;
    if (page === 'dashboard') loadDashboard();
    if (page === 'products') loadProducts();
    if (page === 'orders') loadAllOrders();
    if (page === 'customers') loadCustomers();
    if (page === 'transporters') loadTransporters();
    if (page === 'purchase-rates') loadPurchaseRates();
    if (page === 'sales') loadSales();
    if (page === 'expenses') loadExpenses();
    if (page === 'reports') loadReport();
    if (page === 'settings') loadSettings();
}

async function api(url, opts) {
    opts = opts || {};
    var h = {'Content-Type': 'application/json'};
    var token = localStorage.getItem('access_token');
    if (token) h['Authorization'] = 'Bearer ' + token;
    if (opts.headers) Object.assign(h, opts.headers);
    var r = await fetch(url, {method: opts.method || 'GET', headers: h, body: opts.body ? opts.body : undefined});
    if (r.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        _currentUser = null;
        showLogin();
        throw new Error('Session expired');
    }
    if (!r.ok) { var e = await r.text(); throw new Error(e); }
    return r.json();
}

function toast(msg, err) {
    $('toast').textContent = msg;
    $('toast').className = 'fixed bottom-4 right-4 text-white px-6 py-3 rounded-lg shadow-lg ' + (err ? 'bg-red-600' : 'bg-green-600');
    $('toast').classList.remove('hidden');
    setTimeout(function() { $('toast').classList.add('hidden'); }, 3000);
}

function showLoading(tableId, colspan) {
    var tbody = document.getElementById(tableId);
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="' + colspan + '" class="text-center py-8"><div style="display:inline-flex;align-items:center;gap:8px;color:#64748b;"><div class="spinner" style="width:20px;height:20px;border:2px solid #e2e8f0;border-top-color:#6366f1;border-radius:50%;animation:spin 0.8s linear infinite;"></div>Loading...</div></td></tr>';
    }
}

var style = document.createElement('style');
style.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
document.head.appendChild(style);

async function showModal(id) {
    $(id).classList.remove('hidden');
    if (id === 'm-sale' && !$('f-slid').value) {
        await refreshDropdowns();
        _saleItems = [];
        addSaleItem();
    }
    if (id === 'm-purchase-rate') {
        await refreshProductDropdown();
    }
}

async function refreshDropdowns() {
    _products = await api('/api/products');
    _customers = await api('/api/customers');
    _billingSites = await api('/api/billing-sites');
    var po = '';
    _products.forEach(function(p) { po += '<option value="' + p.id + '">' + escapeHtml(p.part_no) + ' - ' + escapeHtml(p.name) + ' (' + escapeHtml(p.size || 'N/A') + ')</option>'; });
    var co = '<option value="">-- Select Customer --</option>';
    _customers.forEach(function(c) { co += '<option value="' + c.id + '">' + escapeHtml(c.customer_id) + ' - ' + escapeHtml(c.contact_name) + '</option>'; });
    var bs = '<option value="">Select Billing Site</option>';
    _billingSites.forEach(function(s) { bs += '<option value="' + s.id + '">' + escapeHtml(s.name) + '</option>'; });
    if ($('f-slprod')) $('f-slprod').innerHTML = po;
    if ($('f-slcust')) $('f-slcust').innerHTML = co;
    if ($('f-poocust')) $('f-poocust').innerHTML = co;
    if ($('f-poobilling')) $('f-poobilling').innerHTML = bs;
}

function onBillingSiteChange() {
    var id = parseInt($('f-poobilling').value);
    _selectedBillingSite = _billingSites.find(function(s) { return s.id === id; }) || null;
}
function hideModal(id) { $(id).classList.add('hidden'); }

function fmt(n) { return INR + Number(n || 0).toLocaleString('en-IN', {minimumFractionDigits: 0, maximumFractionDigits: 0}); }

function sortTable(tableId, colIdx, type) {
    var state = _sortState[tableId];
    if (state && state.col === colIdx) {
        state.asc = !state.asc;
    } else {
        _sortState[tableId] = { col: colIdx, asc: true };
        state = _sortState[tableId];
    }
    var data = _tableData[tableId];
    if (!data) return;
    data.sort(function(a, b) {
        var va = a.vals[colIdx], vb = b.vals[colIdx];
        if (type === 'num') {
            va = parseFloat(va) || 0; vb = parseFloat(vb) || 0;
            return state.asc ? va - vb : vb - va;
        } else {
            va = (va || '').toString().toLowerCase();
            vb = (vb || '').toString().toLowerCase();
            if (va < vb) return state.asc ? -1 : 1;
            if (va > vb) return state.asc ? 1 : -1;
            return 0;
        }
    });
    var tbody = document.getElementById(tableId);
    if (tbody) {
        var html = '';
        data.forEach(function(row) { html += row.html; });
        tbody.innerHTML = html;
    }
    var table = tbody ? tbody.closest('table') : null;
    if (table) {
        var ths = table.querySelectorAll('thead th');
        ths.forEach(function(th, i) {
            var arrow = th.querySelector('.sort-arrow');
            if (!arrow) return;
            th.classList.remove('sort-active');
            if (i === colIdx) {
                th.classList.add('sort-active');
                arrow.textContent = state.asc ? ' \u25B2' : ' \u25BC';
            } else {
                arrow.textContent = '';
            }
        });
    }
}

function filterTable(tableId, query, searchCols) {
    var data = _tableData[tableId];
    if (!data) return;
    var q = (query || '').toLowerCase().trim();
    var tbody = document.getElementById(tableId);
    if (!tbody) return;
    if (!q) {
        var html = '';
        data.forEach(function(row) { html += row.html; });
        tbody.innerHTML = html;
        return;
    }
    var filtered = data.filter(function(row) {
        return searchCols.some(function(ci) {
            var val = (row.vals[ci] || '').toString().toLowerCase();
            return val.indexOf(q) !== -1;
        });
    });
    var html = '';
    filtered.forEach(function(row) { html += row.html; });
    tbody.innerHTML = html || '<tr><td colspan="20" class="text-center py-4 text-gray-400">No results found</td></tr>';
}

async function loadProducts() {
    showLoading('t-products', 8);
    _products = await api('/api/products');
    var sortRows = [];
    _products.forEach(function(p) {
        var h = '<tr class="border-b data-row" onclick="editProduct(' + p.id + ')">';
        h += '<td class="px-3 py-2">' + p.id + '</td>';
        h += '<td class="px-3 py-2">' + escapeHtml(p.part_no || '-') + '</td>';
        h += '<td class="px-3 py-2 font-medium">' + escapeHtml(p.name) + '</td>';
        h += '<td class="px-3 py-2">' + escapeHtml(p.category || '-') + '</td>';
        h += '<td class="px-3 py-2">' + escapeHtml(p.size || '-') + '</td>';
        h += '<td class="px-3 py-2">' + escapeHtml(p.load_rating || '-') + '</td>';
        h += '<td class="px-3 py-2">' + fmt(p.mrp) + '</td>';
        h += '<td class="px-3 py-2" onclick="event.stopPropagation()">';
        h += '<button onclick="editProduct(' + p.id + ')" class="action-btn action-btn-edit" title="Edit"><i class="fas fa-pen"></i> Edit</button>';
        h += '<button onclick="openPricing(' + p.id + ')" class="action-btn action-btn-pricing ml-1" title="Pricing"><i class="fas fa-tag"></i> Price</button>';
        h += '<button onclick="deleteProduct(' + p.id + ')" class="action-btn action-btn-delete ml-1" title="Delete"><i class="fas fa-trash"></i></button>';
        h += '</td></tr>';
        sortRows.push({vals: [p.id, p.part_no||'', p.name, p.category||'', p.size||'', p.load_rating||'', p.mrp||0], html: h});
    });
    _tableData['t-products'] = sortRows;
    _sortState['t-products'] = null;
    $('t-products').innerHTML = sortRows.map(function(r){return r.html;}).join('') || '<tr><td colspan="8" class="text-center py-4 text-gray-400">No products</td></tr>';
}

function editProduct(id) {
    var p = _products.find(function(x) { return x.id === id; });
    if (!p) return;
    $('f-pid').value = p.id;
    $('f-ppartno').value = p.part_no || '';
    $('f-pname').value = p.name;
    $('f-pcat').value = p.category || '';
    $('f-psize').value = p.size || '';
    $('f-pload').value = p.load_rating || '';
    $('f-phsn').value = p.hsn_code || '';
    $('m-product-title').textContent = 'Edit Product';
    showModal('m-product');
}

async function deleteProduct(id) {
    if (!confirm('Delete this product?')) return;
    await api('/api/products/' + id, {method: 'DELETE'});
    toast('Product deleted');
    loadProducts();
}

async function dedupProducts() {
    if (!confirm('Remove duplicate products? Products with the same Part No or Name will be merged.')) return;
    try {
        var r = await api('/api/products/dedup', {method: 'POST'});
        toast(r.message);
        loadProducts();
    } catch(e) { toast('Dedup failed: ' + e.message, true); }
}

async function openPricing(id) {
    $('f-prpid').value = id;
    try {
        var pr = await api('/api/products/' + id + '/pricing');
        $('f-praw').value = pr.raw_material_cost || 0;
        $('f-pmrp').value = pr.mrp || 0;
        $('f-pgst').value = pr.gst_rate || 18;
    } catch(e) {}
    showModal('m-pricing');
}

async function loadOrders() {
    await loadAllOrders();
}

async function loadAllOrders() {
    showLoading('t-all-orders', 10);
    var filter = $('f-orderfilter') ? $('f-orderfilter').value : '';
    var rows = [];

    if (filter !== 'PIPO') {
        try {
            var cogs = await api('/api/orders');
            cogs.forEach(function(o) {
                rows.push({
                    type: 'COGS',
                    ref: o.po_no || ('Order #' + o.sl_no),
                    date: o.po_date || o.entry_date || '',
                    customer_name: o.customer_name || '-',
                    billing_site: o.billing_site || o.shipping_site || '-',
                    boxes: o.no_of_boxes || 0,
                    value: o.value_excl_gst_freight || 0,
                    invoice_no: o.invoice_no || '-',
                    invoice_amt: o.invoice_amount || 0,
                    payment_status: '-',
                    order_status: '-',
                    id: o.id,
                    raw: o
                });
            });
        } catch(e) {}
    }

    if (filter !== 'COGS') {
        try {
            var pipos = await api('/api/proforma-orders');
            pipos.forEach(function(o) {
                rows.push({
                    type: o.order_type || 'PI',
                    ref: o.pi_no,
                    date: o.pi_date ? o.pi_date.substring(0, 10) : '',
                    customer_name: o.customer_name || '-',
                    billing_site: o.billing_site || o.shipping_site || '-',
                    boxes: o.no_of_boxes || 0,
                    value: o.value_excl_gst || 0,
                    invoice_no: '-',
                    invoice_amt: o.total_amount || 0,
                    payment_status: o.payment_status || 'Pending',
                    order_status: o.status || 'draft',
                    id: o.id,
                    raw: o
                });
            });
        } catch(e) {}
    }

    rows.sort(function(a, b) {
        var da = a.date || '';
        var db2 = b.date || '';
        return da > db2 ? -1 : da < db2 ? 1 : 0;
    });

    var sortRows = [];
    var h = '';
    rows.forEach(function(r) {
        var typeBadge = r.type === 'COGS'
            ? '<span class="px-2 py-1 rounded text-xs bg-gray-100 text-gray-700">COGS</span>'
            : '<span class="px-2 py-1 rounded text-xs bg-blue-100 text-blue-700">' + escapeHtml(r.type) + '</span>';
        var paymentBadge = '';
        if (r.payment_status && r.payment_status !== '-') {
            var sc = r.payment_status === 'Paid' ? 'bg-green-100 text-green-700' : r.payment_status === 'Partial' ? 'bg-yellow-100 text-yellow-700' : 'bg-orange-100 text-orange-700';
            paymentBadge = '<span class="px-2 py-1 rounded text-xs ' + sc + '">' + escapeHtml(r.payment_status) + '</span>';
        }
        var orderStatusBadge = '';
        if (r.order_status && r.order_status !== '-') {
            var statusLabels = {
                'draft': 'Draft', 'confirmed': 'Confirmed', 'po_created': 'PO Created',
                'transport_pending': 'Transport Pending', 'transport_finalized': 'Transport Finalized',
                'billing': 'Billing', 'completed': 'Completed'
            };
            var osc = r.order_status === 'draft' ? 'bg-gray-100 text-gray-600'
                : r.order_status === 'confirmed' ? 'bg-blue-100 text-blue-700'
                : r.order_status === 'po_created' ? 'bg-indigo-100 text-indigo-700'
                : r.order_status === 'transport_pending' ? 'bg-yellow-100 text-yellow-700'
                : r.order_status === 'transport_finalized' ? 'bg-orange-100 text-orange-700'
                : r.order_status === 'billing' ? 'bg-purple-100 text-purple-700'
                : r.order_status === 'completed' ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-600';
            orderStatusBadge = '<span class="px-2 py-1 rounded text-xs ' + osc + '">' + escapeHtml(statusLabels[r.order_status] || r.order_status) + '</span>';
        }
        var statusOptions = ['draft','confirmed','po_created','transport_pending','transport_finalized','billing','completed'];
        var statusLabels = {
            'draft': 'Draft', 'confirmed': 'Confirmed', 'po_created': 'PO Created',
            'transport_pending': 'Transport Pending', 'transport_finalized': 'Transport Finalized',
            'billing': 'Billing', 'completed': 'Completed'
        };
        var statusSelect = '';
        if (r.type !== 'COGS') {
            statusSelect = '<select onchange="changeOrderStatus(' + r.id + ', this.value)" style="border:1px solid #e2e8f0;border-radius:6px;padding:2px 4px;font-size:11px;font-family:Inter,sans-serif;cursor:pointer;">';
            statusOptions.forEach(function(s) {
                var sel = r.order_status === s ? ' selected' : '';
                statusSelect += '<option value="' + s + '"' + sel + '>' + statusLabels[s] + '</option>';
            });
            statusSelect += '</select>';
        }
        var editFn = r.type === 'COGS' ? 'editOrder(' + r.id + ')' : 'editProformaOrder(' + r.id + ')';
        var deleteFn = r.type === 'COGS' ? 'deleteOrder(' + r.id + ')' : 'deleteProformaOrder(' + r.id + ')';
        var viewFn = r.type === 'COGS' ? '' : '<button onclick="viewProformaOrder(' + r.id + ')" class="action-btn action-btn-view" title="View"><i class="fas fa-eye"></i> View</button>';
        var whatsappFn = r.type === 'COGS' ? '' : '<button onclick="openWhatsApp(' + r.id + ')" class="action-btn" style="background:#25d366;color:white;margin-left:4px;" title="Send WhatsApp"><i class="fab fa-whatsapp"></i></button>';

        var rowH = '<tr class="border-b data-row" onclick="' + editFn + '">';
        rowH += '<td class="px-2 py-2">' + typeBadge + '</td>';
        rowH += '<td class="px-2 py-2 font-medium">' + escapeHtml(r.ref || '-') + '</td>';
        rowH += '<td class="px-2 py-2">' + escapeHtml(r.date || '-') + '</td>';
        rowH += '<td class="px-2 py-2">' + escapeHtml(r.customer_name) + '</td>';
        rowH += '<td class="px-2 py-2">' + escapeHtml(r.billing_site) + '</td>';
        rowH += '<td class="px-2 py-2">' + r.boxes + '</td>';
        rowH += '<td class="px-2 py-2">' + fmt(r.value) + '</td>';
        rowH += '<td class="px-2 py-2">' + escapeHtml(r.invoice_no) + '</td>';
        rowH += '<td class="px-2 py-2 font-bold">' + fmt(r.invoice_amt) + '</td>';
        rowH += '<td class="px-2 py-2">' + paymentBadge + '</td>';
        rowH += '<td class="px-2 py-2" onclick="event.stopPropagation()">' + statusSelect + '</td>';
        rowH += '<td class="px-2 py-2" onclick="event.stopPropagation()">';
        rowH += '<button onclick="' + editFn + '" class="action-btn action-btn-edit" title="Edit"><i class="fas fa-pen"></i> Edit</button>';
        rowH += viewFn;
        rowH += whatsappFn;
        rowH += '<button onclick="' + deleteFn + '" class="action-btn action-btn-delete ml-1" title="Delete"><i class="fas fa-trash"></i></button>';
        rowH += '</td></tr>';
        sortRows.push({vals: [r.type, r.ref, r.date, r.customer_name, r.billing_site, r.boxes, r.value, r.invoice_no, r.invoice_amt, r.payment_status, r.order_status], html: rowH});
    });
    _tableData['t-all-orders'] = sortRows;
    _sortState['t-all-orders'] = null;
    $('t-all-orders').innerHTML = sortRows.map(function(r){return r.html;}).join('') || '<tr><td colspan="12" class="text-center py-4 text-gray-400">No orders</td></tr>';
}

function changeOrderStatus(orderId, newStatus) {
    api('/api/proforma-orders/' + orderId + '/status', {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({status: newStatus})
    }).then(function() {
        loadAllOrders();
    }).catch(function(e) {
        alert('Failed to update status: ' + e.message);
    });
}

function editOrder(id) {
    var orders = [];
    api('/api/orders').then(function(data) {
        orders = data;
        var o = orders.find(function(x) { return x.id === id; });
        if (!o) return;
        $('f-oid').value = o.id;
        $('f-oslno').value = o.sl_no || '';
        $('f-opo').value = o.po_no || '';
        $('f-opodate').value = o.po_date || '';
        $('f-ocustname').value = o.customer_name || '';
        $('f-obilling').value = o.billing_site || '';
        $('f-oshipping').value = o.shipping_site || '';
        $('f-oboxes').value = o.no_of_boxes || '';
        $('f-ovalue').value = o.value_excl_gst_freight || '';
        $('f-oinvno').value = o.invoice_no || '';
        $('f-oinvdate').value = o.invoice_date || '';
        $('f-oinvamt').value = o.invoice_amount_excl_gst || '';
        $('f-oweight').value = o.weight_kgs || '';
        $('f-ofrate').value = o.freight_rate_per_kg || '';
        $('f-otcharges').value = o.transport_charges || '';
        $('f-oiamt').value = o.invoice_amount || '';
        $('f-oeway').value = o.eway_bill_no || '';
        $('f-olr').value = o.lr_no || '';
        $('f-oentrydate').value = o.entry_date || '';
        $('f-ocnamt').value = o.credit_note_amount || '';
        $('f-ocnno').value = o.credit_note_no || '';
        $('f-otransporter').value = o.transporter || '';
        $('f-otransno').value = o.transporter_no || '';
        $('m-order-title').textContent = 'Edit Order';
        showModal('m-order');
    });
}

async function deleteOrder(id) {
    if (!confirm('Delete this order?')) return;
    await api('/api/orders/' + id, {method: 'DELETE'});
    toast('Order deleted');
    loadOrders();
}

async function loadCustomers() {
    showLoading('t-customers', 10);
    _customers = await api('/api/customers');
    var sortRows = [];
    _customers.forEach(function(c) {
        var h = '<tr class="border-b data-row" onclick="editCustomer(' + c.id + ')">';
        h += '<td class="px-2 py-2 font-medium">' + escapeHtml(c.customer_id || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(c.contact_name || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(c.gstin || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(c.state || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(c.district || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(c.city || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(c.contact_number || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(c.exec_name || '-') + '</td>';
        h += '<td class="px-2 py-2"><span class="px-2 py-1 rounded text-xs ' + (c.blacklisted ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700') + '">' + (c.blacklisted ? 'Blacklisted' : 'Active') + '</span></td>';
        h += '<td class="px-2 py-2" onclick="event.stopPropagation()">';
        h += '<button onclick="editCustomer(' + c.id + ')" class="action-btn action-btn-edit" title="Edit"><i class="fas fa-pen"></i> Edit</button>';
        h += '<button onclick="deleteCustomer(' + c.id + ')" class="action-btn action-btn-delete ml-1" title="Delete"><i class="fas fa-trash"></i></button>';
        h += '</td></tr>';
        sortRows.push({vals: [c.customer_id||'', c.contact_name||'', c.gstin||'', c.state||'', c.district||'', c.city||'', c.contact_number||'', c.exec_name||'', c.blacklisted?'Blacklisted':'Active'], html: h});
    });
    _tableData['t-customers'] = sortRows;
    _sortState['t-customers'] = null;
    $('t-customers').innerHTML = sortRows.map(function(r){return r.html;}).join('') || '<tr><td colspan="10" class="text-center py-4 text-gray-400">No customers</td></tr>';
}

var _transporters = [];
async function loadTransporters() {
    showLoading('t-transporters', 9);
    _transporters = await api('/api/transporters');
    var sortRows = [];
    _transporters.forEach(function(t) {
        var h = '<tr class="border-b data-row" onclick="editTransporter(' + t.id + ')">';
        h += '<td class="px-2 py-2 font-medium">' + escapeHtml(t.transporter_id || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(t.name || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(t.phone || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(t.state || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(t.gst_number || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(t.pan_number || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(t.contact_person || '-') + '</td>';
        h += '<td class="px-2 py-2"><span class="px-2 py-1 rounded text-xs ' + (t.blacklisted ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700') + '">' + (t.blacklisted ? 'Blacklisted' : 'Active') + '</span></td>';
        h += '<td class="px-2 py-2" onclick="event.stopPropagation()">';
        h += '<button onclick="editTransporter(' + t.id + ')" class="action-btn action-btn-edit" title="Edit"><i class="fas fa-pen"></i> Edit</button>';
        h += '<button onclick="deleteTransporter(' + t.id + ')" class="action-btn action-btn-delete ml-1" title="Delete"><i class="fas fa-trash"></i></button>';
        h += '</td></tr>';
        sortRows.push({vals: [t.transporter_id||'', t.name||'', t.phone||'', t.state||'', t.gst_number||'', t.pan_number||'', t.contact_person||'', t.blacklisted?'Blacklisted':'Active'], html: h});
    });
    _tableData['t-transporters'] = sortRows;
    _sortState['t-transporters'] = null;
    $('t-transporters').innerHTML = sortRows.map(function(r){return r.html;}).join('') || '<tr><td colspan="9" class="text-center py-4 text-gray-400">No transporters</td></tr>';
}

function editTransporter(id) {
    var t = _transporters.find(function(x) { return x.id === id; });
    if (!t) return;
    $('f-tid').value = t.id;
    $('f-ttransid').value = t.transporter_id || '';
    $('f-tname').value = t.name || '';
    $('f-tphone').value = t.phone || '';
    $('f-temail').value = t.email || '';
    $('f-taddr').value = t.address || '';
    $('f-tstate').value = t.state || '';
    $('f-tdistrict').value = t.district || '';
    $('f-tcity').value = t.city || '';
    $('f-tpincode').value = t.pincode || '';
    $('f-tgst').value = t.gst_number || '';
    $('f-tpan').value = t.pan_number || '';
    $('f-tcontactperson').value = t.contact_person || '';
    $('f-tcontactnum').value = t.contact_number || '';
    $('f-ttrackurl').value = t.tracking_url_pattern || '';
    $('f-tblacklisted').checked = t.blacklisted === 1;
    $('f-tgstfile-name').innerHTML = t.gst_certificate ? '<a onclick="viewFileAuth(\'' + escapeHtml(t.gst_certificate) + '\')" class="text-blue-600 underline" style="cursor:pointer;">View uploaded file</a>' : '';
    $('f-tpanfile-name').innerHTML = t.pan_card ? '<a onclick="viewFileAuth(\'' + escapeHtml(t.pan_card) + '\')" class="text-blue-600 underline" style="cursor:pointer;">View uploaded file</a>' : '';
    $('m-trans-title').textContent = 'Edit Transporter';
    showModal('m-transporter');
}

async function deleteTransporter(id) {
    if (!confirm('Delete this transporter?')) return;
    await api('/api/transporters/' + id, {method: 'DELETE'});
    toast('Transporter deleted');
    loadTransporters();
}

var _purchaseRates = [];
async function loadPurchaseRates() {
    showLoading('t-purchase-rates', 9);
    _purchaseRates = await api('/api/purchase-rates');
    var sortRows = [];
    _purchaseRates.forEach(function(r) {
        var h = '<tr class="border-b data-row" onclick="editPurchaseRate(' + r.id + ')">';
        h += '<td class="px-2 py-2">' + r.id + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(r.part_no || '-') + '</td>';
        h += '<td class="px-2 py-2 font-medium">' + escapeHtml(r.product_name || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(r.category || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(r.size || '-') + '</td>';
        h += '<td class="px-2 py-2 font-bold">' + fmt(r.rate) + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(r.supplier || '-') + '</td>';
        h += '<td class="px-2 py-2">' + escapeHtml(r.effective_date || '-') + '</td>';
        h += '<td class="px-2 py-2" onclick="event.stopPropagation()">';
        h += '<button onclick="editPurchaseRate(' + r.id + ')" class="action-btn action-btn-edit" title="Edit"><i class="fas fa-pen"></i> Edit</button>';
        h += '<button onclick="deletePurchaseRate(' + r.id + ')" class="action-btn action-btn-delete ml-1" title="Delete"><i class="fas fa-trash"></i></button>';
        h += '</td></tr>';
        sortRows.push({vals: [r.id, r.part_no||'', r.product_name||'', r.category||'', r.size||'', r.rate||0, r.supplier||'', r.effective_date||''], html: h});
    });
    _tableData['t-purchase-rates'] = sortRows;
    _sortState['t-purchase-rates'] = null;
    $('t-purchase-rates').innerHTML = sortRows.map(function(r){return r.html;}).join('') || '<tr><td colspan="9" class="text-center py-4 text-gray-400">No purchase rates</td></tr>';
}

async function editPurchaseRate(id) {
    var r = _purchaseRates.find(function(x) { return x.id === id; });
    if (!r) return;
    $('f-prid').value = r.id;
    $('f-prrate').value = r.rate || '';
    $('f-predate').value = r.effective_date || '';
    $('f-prsupplier').value = r.supplier || '';
    $('m-pr-title').textContent = 'Edit Purchase Rate';
    await refreshProductDropdown();
    $('f-prproduct').value = r.product_id;
    showModal('m-purchase-rate');
}

async function deletePurchaseRate(id) {
    if (!confirm('Delete this purchase rate?')) return;
    await api('/api/purchase-rates/' + id, {method: 'DELETE'});
    toast('Purchase rate deleted');
    loadPurchaseRates();
}

async function refreshProductDropdown() {
    if (!_products.length) _products = await api('/api/products');
    var po = '<option value="">Select Product</option>';
    _products.forEach(function(p) { po += '<option value="' + p.id + '">' + escapeHtml(p.part_no) + ' - ' + escapeHtml(p.name) + ' (' + escapeHtml(p.size || 'N/A') + ')</option>'; });
    if ($('f-prproduct')) $('f-prproduct').innerHTML = po;
}

async function importPurchaseRatesCSV(input) {
    var file = input.files[0];
    if (!file) return;
    var text = await file.text();
    var lines = text.split('\n').filter(function(l) { return l.trim(); });
    if (lines.length < 2) { toast('CSV is empty', true); return; }
    var header = lines[0].toLowerCase();
    var rates = [];
    for (var i = 1; i < lines.length; i++) {
        var cols = lines[i].split(',').map(function(c) { return c.trim().replace(/^"|"$/g, ''); });
        if (cols.length < 2) continue;
        var product = _products.find(function(p) { return p.part_no === cols[0] || p.name === cols[0]; });
        if (!product) continue;
        rates.push({
            product_id: product.id,
            rate: parseFloat(cols[1]) || 0,
            supplier: cols[2] || '',
            effective_date: cols[3] || new Date().toISOString().split('T')[0]
        });
    }
    if (rates.length === 0) { toast('No matching products found', true); return; }
    try {
        var r = await api('/api/purchase-rates/bulk', {method: 'POST', body: JSON.stringify({rates: rates})});
        toast(r.message);
        loadPurchaseRates();
    } catch(e) { toast('Import failed: ' + e.message, true); }
    input.value = '';
}

function editCustomer(id) {
    var c = _customers.find(function(x) { return x.id === id; });
    if (!c) return;
    $('f-cid').value = c.id;
    $('f-ccustid').value = c.customer_id || '';
    $('f-cgstin').value = c.gstin || '';
    $('f-cbilladdr').value = c.billing_address || '';
    $('f-cshipaddr').value = c.shipping_address || '';
    $('f-cstate').value = c.state || '';
    $('f-cdistrict').value = c.district || '';
    $('f-ccity').value = c.city || '';
    $('f-cpincode').value = c.pincode || '';
    $('f-ccontactname').value = c.contact_name || '';
    $('f-ccontactnum').value = c.contact_number || '';
    $('f-ccontactemail').value = c.contact_email || '';
    $('f-cexeccode').value = c.exec_code || '';
    $('f-cexecname').value = c.exec_name || '';
    $('f-cexecnum').value = c.exec_number || '';
    $('f-cexecemail').value = c.exec_email || '';
    $('f-cblacklisted').checked = c.blacklisted === 1;
    $('m-cust-title').textContent = 'Edit Customer';
    showModal('m-customer');
}

async function deleteCustomer(id) {
    if (!confirm('Delete this customer?')) return;
    await api('/api/customers/' + id, {method: 'DELETE'});
    toast('Customer deleted');
    loadCustomers();
}

try { $('f-csameaddr').addEventListener('change', function() {
    if (this.checked) {
        $('f-cshipaddr').value = $('f-cbilladdr').value;
    }
}); } catch(e) {}

async function loadSales() {
    try {
    showLoading('t-sales', 11);
    api('/api/auto-generate-tracking-urls', {method: 'POST'}).catch(function(){});
    var sales = await api('/api/sales');
    var rows = [];
    sales.forEach(function(s) {
        var tn = s.transporter_name || '-';
        var tnDisplay = tn !== '-' ? '<span class="text-indigo-600 hover:text-indigo-800 underline cursor-pointer" onclick="event.stopPropagation(); addTransporterFromSales(\'' + tn.replace(/'/g, "\\'") + '\')">' + escapeHtml(tn) + '</span>' : tn;
        var h = '<tr class="border-b data-row" onclick="editSale(' + s.id + ')">';
        h += '<td class="px-3 py-2 font-medium">' + escapeHtml(s.invoice_no || '-') + '</td>';
        h += '<td class="px-3 py-2">' + (s.sale_date ? s.sale_date.substring(0, 10) : '-') + '</td>';
        h += '<td class="px-3 py-2">' + escapeHtml(s.party_name || '-') + '</td>';
        h += '<td class="px-3 py-2">' + escapeHtml(s.location || '-') + '</td>';
        h += '<td class="px-3 py-2">' + tnDisplay + '</td>';
        h += '<td class="px-3 py-2">' + fmt((s.freight_amount || 0) * (s.weight_kgs || 0)) + '</td>';
        h += '<td class="px-3 py-2 font-bold">' + fmt(s.total_amount || s.invoice_value) + '</td>';
        h += '<td class="px-3 py-2">' + (s.weight_kgs || '-') + '</td>';
        h += '<td class="px-3 py-2">' + (s.gp_percent ? Number(s.gp_percent).toFixed(1) + '%' : '-') + '</td>';
        var lrHtml = '';
        if (s.lr_no) {
            var status = s.lr_tracking_status || '';
            var statusColors = {
                'Delivered': {bg: '#dcfce7', fg: '#166534'},
                'In Transit': {bg: '#dbeafe', fg: '#1e40af'},
                'Delayed': {bg: '#fef2f2', fg: '#991b1b'},
                'Out for Delivery': {bg: '#fef9c3', fg: '#854d0e'},
                'Pending': {bg: '#f1f5f9', fg: '#64748b'}
            };
            var sc = statusColors[status] || statusColors['Pending'];
            var trackLink = s.lr_tracking_url ? '<a href="' + escapeHtml(s.lr_tracking_url) + '" target="_blank" onclick="event.stopPropagation()" style="color:#4f46e5;font-size:10px;margin-left:4px;" title="Track on transporter website"><i class="fas fa-external-link-alt"></i></a>' : '';
            var statusOptions = ['', 'In Transit', 'Out for Delivery', 'Delivered', 'Delayed'];
            var selHtml = '<select onchange="event.stopPropagation();quickUpdateLrStatus(' + s.id + ', this.value)" style="border:1px solid ' + sc.fg + '30;border-radius:6px;padding:2px 6px;font-size:11px;font-weight:600;background:' + sc.bg + ';color:' + sc.fg + ';cursor:pointer;max-width:130px;outline:none;" onclick="event.stopPropagation()">';
            statusOptions.forEach(function(opt) {
                selHtml += '<option value="' + opt + '"' + (status === opt ? ' selected' : '') + '>' + (opt || 'Not Set') + '</option>';
            });
            selHtml += '</select>';
            lrHtml = '<div style="display:flex;flex-direction:column;gap:3px;">' +
                '<span style="font-size:11px;color:#64748b;font-weight:600;">' + escapeHtml(s.lr_no) + '</span>' +
                '<div style="display:flex;align-items:center;gap:3px;">' + selHtml + trackLink + '</div>' +
                '</div>';
        } else {
            lrHtml = '<button onclick="event.stopPropagation();showLrTrackingModal(' + s.id + ',\'\',\'\',\'\',\'' + (s.transporter_name||'').replace(/'/g,"\\'") + '\')" style="background:#f1f5f9;border:1px dashed #cbd5e1;border-radius:6px;padding:3px 8px;font-size:11px;color:#64748b;cursor:pointer;width:100%;">+ Add LR</button>';
        }
        lrHtml += '<button onclick="event.stopPropagation();showLrTrackingModal(' + s.id + ',\'' + (s.lr_no||'').replace(/'/g,"\\'") + '\',\'' + (s.lr_tracking_status||'').replace(/'/g,"\\'") + '\',\'' + (s.lr_tracking_url||'').replace(/'/g,"\\'") + '\',\'' + (s.transporter_name||'').replace(/'/g,"\\'") + '\')" style="background:none;border:none;color:#94a3b8;font-size:10px;cursor:pointer;margin-top:2px;text-align:left;">Details</button>';
        h += '<td class="px-3 py-2" onclick="event.stopPropagation()">' + lrHtml + '</td>';
        h += '<td class="px-3 py-2" onclick="event.stopPropagation()">';
        h += '<button onclick="editSale(' + s.id + ')" class="action-btn action-btn-edit" title="Edit"><i class="fas fa-pen"></i> Edit</button>';
        h += '<button onclick="deleteSale(' + s.id + ')" class="action-btn action-btn-delete ml-1" title="Delete"><i class="fas fa-trash"></i></button>';
        h += '</td></tr>';
        rows.push({vals: [s.invoice_no||'', s.sale_date||'', s.party_name||'', s.location||'', s.transporter_name||'', (s.freight_amount||0)*(s.weight_kgs||0), s.total_amount||s.invoice_value||0, s.weight_kgs||0, s.gp_percent||0, s.lr_tracking_status||''], html: h});
    });
    _tableData['t-sales'] = rows;
    _sortState['t-sales'] = null;
    $('t-sales').innerHTML = rows.map(function(r){return r.html;}).join('') || '<tr><td colspan="11" class="text-center py-4 text-gray-400">No sales</td></tr>';
    } catch(e) { console.error('loadSales error:', e); toast('Error loading sales: ' + e.message, true); }
}

async function addTransporterFromSales(name) {
    _transporters = await api('/api/transporters');
    var existing = _transporters.find(function(t) { return t.name.toLowerCase() === name.toLowerCase(); });
    if (existing) {
        editTransporter(existing.id);
    } else {
        $('f-tid').value = '';
        $('f-ttransid').value = '';
        $('f-tname').value = name;
        $('f-tphone').value = '';
        $('f-temail').value = '';
        $('f-taddr').value = '';
        $('f-tstate').value = '';
        $('f-tdistrict').value = '';
        $('f-tcity').value = '';
        $('f-tpincode').value = '';
        $('f-tgst').value = '';
        $('f-tpan').value = '';
        $('f-tcontactperson').value = '';
        $('f-tcontactnum').value = '';
        $('f-ttrackurl').value = '';
        $('f-tblacklisted').checked = false;
        $('f-tgstfile-name').innerHTML = '';
        $('f-tpanfile-name').innerHTML = '';
        $('m-trans-title').textContent = 'Add Transporter - ' + name;
        showModal('m-transporter');
    }
}

async function deleteSale(id) {
    if (!confirm('Delete this sale?')) return;
    await api('/api/sales/' + id, {method: 'DELETE'});
    toast('Sale deleted');
    loadSales();
}

function showLrTrackingModal(saleId, lrNo, status, url, transporter) {
    $('f-lrsaleid').value = saleId;
    $('f-lrlrno').value = lrNo || '';
    $('f-lrtransporter').value = transporter || '';
    $('f-lrstatus').value = status || '';
    $('f-lrurl').value = url || '';
    if (url) {
        $('f-lrlink').style.display = 'block';
        $('f-lrlinka').href = url;
    } else {
        $('f-lrlink').style.display = 'none';
    }
    showModal('m-lr-tracking');
}

async function generateTrackingUrl() {
    var saleId = $('f-lrsaleid').value;
    var lrNo = $('f-lrlrno').value.trim();
    if (!lrNo) {
        toast('Enter an LR number first', true);
        return;
    }
    try {
        var result = await api('/api/sales/' + saleId + '/generate-tracking-url', {method: 'POST'});
        if (result.tracking_url) {
            $('f-lrurl').value = result.tracking_url;
            $('f-lrlink').style.display = 'block';
            $('f-lrlinka').href = result.tracking_url;
            toast('Tracking URL generated!');
        } else {
            toast(result.message || 'No tracking URL pattern configured for this transporter. Add it in Transporter settings.', true);
        }
    } catch(e) {
        toast('Error: ' + e.message, true);
    }
}

async function fetchSingleTracking() {
    var saleId = $('f-lrsaleid').value;
    var lrNo = $('f-lrlrno').value.trim();
    var btn = $('btn-fetch-tracking');
    if (!lrNo) {
        toast('Enter an LR number first', true);
        return;
    }
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Fetching...';
    btn.disabled = true;
    try {
        var lrPayload = {lr_no: lrNo, lr_tracking_status: $('f-lrstatus').value, lr_tracking_url: $('f-lrurl').value};
        await api('/api/sales/' + saleId + '/lr-tracking', {method: 'PUT', body: JSON.stringify(lrPayload)});
        var result = await api('/api/fetch-tracking/' + saleId, {method: 'POST'});
        if (result.status) {
            $('f-lrstatus').value = result.status;
            toast('Status fetched: ' + result.status + (result.location ? ' at ' + result.location : ''));
            if (result.history && result.history.length > 0) {
                var histHtml = '<div style="margin-top:12px;border-top:1px solid #e2e8f0;padding-top:12px;">';
                histHtml += '<p style="font-size:12px;font-weight:600;color:#374151;margin-bottom:8px;">Tracking History (' + escapeHtml(result.source || '') + '):</p>';
                result.history.reverse().forEach(function(h) {
                    histHtml += '<div style="display:flex;gap:8px;font-size:11px;padding:4px 0;border-bottom:1px solid #f1f5f9;">';
                    histHtml += '<span style="color:#94a3b8;white-space:nowrap;">' + escapeHtml(h.date || '-') + '</span>';
                    histHtml += '<span style="color:#64748b;">' + escapeHtml(h.location || '-') + '</span>';
                    histHtml += '<span style="color:#0f172a;font-weight:600;">' + escapeHtml(h.status || '') + '</span>';
                    histHtml += '</div>';
                });
                histHtml += '</div>';
                var linkDiv = $('f-lrlink');
                linkDiv.insertAdjacentHTML('afterend', histHtml);
            }
        } else {
            toast(result.message || 'Could not fetch tracking status', true);
        }
    } catch(e) {
        toast('Error: ' + e.message, true);
    }
    btn.innerHTML = '<i class="fas fa-sync-alt mr-1"></i> Fetch Status';
    btn.disabled = false;
}

async function saveLrTracking() {
    var saleId = $('f-lrsaleid').value;
    var lrNo = $('f-lrlrno').value.trim();
    var status = $('f-lrstatus').value;
    var url = $('f-lrurl').value;

    var payload = {lr_no: lrNo, lr_tracking_status: status, lr_tracking_url: url};
    await api('/api/sales/' + saleId + '/lr-tracking', {
        method: 'PUT',
        body: JSON.stringify(payload)
    });

    if (lrNo && !url) {
        try {
            var result = await api('/api/sales/' + saleId + '/generate-tracking-url', {method: 'POST'});
            if (result.tracking_url) {
                await api('/api/sales/' + saleId + '/lr-tracking', {
                    method: 'PUT',
                    body: JSON.stringify({lr_tracking_url: result.tracking_url})
                });
            }
        } catch(e) {}
    }

    toast('LR tracking updated!');
    hideModal('m-lr-tracking');
    loadSales();
}

async function quickUpdateLrStatus(saleId, newStatus) {
    try {
        await api('/api/sales/' + saleId + '/lr-tracking', {
            method: 'PUT',
            body: JSON.stringify({ lr_tracking_status: newStatus })
        });
        toast('Status updated to: ' + (newStatus || 'Not Set'));
        loadSales();
    } catch(e) {
        toast('Error updating status: ' + e.message, true);
        loadSales();
    }
}

async function fetchBulkTracking() {
    var btn = $('btn-fetch-all-tracking');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin" style="margin-right:4px;"></i>Fetching...';
    btn.disabled = true;
    try {
        var result = await api('/api/fetch-tracking-bulk', {method: 'POST'});
        toast('Updated ' + result.updated + ' shipments');
        loadSales();
    } catch(e) {
        toast('Error: ' + e.message, true);
    }
    btn.innerHTML = '<i class="fas fa-sync-alt" style="margin-right:4px;"></i>Fetch All Tracking';
    btn.disabled = false;
}

async function editSale(id) {
    await refreshDropdowns();
    var s = await api('/api/sales/' + id);
    if (!s) return;
    $('f-slid').value = s.id;
    $('m-sale-title').textContent = 'Edit Sale';
    if ($('f-slcust')) {
        if (s.customer_id) {
            $('f-slcust').value = s.customer_id;
        } else {
            $('f-slcust').value = '';
        }
    }
    if (s.party_name) {
        var dd = $('f-slcust');
        if (dd) {
            var alreadyThere = false;
            for (var i = 0; i < dd.options.length; i++) {
                if (dd.options[i].text === s.party_name || dd.options[i].text.indexOf(s.party_name) !== -1) {
                    dd.selectedIndex = i;
                    alreadyThere = true;
                    break;
                }
            }
            if (!alreadyThere && !s.customer_id) {
                var opt = document.createElement('option');
                opt.value = '';
                opt.textContent = s.party_name;
                opt.selected = true;
                dd.prepend(opt);
            }
        }
    }
    if ($('f-slfrt')) $('f-slfrt').value = s.freight_amount || 0;
    if ($('f-slinvval')) $('f-slinvval').value = s.invoice_value || 0;
    if ($('f-slstatus')) $('f-slstatus').value = s.payment_status || 'Pending';
    if ($('f-slmethod')) $('f-slmethod').value = s.payment_method || 'Cash';
    if ($('f-sltransporter')) $('f-sltransporter').value = s.transporter_name || '';
    if ($('f-sllrno')) $('f-sllrno').value = s.lr_no || '';
    _saleItems = (s.items && s.items.length > 0) ? s.items.map(function(item) {
        return {
            product_id: item.product_id, quantity: item.quantity,
            unit_price: item.unit_price, discount_percent: item.discount_percent,
            taxable_amount: item.taxable_amount, gst_rate: item.gst_rate,
            cgst_amount: item.cgst_amount, sgst_amount: item.sgst_amount,
            total_amount: item.total_amount
        };
    }) : [{
        product_id: s.product_id || 0, quantity: s.quantity || 0,
        unit_price: s.unit_price || 0, discount_percent: s.discount_percent || 0,
        taxable_amount: s.taxable_amount || 0, gst_rate: 18,
        cgst_amount: s.cgst_amount || 0, sgst_amount: s.sgst_amount || 0,
        total_amount: s.total_amount || 0
    }];
    renderSaleItems();
    calcSaleTotals();
    showModal('m-sale');
}

function addSaleItem() {
    _saleItems.push({
        product_id: 0, quantity: 1, unit_price: 0, discount_percent: 0,
        taxable_amount: 0, gst_rate: 18, cgst_amount: 0, sgst_amount: 0, total_amount: 0
    });
    renderSaleItems();
}

function removeSaleItem(idx) {
    _saleItems.splice(idx, 1);
    renderSaleItems();
    calcSaleTotals();
}

function updateSaleItem(idx, field, value) {
    _saleItems[idx][field] = value;
}

async function onSaleProductChange(idx, pid) {
    if (!pid) return;
    try {
        var pr = await api('/api/products/' + pid + '/pricing');
        if (pr) {
            _saleItems[idx].unit_price = pr.mrp || pr.dealer_price || pr.distributor_price || 0;
            _saleItems[idx].gst_rate = pr.gst_rate || 18;
        }
    } catch(e) {}
    calcSaleItemAmount(idx);
    renderSaleItems();
    calcSaleTotals();
}

function calcSaleItemAmount(idx) {
    var item = _saleItems[idx];
    var taxable = (item.quantity || 0) * (item.unit_price || 0);
    var discAmt = taxable * (item.discount_percent || 0) / 100;
    taxable -= discAmt;
    var cgst = taxable * (item.gst_rate || 18) / 200;
    var sgst = taxable * (item.gst_rate || 18) / 200;
    item.taxable_amount = taxable;
    item.cgst_amount = cgst;
    item.sgst_amount = sgst;
    item.total_amount = taxable + cgst + sgst;
}

function calcSaleTotals() {
    var totalQty = 0;
    var totalTaxable = 0;
    var totalCgst = 0;
    var totalSgst = 0;
    var frtEl = $('f-slfrt');
    var frt = frtEl ? (parseFloat(frtEl.value) || 0) : 0;
    _saleItems.forEach(function(item) {
        calcSaleItemAmount(_saleItems.indexOf(item));
        totalQty += item.quantity || 0;
        totalTaxable += item.taxable_amount;
        totalCgst += item.cgst_amount;
        totalSgst += item.sgst_amount;
    });
    var grandTotal = totalTaxable + totalCgst + totalSgst + frt;
    if ($('sale-total-qty')) $('sale-total-qty').textContent = totalQty;
    if ($('sale-total-amount')) $('sale-total-amount').textContent = fmt(grandTotal);
    if ($('sv-tax')) $('sv-tax').textContent = fmt(totalTaxable);
    if ($('sv-cgst')) $('sv-cgst').textContent = fmt(totalCgst);
    if ($('sv-sgst')) $('sv-sgst').textContent = fmt(totalSgst);
    if ($('sv-frt')) $('sv-frt').textContent = fmt(frt);
    if ($('sv-total')) $('sv-total').textContent = fmt(grandTotal);
    if ($('f-slinvval')) $('f-slinvval').value = grandTotal.toFixed(2);
}

function renderSaleItems() {
    var h = '';
    _saleItems.forEach(function(item, idx) {
        var prodOpts = '<option value="0">-- Select --</option>';
        _products.forEach(function(p) {
            var sel = item.product_id == p.id ? ' selected' : '';
            prodOpts += '<option value="' + p.id + '"' + sel + '>' + escapeHtml(p.name) + '</option>';
        });
        h += '<tr style="border-bottom:1px solid #f1f5f9;">';
        h += '<td class="px-2 py-1"><select onchange="updateSaleItem(' + idx + ',\'product_id\',parseInt(this.value));onSaleProductChange(' + idx + ',this.value)" style="width:100%;border:1px solid #e2e8f0;border-radius:4px;padding:4px;font-size:12px;">' + prodOpts + '</select></td>';
        h += '<td class="px-2 py-1"><input type="number" min="0" value="' + (item.quantity || 0) + '" onchange="updateSaleItem(' + idx + ',\'quantity\',parseInt(this.value));calcSaleItemAmount(' + idx + ');renderSaleItems();calcSaleTotals()" style="width:100%;border:1px solid #e2e8f0;border-radius:4px;padding:4px;text-align:right;font-size:12px;"></td>';
        h += '<td class="px-2 py-1"><input type="number" min="0" step="0.01" value="' + (item.unit_price || 0) + '" onchange="updateSaleItem(' + idx + ',\'unit_price\',parseFloat(this.value));calcSaleItemAmount(' + idx + ');renderSaleItems();calcSaleTotals()" style="width:100%;border:1px solid #e2e8f0;border-radius:4px;padding:4px;text-align:right;font-size:12px;"></td>';
        h += '<td class="px-2 py-1"><input type="number" min="0" max="100" step="0.01" value="' + (item.discount_percent || 0) + '" onchange="updateSaleItem(' + idx + ',\'discount_percent\',parseFloat(this.value));calcSaleItemAmount(' + idx + ');renderSaleItems();calcSaleTotals()" style="width:100%;border:1px solid #e2e8f0;border-radius:4px;padding:4px;text-align:right;font-size:12px;"></td>';
        h += '<td class="px-2 py-1 text-right" style="font-size:12px;font-weight:600;">' + fmt(item.total_amount || 0) + '</td>';
        h += '<td class="px-2 py-1 text-center"><button type="button" onclick="removeSaleItem(' + idx + ')" style="color:#ef4444;background:none;border:none;cursor:pointer;font-size:14px;" title="Remove"><i class="fas fa-times"></i></button></td>';
        h += '</tr>';
    });
    $('sale-items-body').innerHTML = h || '<tr><td colspan="6" class="text-center py-3 text-gray-400" style="font-size:12px;">No items. Click "Add Item" to begin.</td></tr>';
}

async function loadExpenses() {
    showLoading('t-expenses', 6);
    var expenses = await api('/api/expenses');
    var sales = await api('/api/sales/freight-summary');
    var sortRows = [];
    var totalFreight = 0;

    sales.forEach(function(s) {
        var frt = parseFloat(s.freight_amount) || 0;
        var wt = parseFloat(s.weight_kgs) || 0;
        var freightCost = frt * wt;
        if (freightCost > 0) {
            totalFreight += freightCost;
            var h = '<tr class="border-b freight-row">';
            h += '<td class="px-3 py-2">' + (s.sale_date ? s.sale_date.substring(0, 10) : '-') + '</td>';
            h += '<td class="px-3 py-2"><span class="px-2 py-1 rounded text-xs bg-orange-100 text-orange-700">Freight</span></td>';
            h += '<td class="px-3 py-2">Freight for ' + escapeHtml(s.invoice_no || 'Sale #' + s.id) + ' (' + wt + ' kg x ' + fmt(frt) + '/kg)</td>';
            h += '<td class="px-3 py-2">' + escapeHtml(s.transporter_name || '-') + '</td>';
            h += '<td class="px-3 py-2 font-bold text-orange-600">' + fmt(freightCost) + '</td>';
            h += '<td class="px-3 py-2"></td>';
            h += '</tr>';
            sortRows.push({vals: [s.sale_date||'', 'Freight', 'Freight for ' + (s.invoice_no||''), s.transporter_name||'', freightCost], html: h});
        }
    });

    expenses.forEach(function(e) {
        var h = '<tr class="border-b data-row" onclick="editExpense(' + e.id + ')">';
        h += '<td class="px-3 py-2">' + (e.expense_date ? e.expense_date.substring(0, 10) : '-') + '</td>';
        h += '<td class="px-3 py-2"><span class="px-2 py-1 rounded text-xs bg-blue-100 text-blue-700">' + escapeHtml(e.category) + '</span></td>';
        h += '<td class="px-3 py-2">' + escapeHtml(e.description || '-') + '</td>';
        h += '<td class="px-3 py-2">' + escapeHtml(e.vendor || '-') + '</td>';
        h += '<td class="px-3 py-2 font-bold text-red-600">' + fmt(e.amount) + '</td>';
        h += '<td class="px-3 py-2" onclick="event.stopPropagation()">';
        h += '<button onclick="editExpense(' + e.id + ')" class="action-btn action-btn-edit" title="Edit"><i class="fas fa-pen"></i> Edit</button>';
        h += '<button onclick="deleteExpense(' + e.id + ')" class="action-btn action-btn-delete ml-1" title="Delete"><i class="fas fa-trash"></i></button>';
        h += '</td></tr>';
        sortRows.push({vals: [e.expense_date||'', e.category, e.description||'', e.vendor||'', e.amount||0], html: h});
    });

    _tableData['t-expenses'] = sortRows;
    _sortState['t-expenses'] = null;
    $('t-expenses').innerHTML = sortRows.map(function(r){return r.html;}).join('') || '<tr><td colspan="6" class="text-center py-4 text-gray-400">No expenses</td></tr>';
}

async function editExpense(id) {
    var expenses = await api('/api/expenses');
    var e = expenses.find(function(x) { return x.id === id; });
    if (!e) return;
    $('f-eid').value = e.id;
    $('m-expense-title').textContent = 'Edit Expense';
    $('f-ecat').value = e.category || '';
    $('f-edesc').value = e.description || '';
    $('f-eamt').value = e.amount || '';
    $('f-evendor').value = e.vendor || '';
    $('f-edate').value = e.expense_date ? e.expense_date.substring(0, 10) : '';
    showModal('m-expense');
}

async function deleteExpense(id) {
    if (!confirm('Delete this expense?')) return;
    await api('/api/expenses/' + id, {method: 'DELETE'});
    toast('Expense deleted');
    loadExpenses();
}

async function loadDashboard() {
    try {
    var d = await api('/api/dashboard');
    var html = '';
    html += '<div class="stat-card card-indigo"><div style="display:flex;justify-content:space-between;align-items:flex-start;"><div><p class="stat-label">Products</p><p class="stat-value" style="color:#4f46e5;">' + d.total_products + '</p></div><div class="stat-icon indigo"><i class="fas fa-box"></i></div></div></div>';
    html += '<div class="stat-card card-blue"><div style="display:flex;justify-content:space-between;align-items:flex-start;"><div><p class="stat-label">Customers</p><p class="stat-value" style="color:#3b82f6;">' + d.total_customers + '</p></div><div class="stat-icon blue"><i class="fas fa-users"></i></div></div></div>';
    html += '<div class="stat-card card-purple"><div style="display:flex;justify-content:space-between;align-items:flex-start;"><div><p class="stat-label">Orders (COGS)</p><p class="stat-value" style="color:#8b5cf6;">' + d.total_orders + '</p><p class="stat-sub">' + fmt(d.total_order_value) + ' invoiced</p></div><div class="stat-icon purple"><i class="fas fa-clipboard-list"></i></div></div></div>';
    html += '<div class="stat-card card-green"><div style="display:flex;justify-content:space-between;align-items:flex-start;"><div><p class="stat-label">Sales</p><p class="stat-value" style="color:#10b981;">' + d.total_sales + '</p><p class="stat-sub">' + fmt(d.revenue) + ' revenue</p></div><div class="stat-icon green"><i class="fas fa-shopping-cart"></i></div></div></div>';
    html += '<div class="stat-card card-orange"><div style="display:flex;justify-content:space-between;align-items:flex-start;"><div><p class="stat-label">Freight</p><p class="stat-value" style="color:#f59e0b;">' + fmt(d.freight) + '</p></div><div class="stat-icon orange"><i class="fas fa-truck"></i></div></div></div>';
    html += '<div class="stat-card card-red"><div style="display:flex;justify-content:space-between;align-items:flex-start;"><div><p class="stat-label">Pending</p><p class="stat-value" style="color:#ef4444;">' + fmt(d.pending) + '</p></div><div class="stat-icon red"><i class="fas fa-exclamation-triangle"></i></div></div></div>';
    $('dash-cards').innerHTML = html;

    var lrHtml = '';
    lrHtml += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">';
    lrHtml += '<div style="background:#dbeafe;border-radius:10px;padding:16px;text-align:center;border:1px solid #bfdbfe;"><p style="font-size:24px;font-weight:800;color:#1e40af;">' + (d.lr_in_transit || 0) + '</p><p style="font-size:12px;color:#1e40af;font-weight:600;margin-top:2px;">In Transit</p></div>';
    lrHtml += '<div style="background:#dcfce7;border-radius:10px;padding:16px;border:1px solid #bbf7d0;"><p style="font-size:24px;font-weight:800;color:#166534;">' + (d.lr_delivered || 0) + '</p><p style="font-size:12px;color:#166534;font-weight:600;margin-top:2px;">Delivered</p></div>';
    lrHtml += '<div style="background:#fef2f2;border-radius:10px;padding:16px;border:1px solid #fecaca;"><p style="font-size:24px;font-weight:800;color:#991b1b;">' + (d.lr_delayed || 0) + '</p><p style="font-size:12px;color:#991b1b;font-weight:600;margin-top:2px;">Delayed</p></div>';
    lrHtml += '<div style="background:#f1f5f9;border-radius:10px;padding:16px;border:1px solid #e2e8f0;"><p style="font-size:24px;font-weight:800;color:#64748b;">' + (d.lr_pending || 0) + '</p><p style="font-size:12px;color:#64748b;font-weight:600;margin-top:2px;">Pending</p></div>';
    $('dash-lr').innerHTML = lrHtml;

    var oh = '';
    if (d.recent_orders && d.recent_orders.length) {
        d.recent_orders.forEach(function(o) {
            oh += '<div style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid #f1f5f9;transition:all 0.15s;border-radius:8px;cursor:pointer;" onmouseover="this.style.background=\'#f8fafc\'" onmouseout="this.style.background=\'transparent\'">';
            oh += '<div><p style="font-weight:600;font-size:14px;color:#0f172a;">' + escapeHtml(o.po_no || 'Order #' + o.sl_no) + '</p>';
            oh += '<p style="font-size:12px;color:#94a3b8;margin-top:2px;">' + escapeHtml(o.customer_name || o.billing_site || '') + (o.entry_date ? ' &middot; ' + escapeHtml(o.entry_date) : '') + '</p></div>';
            oh += '<div style="text-align:right;"><p style="font-weight:700;font-size:14px;color:#0f172a;">' + fmt(o.invoice_amount) + '</p>';
            oh += '<p style="font-size:11px;color:#94a3b8;">' + escapeHtml(o.invoice_no || '-') + '</p></div></div>';
        });
    } else {
        oh = '<p style="color:#94a3b8;font-size:14px;text-align:center;padding:24px;">No orders yet</p>';
    }
    $('dash-orders').innerHTML = oh;

    var rh = '';
    if (d.recent_sales && d.recent_sales.length) {
        d.recent_sales.forEach(function(s) {
            var statusColor = s.status === 'Paid' ? 'color:#10b981;background:#ecfdf5;' : 'color:#f59e0b;background:#fffbeb;';
            rh += '<div style="display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid #f1f5f9;transition:all 0.15s;border-radius:8px;cursor:pointer;" onmouseover="this.style.background=\'#f8fafc\'" onmouseout="this.style.background=\'transparent\'">';
            rh += '<div><p style="font-weight:600;font-size:14px;color:#0f172a;">' + escapeHtml(s.customer || 'Unknown') + '</p>';
            rh += '<p style="font-size:12px;color:#94a3b8;margin-top:2px;">' + escapeHtml(s.invoice || '') + (s.date ? ' &middot; ' + escapeHtml(s.date) : '') + '</p></div>';
            rh += '<div style="text-align:right;"><p style="font-weight:700;font-size:14px;color:#0f172a;">' + fmt(s.amount) + '</p>';
            if (s.status) {
                rh += '<span style="font-size:11px;font-weight:600;padding:2px 8px;border-radius:12px;display:inline-block;margin-top:2px;' + statusColor + '">' + escapeHtml(s.status) + '</span>';
            }
            rh += '</div></div>';
        });
    } else {
        rh = '<p style="color:#94a3b8;font-size:14px;text-align:center;padding:24px;">No sales yet</p>';
    }
    $('dash-recent').innerHTML = rh;

    if (d.revenue_chart && d.revenue_chart.labels && d.revenue_chart.labels.length) {
        var ctx1 = document.getElementById('chart-dash-revenue');
        if (ctx1) {
            if (ctx1._chartInstance) ctx1._chartInstance.destroy();
            ctx1._chartInstance = new Chart(ctx1.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: d.revenue_chart.labels,
                    datasets: [{label: 'Revenue', data: d.revenue_chart.data, backgroundColor: 'rgba(99,102,241,0.7)', borderRadius: 6}]
                },
                options: {responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false}},y:{grid:{color:'#f1f5f9'},ticks:{callback:function(v){return '₹'+v.toLocaleString('en-IN')}}}}}
            });
        }
    }

    if (d.location_chart && d.location_chart.labels && d.location_chart.labels.length) {
        var ctx2 = document.getElementById('chart-dash-location');
        if (ctx2) {
            var colors = ['#6366f1','#10b981','#f59e0b','#ef4444','#3b82f6','#8b5cf6','#ec4899','#06b6d4'];
            if (ctx2._chartInstance) ctx2._chartInstance.destroy();
            ctx2._chartInstance = new Chart(ctx2.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: d.location_chart.labels,
                    datasets: [{data: d.location_chart.data, backgroundColor: colors.slice(0, d.location_chart.labels.length), borderWidth: 0}]
                },
                options: {responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{font:{size:11},padding:8}}}}
            });
        }
    }
    } catch(e) { console.error('Dashboard error:', e); }
}

async function loadReport() {
    try {
    var from = $('rpt-from') ? $('rpt-from').value : '';
    var to = $('rpt-to') ? $('rpt-to').value : '';
    var params = [];
    if (from) params.push('start_date=' + from);
    if (to) params.push('end_date=' + to);
    var url = '/api/reports/profit-loss' + (params.length ? '?' + params.join('&') : '');
    var d = await api(url);
    var h = '';

    h += '<div class="grid grid-cols-4 gap-4 mb-6">';
    h += '<div style="background:linear-gradient(135deg,#ecfdf5,#d1fae5);border-radius:12px;padding:20px;border:1px solid #a7f3d0;"><p style="font-size:12px;font-weight:600;color:#059669;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">Revenue (Sales)</p><p style="font-size:26px;font-weight:800;color:#047857;letter-spacing:-0.03em;">' + fmt(d.total_revenue) + '</p><p style="font-size:12px;color:#6b7280;margin-top:4px;">' + d.total_sales + ' sales &middot; ' + d.units + ' units</p></div>';
    h += '<div style="background:linear-gradient(135deg,#fef2f2,#fee2e2);border-radius:12px;padding:20px;border:1px solid #fecaca;"><p style="font-size:12px;font-weight:600;color:#dc2626;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">COGS (Orders)</p><p style="font-size:26px;font-weight:800;color:#b91c1c;letter-spacing:-0.03em;">' + fmt(d.total_cogs) + '</p><p style="font-size:12px;color:#6b7280;margin-top:4px;">' + d.total_orders + ' orders &middot; ' + d.order_boxes + ' boxes</p></div>';
    h += '<div style="background:linear-gradient(135deg,#f5f3ff,#ede9fe);border-radius:12px;padding:20px;border:1px solid #c4b5fd;"><p style="font-size:12px;font-weight:600;color:#7c3aed;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">Gross Profit</p><p style="font-size:26px;font-weight:800;color:#6d28d9;letter-spacing:-0.03em;">' + fmt(d.gross_profit) + '</p><p style="font-size:12px;color:#6b7280;margin-top:4px;">' + d.gross_margin.toFixed(1) + '% margin</p></div>';
    h += '<div style="background:linear-gradient(135deg,#fffbeb,#fef3c7);border-radius:12px;padding:20px;border:1px solid #fde68a;"><p style="font-size:12px;font-weight:600;color:#d97706;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">EBITDA</p><p style="font-size:26px;font-weight:800;color:#b45309;letter-spacing:-0.03em;">' + fmt(d.ebitda) + '</p><p style="font-size:12px;color:#6b7280;margin-top:4px;">' + d.ebitda_margin.toFixed(1) + '% margin</p></div>';
    h += '</div>';

    h += '<div style="margin-bottom:20px;padding:20px;background:linear-gradient(135deg,#ecfdf5,#f0fdfa);border-radius:12px;border:1px solid #a7f3d0;"><h4 style="font-weight:700;color:#047857;margin-bottom:12px;font-size:15px;display:flex;align-items:center;gap:8px;"><span style="width:28px;height:28px;border-radius:8px;background:#d1fae5;display:inline-flex;align-items:center;justify-content:center;font-size:13px;"><i class="fas fa-arrow-up"></i></span>Revenue (Sales)</h4>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">Sales Revenue:</span><span style="font-weight:700;color:#0f172a;">' + fmt(d.sale_revenue) + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">Sales Freight:</span><span style="font-weight:700;color:#0f172a;">' + fmt(d.sale_freight) + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">GST Collected:</span><span style="font-weight:700;color:#0f172a;">' + fmt(d.gst) + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">Units Sold:</span><span style="font-weight:700;color:#0f172a;">' + d.units + '</span></div>';
    if (d.gp_from_sales > 0) {
        h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">GP (from Sales CSV):</span><span style="font-weight:700;color:#0f172a;">' + fmt(d.gp_from_sales) + '</span></div>';
    }
    if (d.gp_avg > 0) {
        h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">Avg GP%:</span><span style="font-weight:700;color:#0f172a;">' + d.gp_avg.toFixed(1) + '%</span></div>';
    }
    h += '</div>';

    h += '<div style="margin-bottom:20px;padding:20px;background:linear-gradient(135deg,#fef2f2,#fff1f2);border-radius:12px;border:1px solid #fecaca;"><h4 style="font-weight:700;color:#dc2626;margin-bottom:12px;font-size:15px;display:flex;align-items:center;gap:8px;"><span style="width:28px;height:28px;border-radius:8px;background:#fee2e2;display:inline-flex;align-items:center;justify-content:center;font-size:13px;"><i class="fas fa-arrow-down"></i></span>Cost of Goods (Orders)</h4>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">Order Value (excl GST):</span><span style="font-weight:700;color:#0f172a;">' + fmt(d.order_cogs) + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">Transport/Freight Cost:</span><span style="font-weight:700;color:#0f172a;">' + fmt(d.order_freight_cost) + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">Total Invoice Amount:</span><span style="font-weight:700;color:#0f172a;">' + fmt(d.order_invoice_total) + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">Total Boxes:</span><span style="font-weight:700;color:#0f172a;">' + d.order_boxes + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">Total Weight:</span><span style="font-weight:700;color:#0f172a;">' + Number(d.order_weight).toLocaleString('en-IN') + ' Kgs</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">Credit Notes:</span><span style="font-weight:700;color:#ef4444;">' + fmt(d.order_credit_notes) + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding:8px 0 0;margin-top:8px;border-top:2px solid #fecaca;font-weight:700;font-size:14px;"><span style="color:#374151;">Total COGS:</span><span style="color:#ef4444;">' + fmt(d.total_cogs) + '</span></div>';
    h += '</div>';

    var gpC = d.gross_profit >= 0 ? 'color:#059669' : 'color:#ef4444';
    h += '<div style="margin-bottom:20px;padding:20px;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;"><h4 style="font-weight:700;color:#374151;margin-bottom:12px;font-size:15px;display:flex;align-items:center;gap:8px;"><span style="width:28px;height:28px;border-radius:8px;background:#e2e8f0;display:inline-flex;align-items:center;justify-content:center;font-size:13px;"><i class="fas fa-calculator"></i></span>Gross Profit = Revenue - COGS</h4>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">Revenue:</span><span style="font-weight:700;color:#0f172a;">' + fmt(d.total_revenue) + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">Less: COGS:</span><span style="font-weight:700;color:#ef4444;">' + fmt(d.total_cogs) + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">Less: Credit Notes:</span><span style="font-weight:700;color:#ef4444;">' + fmt(d.order_credit_notes) + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding:10px 0 0;margin-top:10px;border-top:2px solid #e2e8f0;font-size:16px;"><span style="font-weight:700;color:#0f172a;">Gross Profit:</span><span style="font-weight:800;' + gpC + ';">' + fmt(d.gross_profit) + ' (' + d.gross_margin.toFixed(1) + '%)</span></div>';
    h += '</div>';

    h += '<div style="margin-bottom:20px;padding:20px;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;"><h4 style="font-weight:700;color:#d97706;margin-bottom:12px;font-size:15px;display:flex;align-items:center;gap:8px;"><span style="width:28px;height:28px;border-radius:8px;background:#fef3c7;display:inline-flex;align-items:center;justify-content:center;font-size:13px;"><i class="fas fa-building"></i></span>Operating Expenses</h4>';
    var keys = Object.keys(d.expenses || {});
    if (keys.length) {
        keys.forEach(function(k) { h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;"><span style="color:#374151;">' + escapeHtml(k) + ':</span><span style="font-weight:700;color:#ef4444;">' + fmt(d.expenses[k]) + '</span></div>'; });
    } else {
        h += '<p style="color:#94a3b8;font-size:14px;text-align:center;padding:16px;">No expenses recorded</p>';
    }
    h += '<div style="display:flex;justify-content:space-between;padding:8px 0 0;margin-top:8px;border-top:2px solid #e2e8f0;font-weight:700;font-size:14px;"><span style="color:#374151;">Total OpEx:</span><span style="color:#ef4444;">' + fmt(d.total_opex) + '</span></div></div>';

    var ebC = d.ebitda >= 0 ? 'color:#4f46e5' : 'color:#ef4444';
    h += '<div style="margin-bottom:20px;padding:20px;background:linear-gradient(135deg,#eef2ff,#e0e7ff);border-radius:12px;border:1px solid #c7d2fe;"><h4 style="font-weight:700;color:#4338ca;margin-bottom:12px;font-size:15px;">EBITDA = Gross Profit - OpEx</h4>';
    h += '<div style="display:flex;justify-content:space-between;font-size:18px;"><span style="font-weight:600;color:#374151;">Amount:</span><span style="font-weight:800;' + ebC + ';">' + fmt(d.ebitda) + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding-top:4px;font-size:14px;"><span style="color:#6b7280;">Margin:</span><span style="font-weight:700;color:#0f172a;">' + d.ebitda_margin.toFixed(1) + '%</span></div></div>';

    var paC = d.pat >= 0 ? 'color:#10b981' : 'color:#ef4444';
    h += '<div style="padding:24px;background:linear-gradient(135deg,#0f172a,#1e293b);color:white;border-radius:12px;"><h4 style="font-weight:700;margin-bottom:16px;font-size:15px;">Profit After Tax</h4>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;opacity:0.8;"><span>PBT:</span><span style="font-weight:700;">' + fmt(d.ebitda) + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding:6px 0;font-size:14px;opacity:0.8;"><span>Tax @ ' + d.tax_rate + '%:</span><span style="font-weight:700;color:#f87171;">' + fmt(d.tax) + '</span></div>';
    h += '<div style="display:flex;justify-content:space-between;padding:12px 0 0;margin-top:12px;border-top:2px solid rgba(255,255,255,0.15);font-size:22px;"><span style="font-weight:700;">PAT:</span><span style="font-weight:800;' + paC + ';">' + fmt(d.pat) + '</span></div></div>';

    $('rpt-body').innerHTML = h;

    try { renderReportCharts(d); } catch(chartErr) { console.warn('Chart render error:', chartErr); }
    } catch(e) { console.error('Report error:', e); $('rpt-body').innerHTML = '<p class="text-red-500">Error loading report</p>'; }
}

var _reportCharts = {};
function destroyCharts() {
    Object.keys(_reportCharts).forEach(function(k) { if (_reportCharts[k]) _reportCharts[k].destroy(); });
    _reportCharts = {};
}

function renderReportCharts(d) {
    destroyCharts();
    if (typeof Chart === 'undefined') { console.warn('Chart.js not loaded'); return; }
    var colors = {
        indigo: '#6366f1', green: '#10b981', red: '#ef4444', orange: '#f59e0b',
        purple: '#8b5cf6', blue: '#3b82f6', yellow: '#eab308', teal: '#14b8a6',
        pink: '#ec4899', cyan: '#06b6d4', lime: '#84cc16', rose: '#f43f5e'
    };

    // Revenue vs COGS Bar Chart
    var ctx1 = document.getElementById('chart-revenue');
    if (ctx1) {
        _reportCharts.revenue = new Chart(ctx1, {
            type: 'bar',
            data: {
                labels: ['Revenue (Sales)', 'COGS (Orders)', 'Freight Cost', 'Credit Notes'],
                datasets: [{
                    label: 'Amount',
                    data: [d.total_revenue || 0, d.total_cogs || 0, d.order_freight_cost || 0, d.order_credit_notes || 0],
                    backgroundColor: [
                        'rgba(16, 185, 129, 0.85)',
                        'rgba(239, 68, 68, 0.85)',
                        'rgba(245, 158, 11, 0.85)',
                        'rgba(234, 179, 8, 0.85)'
                    ],
                    borderColor: [colors.green, colors.red, colors.orange, colors.yellow],
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Revenue vs COGS', font: { size: 15, weight: 'bold', family: 'Inter' }, padding: { bottom: 16 } },
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { font: { family: 'Inter', size: 11 }, callback: function(v) { return '\u20B9' + v.toLocaleString('en-IN'); } } },
                    x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11 } } }
                }
            }
        });
    }

    // Expense Breakdown Doughnut
    var ctx2 = document.getElementById('chart-expenses');
    if (ctx2) {
        var expLabels = Object.keys(d.expenses || {});
        var expValues = expLabels.map(function(k) { return d.expenses[k]; });
        var expColors = ['#6366f1', '#10b981', '#ef4444', '#f59e0b', '#8b5cf6', '#3b82f6', '#eab308', '#14b8a6', '#ec4899', '#06b6d4'];
        if (expLabels.length === 0) { expLabels = ['No Expenses']; expValues = [1]; expColors = ['#e2e8f0']; }
        _reportCharts.expenses = new Chart(ctx2, {
            type: 'doughnut',
            data: {
                labels: expLabels,
                datasets: [{
                    data: expValues,
                    backgroundColor: expColors.slice(0, expLabels.length),
                    borderWidth: 3,
                    borderColor: '#ffffff',
                    hoverBorderWidth: 0,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                cutout: '60%',
                plugins: {
                    title: { display: true, text: 'Expense Breakdown', font: { size: 15, weight: 'bold', family: 'Inter' }, padding: { bottom: 16 } },
                    legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 11 }, padding: 12, usePointStyle: true, pointStyleWidth: 8 } }
                }
            }
        });
    }

    // Profitability Waterfall (horizontal bar)
    var ctx3 = document.getElementById('chart-gp');
    if (ctx3) {
        _reportCharts.gp = new Chart(ctx3, {
            type: 'bar',
            data: {
                labels: ['Gross Profit', 'Operating Expenses', 'EBITDA', 'Tax', 'PAT'],
                datasets: [{
                    label: 'Amount',
                    data: [d.gross_profit || 0, d.total_opex || 0, d.ebitda || 0, d.tax || 0, d.pat || 0],
                    backgroundColor: [
                        'rgba(16, 185, 129, 0.85)',
                        'rgba(239, 68, 68, 0.85)',
                        'rgba(99, 102, 241, 0.85)',
                        'rgba(245, 158, 11, 0.85)',
                        'rgba(20, 184, 166, 0.85)'
                    ],
                    borderColor: [colors.green, colors.red, colors.indigo, colors.orange, colors.teal],
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Profitability Waterfall', font: { size: 15, weight: 'bold', family: 'Inter' }, padding: { bottom: 16 } },
                    legend: { display: false }
                },
                scales: {
                    x: { grid: { color: '#f1f5f9' }, ticks: { font: { family: 'Inter', size: 11 }, callback: function(v) { return '\u20B9' + v.toLocaleString('en-IN'); } } },
                    y: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11, weight: '500' } } }
                }
            }
        });
    }

    // Key Metrics Summary (bar)
    var ctx4 = document.getElementById('chart-sales');
    if (ctx4) {
        _reportCharts.sales = new Chart(ctx4, {
            type: 'bar',
            data: {
                labels: ['Total Sales', 'Total Orders', 'Units Sold', 'Boxes', 'GST Collected'],
                datasets: [{
                    label: 'Count / Amount',
                    data: [d.total_sales || 0, d.total_orders || 0, d.units || 0, d.order_boxes || 0, d.gst || 0],
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.85)',
                        'rgba(139, 92, 246, 0.85)',
                        'rgba(16, 185, 129, 0.85)',
                        'rgba(245, 158, 11, 0.85)',
                        'rgba(234, 179, 8, 0.85)'
                    ],
                    borderColor: [colors.blue, colors.purple, colors.green, colors.orange, colors.yellow],
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: { display: true, text: 'Key Metrics', font: { size: 15, weight: 'bold', family: 'Inter' }, padding: { bottom: 16 } },
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { font: { family: 'Inter', size: 11 } } },
                    x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11 } } }
                }
            }
        });
    }
}

// ---- FORM HANDLERS ----
$('f-product').addEventListener('submit', async function(e) {
    e.preventDefault();
    var id = $('f-pid').value;
    var data = {
        part_no: $('f-ppartno').value,
        name: $('f-pname').value,
        category: $('f-pcat').value,
        size: $('f-psize').value,
        load_rating: $('f-pload').value,
        hsn_code: $('f-phsn').value
    };
    if (id) {
        await api('/api/products/' + id, {method: 'PUT', body: JSON.stringify(data)});
        toast('Product updated!');
    } else {
        await api('/api/products', {method: 'POST', body: JSON.stringify(data)});
        toast('Product added!');
    }
    hideModal('m-product');
    $('f-product').reset();
    $('f-pid').value = '';
    loadProducts();
});

$('f-pricing').addEventListener('submit', async function(e) {
    e.preventDefault();
    var data = {
        raw_material_cost: parseFloat($('f-praw').value) || 0,
        mrp: parseFloat($('f-pmrp').value) || 0,
        labor_cost: 0,
        overhead_cost: 0,
        packing_cost: 0,
        profit_margin: 0,
        gst_rate: parseFloat($('f-pgst').value) || 18
    };
    await api('/api/products/' + $('f-prpid').value + '/pricing', {method: 'PUT', body: JSON.stringify(data)});
    hideModal('m-pricing');
    toast('Pricing updated!');
    loadProducts();
});

$('f-order').addEventListener('submit', async function(e) {
    e.preventDefault();
    var id = $('f-oid').value;
    var data = {
        sl_no: parseInt($('f-oslno').value) || 0,
        po_no: $('f-opo').value,
        po_date: $('f-opodate').value,
        customer_name: $('f-ocustname').value,
        billing_site: $('f-obilling').value,
        shipping_site: $('f-oshipping').value,
        no_of_boxes: parseInt($('f-oboxes').value) || 0,
        value_excl_gst_freight: parseFloat($('f-ovalue').value) || 0,
        invoice_no: $('f-oinvno').value,
        invoice_date: $('f-oinvdate').value,
        invoice_amount_excl_gst: parseFloat($('f-oinvamt').value) || 0,
        weight_kgs: parseFloat($('f-oweight').value) || 0,
        freight_rate_per_kg: parseFloat($('f-ofrate').value) || 0,
        transport_charges: parseFloat($('f-otcharges').value) || 0,
        invoice_amount: parseFloat($('f-oiamt').value) || 0,
        eway_bill_no: $('f-oeway').value,
        lr_no: $('f-olr').value,
        entry_date: $('f-oentrydate').value,
        credit_note_amount: parseFloat($('f-ocnamt').value) || 0,
        credit_note_no: $('f-ocnno').value,
        transporter: $('f-otransporter').value,
        transporter_no: $('f-otransno').value
    };
    if (id) {
        await api('/api/orders/' + id, {method: 'PUT', body: JSON.stringify(data)});
        toast('Order updated!');
    } else {
        await api('/api/orders', {method: 'POST', body: JSON.stringify(data)});
        toast('Order created!');
    }
    hideModal('m-order');
    $('f-order').reset();
    $('f-oid').value = '';
    loadOrders();
});

$('f-customer').addEventListener('submit', async function(e) {
    e.preventDefault();
    var id = $('f-cid').value;
    var data = {
        customer_id: $('f-ccustid').value,
        gstin: $('f-cgstin').value,
        billing_address: $('f-cbilladdr').value,
        shipping_address: $('f-cshipaddr').value,
        state: $('f-cstate').value,
        district: $('f-cdistrict').value,
        city: $('f-ccity').value,
        pincode: $('f-cpincode').value,
        contact_name: $('f-ccontactname').value,
        contact_number: $('f-ccontactnum').value,
        contact_email: $('f-ccontactemail').value,
        exec_code: $('f-cexeccode').value,
        exec_name: $('f-cexecname').value,
        exec_number: $('f-cexecnum').value,
        exec_email: $('f-cexecemail').value,
        blacklisted: $('f-cblacklisted').checked ? 1 : 0
    };
    if (id) {
        await api('/api/customers/' + id, {method: 'PUT', body: JSON.stringify(data)});
        toast('Customer updated!');
    } else {
        await api('/api/customers', {method: 'POST', body: JSON.stringify(data)});
        toast('Customer added!');
    }
    hideModal('m-customer');
    $('f-customer').reset();
    $('f-cid').value = '';
    loadCustomers();
});

$('f-transporter').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // Manual validation
    var requiredFields = [
        {id: 'f-ttransid', label: 'Transporter ID'},
        {id: 'f-tname', label: 'Name'},
        {id: 'f-tphone', label: 'Phone'},
        {id: 'f-temail', label: 'Email'},
        {id: 'f-taddr', label: 'Address'},
        {id: 'f-tstate', label: 'State'},
        {id: 'f-tdistrict', label: 'District'},
        {id: 'f-tcity', label: 'City'},
        {id: 'f-tpincode', label: 'Pincode'},
        {id: 'f-tgst', label: 'GST Number'},
        {id: 'f-tpan', label: 'PAN Number'},
        {id: 'f-tcontactperson', label: 'Contact Person'},
        {id: 'f-tcontactnum', label: 'Contact Number'}
    ];
    for (var i = 0; i < requiredFields.length; i++) {
        var el = $(requiredFields[i].id);
        if (!el.value || !el.value.trim()) {
            toast(requiredFields[i].label + ' is required', true);
            el.focus();
            return;
        }
    }
    
    var id = $('f-tid').value;
    var gstCert = '';
    var panCard = '';
    
    // Upload GST Certificate if selected
    var gstFile = $('f-tgstfile').files[0];
    if (gstFile) {
        try {
            var fd = new FormData();
            fd.append('file', gstFile);
            var res = await fetch('/api/upload', {method: 'POST', body: fd});
            var data = await res.json();
            gstCert = data.url || '';
        } catch(err) { console.error('GST upload failed:', err); }
    } else if (id) {
        var t = _transporters.find(function(x) { return x.id == id; });
        if (t) gstCert = t.gst_certificate || '';
    }
    
    // Upload PAN Card if selected
    var panFile = $('f-tpanfile').files[0];
    if (panFile) {
        try {
            var fd = new FormData();
            fd.append('file', panFile);
            var res = await fetch('/api/upload', {method: 'POST', body: fd});
            var data = await res.json();
            panCard = data.url || '';
        } catch(err) { console.error('PAN upload failed:', err); }
    } else if (id) {
        var t = _transporters.find(function(x) { return x.id == id; });
        if (t) panCard = t.pan_card || '';
    }
    
    var payload = {
        transporter_id: $('f-ttransid').value,
        name: $('f-tname').value,
        phone: $('f-tphone').value,
        email: $('f-temail').value,
        address: $('f-taddr').value,
        state: $('f-tstate').value,
        district: $('f-tdistrict').value,
        city: $('f-tcity').value,
        pincode: $('f-tpincode').value,
        gst_number: $('f-tgst').value,
        pan_number: $('f-tpan').value,
        gst_certificate: gstCert,
        pan_card: panCard,
        contact_person: $('f-tcontactperson').value,
        contact_number: $('f-tcontactnum').value,
        tracking_url_pattern: $('f-ttrackurl').value,
        blacklisted: $('f-tblacklisted').checked ? 1 : 0
    };
    try {
        if (id) {
            await api('/api/transporters/' + id, {method: 'PUT', body: JSON.stringify(payload)});
            toast('Transporter updated!');
        } else {
            await api('/api/transporters', {method: 'POST', body: JSON.stringify(payload)});
            toast('Transporter added!');
        }
        hideModal('m-transporter');
        $('f-transporter').reset();
        $('f-tid').value = '';
        loadTransporters();
    } catch(err) {
        toast('Error: ' + err.message, true);
    }
});

$('f-purchase-rate').addEventListener('submit', async function(e) {
    e.preventDefault();
    var id = $('f-prid').value;
    var payload = {
        product_id: parseInt($('f-prproduct').value),
        rate: parseFloat($('f-prrate').value) || 0,
        supplier: $('f-prsupplier').value,
        effective_date: $('f-predate').value
    };
    if (!payload.product_id) { toast('Product is required', true); return; }
    try {
        if (id) {
            await api('/api/purchase-rates/' + id, {method: 'PUT', body: JSON.stringify(payload)});
            toast('Purchase rate updated!');
        } else {
            await api('/api/purchase-rates', {method: 'POST', body: JSON.stringify(payload)});
            toast('Purchase rate added!');
        }
        hideModal('m-purchase-rate');
        $('f-purchase-rate').reset();
        $('f-prid').value = '';
        loadPurchaseRates();
    } catch(err) {
        toast('Error: ' + err.message, true);
    }
});

// WhatsApp Functions
function openWhatsApp(oid) {
    // Fetch order details and open modal
    api('/api/proforma-orders/' + oid).then(function(order) {
        $('f-waoid').value = oid;
        $('f-waorder').textContent = order.pi_no || 'Order #' + oid;
        $('f-wacustomer').textContent = order.customer_name || '';
        $('f-waphone').value = '';
        $('wa-status').style.display = 'none';
        showModal('m-whatsapp');
    }).catch(function(e) {
        toast('Error loading order: ' + e.message, true);
    });
}

function showWhatsAppModal(oid, orderNo, customer) {
    $('f-waoid').value = oid;
    $('f-waorder').textContent = orderNo;
    $('f-wacustomer').textContent = customer;
    $('f-waphone').value = '';
    $('wa-status').style.display = 'none';
    showModal('m-whatsapp');
}

// Test WhatsApp
async function testWhatsApp() {
    var phone = prompt("Enter your phone number to test WhatsApp:");
    if (!phone) return;
    toast("Sending test message...");
    try {
        var result = await api('/api/whatsapp/test', {
            method: 'POST',
            body: JSON.stringify({phone: phone})
        });
        if (result.success) {
            toast("Test message sent! Check your WhatsApp.");
        } else {
            toast("Failed: " + (result.error || "Unknown error"), true);
        }
    } catch(e) {
        toast("Error: " + e.message, true);
    }
}

async function sendWhatsAppPI() {
    var oid = $('f-waoid').value;
    var phone = $('f-waphone').value.trim();
    if (!phone || phone.length < 10) {
        toast('Enter a valid 10-digit phone number', true);
        return;
    }
    var statusEl = $('wa-status');
    statusEl.style.display = 'block';
    statusEl.style.background = '#dbeafe';
    statusEl.style.color = '#1e40af';
    statusEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending PI...';
    
    try {
        var result = await api('/api/whatsapp/send-pi/' + oid, {
            method: 'POST',
            body: JSON.stringify({phone: phone})
        });
        if (result.success) {
            statusEl.style.background = '#dcfce7';
            statusEl.style.color = '#166534';
            statusEl.innerHTML = '<i class="fas fa-check-circle"></i> PI sent successfully!';
            toast('WhatsApp PI sent!');
        } else {
            statusEl.style.background = '#fef2f2';
            statusEl.style.color = '#991b1b';
            statusEl.innerHTML = '<i class="fas fa-times-circle"></i> Failed: ' + (result.error || 'Unknown error');
        }
    } catch(e) {
        statusEl.style.background = '#fef2f2';
        statusEl.style.color = '#991b1b';
        statusEl.innerHTML = '<i class="fas fa-times-circle"></i> Error: ' + e.message;
    }
}

async function sendWhatsAppPO() {
    var oid = $('f-waoid').value;
    var phone = $('f-waphone').value.trim();
    if (!phone || phone.length < 10) {
        toast('Enter a valid 10-digit phone number', true);
        return;
    }
    var statusEl = $('wa-status');
    statusEl.style.display = 'block';
    statusEl.style.background = '#dbeafe';
    statusEl.style.color = '#1e40af';
    statusEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending PO...';
    
    try {
        var result = await api('/api/whatsapp/send-po/' + oid, {
            method: 'POST',
            body: JSON.stringify({phone: phone})
        });
        if (result.success) {
            statusEl.style.background = '#dcfce7';
            statusEl.style.color = '#166534';
            statusEl.innerHTML = '<i class="fas fa-check-circle"></i> PO sent successfully!';
            toast('WhatsApp PO sent!');
        } else {
            statusEl.style.background = '#fef2f2';
            statusEl.style.color = '#991b1b';
            statusEl.innerHTML = '<i class="fas fa-times-circle"></i> Failed: ' + (result.error || 'Unknown error');
        }
    } catch(e) {
        statusEl.style.background = '#fef2f2';
        statusEl.style.color = '#991b1b';
        statusEl.innerHTML = '<i class="fas fa-times-circle"></i> Error: ' + e.message;
    }
}

$('f-sale').addEventListener('submit', async function(e) {
    e.preventDefault();
    try {
        var id = $('f-slid') ? $('f-slid').value : '';
        var validItems = _saleItems.filter(function(item) { return item.product_id > 0; });
        if (validItems.length === 0) {
            toast('Add at least one product', true);
            return;
        }
        var data = {
            customer_id: parseInt($('f-slcust').value),
            product_id: validItems[0] ? validItems[0].product_id : 0,
            quantity: validItems.reduce(function(sum, i) { return sum + (i.quantity || 0); }, 0),
            unit_price: validItems[0] ? validItems[0].unit_price : 0,
            discount_percent: validItems[0] ? validItems[0].discount_percent : 0,
            freight_amount: parseFloat($('f-slfrt').value) || 0,
            invoice_value: parseFloat($('f-slinvval').value) || 0,
            payment_status: $('f-slstatus').value,
            payment_method: $('f-slmethod').value,
            transporter_name: $('f-sltransporter') ? $('f-sltransporter').value : '',
            lr_no: $('f-sllrno') ? $('f-sllrno').value : '',
            items: validItems
        };
        if (id) {
            var res = await api('/api/sales/' + id, {method: 'PUT', body: JSON.stringify(data)});
            hideModal('m-sale');
            $('f-sale').reset();
            $('f-slid').value = '';
            _saleItems = [];
            toast('Sale updated!');
        } else {
            var res = await api('/api/sales', {method: 'POST', body: JSON.stringify(data)});
            hideModal('m-sale');
            $('f-sale').reset();
            _saleItems = [];
            toast('Sale created! ' + res.invoice_no);
        }
        loadSales();
    } catch(err) {
        toast('Error saving sale: ' + (err.message || 'Unknown error'), true);
    }
});

$('f-expense').addEventListener('submit', async function(e) {
    e.preventDefault();
    var id = $('f-eid') ? $('f-eid').value : '';
    var data = {
        category: $('f-ecat').value,
        description: $('f-edesc').value,
        amount: parseFloat($('f-eamt').value),
        vendor: $('f-evendor').value,
        expense_date: $('f-edate').value || null
    };
    if (id) {
        await api('/api/expenses/' + id, {method: 'PUT', body: JSON.stringify(data)});
        hideModal('m-expense');
        $('f-expense').reset();
        $('f-eid').value = '';
        toast('Expense updated!');
    } else {
        await api('/api/expenses', {method: 'POST', body: JSON.stringify(data)});
        hideModal('m-expense');
        $('f-expense').reset();
        toast('Expense added!');
    }
    loadExpenses();
});

// ---- CSV IMPORT ----
async function importOrdersCSV(input) {
    var file = input.files[0];
    if (!file) return;
    var fd = new FormData();
    fd.append('file', file);
    toast('Importing orders...');
    try {
        var r = await fetch('/api/import/orders', {method: 'POST', body: fd});
        var d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Import failed');
        toast(d.message);
        loadAllOrders();
    } catch(e) { toast('Error: ' + e.message, true); }
    input.value = '';
}

async function importOrdersXLSX(input) {
    var file = input.files[0];
    if (!file) return;
    var fd = new FormData();
    fd.append('file', file);
    toast('Importing orders from XLSX...');
    try {
        var r = await fetch('/api/import/orders-xlsx', {method: 'POST', body: fd});
        var d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Import failed');
        toast(d.message);
        loadAllOrders();
    } catch(e) { toast('Error: ' + e.message, true); }
    input.value = '';
}

async function importSalesCSV(input) {
    var file = input.files[0];
    if (!file) return;
    var fd = new FormData();
    fd.append('file', file);
    toast('Importing sales...');
    try {
        var r = await fetch('/api/import/sales', {method: 'POST', body: fd});
        var d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Import failed');
        toast(d.message);
        loadSales();
    } catch(e) { toast('Error: ' + e.message, true); }
    input.value = '';
}

async function importSalesXLSX(input) {
    var file = input.files[0];
    if (!file) return;
    var fd = new FormData();
    fd.append('file', file);
    toast('Importing sales from XLSX...');
    try {
        var r = await fetch('/api/import/sales-xlsx', {method: 'POST', body: fd});
        var d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Import failed');
        toast(d.message);
        loadSales();
    } catch(e) { toast('Error: ' + e.message, true); }
    input.value = '';
}

async function importProductsCSV(input) {
    var file = input.files[0];
    if (!file) return;
    var fd = new FormData();
    fd.append('file', file);
    toast('Importing products...');
    try {
        var r = await fetch('/api/import/products', {method: 'POST', body: fd});
        var d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Import failed');
        toast(d.message);
        loadProducts();
    } catch(e) { toast('Error: ' + e.message, true); }
    input.value = '';
}

async function importCustomersCSV(input) {
    var file = input.files[0];
    if (!file) return;
    var fd = new FormData();
    fd.append('file', file);
    toast('Importing customers...');
    try {
        var r = await fetch('/api/import/customers', {method: 'POST', body: fd});
        var d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Import failed');
        toast(d.message);
        loadCustomers();
    } catch(e) { toast('Error: ' + e.message, true); }
    input.value = '';
}

async function importTransportersCSV(input) {
    var file = input.files[0];
    if (!file) return;
    var fd = new FormData();
    fd.append('file', file);
    toast('Importing transporters...');
    try {
        var r = await fetch('/api/import/transporters', {method: 'POST', body: fd});
        var d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Import failed');
        toast(d.message);
        loadTransporters();
    } catch(e) { toast('Error: ' + e.message, true); }
    input.value = '';
}

async function importExpensesCSV(input) {
    var file = input.files[0];
    if (!file) return;
    var fd = new FormData();
    fd.append('file', file);
    toast('Importing expenses...');
    try {
        var r = await fetch('/api/import/expenses', {method: 'POST', body: fd});
        var d = await r.json();
        if (!r.ok) throw new Error(d.detail || 'Import failed');
        toast(d.message);
        loadExpenses();
    } catch(e) { toast('Error: ' + e.message, true); }
    input.value = '';
}

// ---- PROFORMA ORDERS (PI/PO) ----
async function loadProformaOrders() {
    await loadAllOrders();
}

async function showProformaOrderModal() {
    _editingProformaId = null;
    _proformaItems = [];
    $('f-pooid').value = '';
    $('m-po-title').textContent = 'New PI/PO Order';
    try { await refreshDropdowns(); } catch(e) {}
    addProformaItem();
    $('m-proforma-order').classList.remove('hidden');
}

async function editProformaOrder(id) {
    var order = await api('/api/proforma-orders/' + id);
    _editingProformaId = id;
    // Load purchase rates for GP calculation
    try { _purchaseRates = await api('/api/purchase-rates'); } catch(e) { _purchaseRates = []; }
    $('f-pooid').value = id;
    $('f-pootype').value = order.order_type;
    $('f-poobilling').value = order.billing_site || '';
    onBillingSiteChange();
    $('f-pooshipping').value = order.shipping_site || '';
    $('f-poofreight').value = order.freight_amount || 0;
    $('f-poopaystatus').value = order.payment_status;
    $('f-poopaymethod').value = order.payment_method;
    $('f-poodelivery').value = order.delivery_days || 30;
    $('f-poonotes').value = order.notes || '';
    $('m-po-title').textContent = 'Edit Order - ' + order.pi_no;

    // Restore discount scheme state
    if ($('f-poodiscount')) $('f-poodiscount').checked = order.discount_scheme_applied === 1;

    await refreshDropdowns();
    $('f-poocust').value = order.customer_id;

    _proformaItems = order.items.map(function(item) {
        return {
            product_id: item.product_id,
            part_no: item.part_no,
            description: item.description,
            size: item.size,
            category: item.category,
            qty_boxes: item.qty_boxes,
            std_packaging: item.std_packaging,
            pieces_per_box: item.pieces_per_box,
            final_qty: item.final_qty,
            mrp: item.mrp,
            d1: item.d1, d2: item.d2, d3: item.d3, d4: item.d4, d5: item.d5,
            cd: item.cd,
            discount_percent: item.discount_percent,
            net_rate: item.net_rate,
            lock_hinge: item.lock_hinge,
            basic_amount: item.basic_amount
        };
    });
    renderProformaItems();
    calcProformaTotals();
    $('m-proforma-order').classList.remove('hidden');
}

async function viewProformaOrder(id) {
    var order = await api('/api/proforma-orders/' + id);
    _editingProformaId = id;
    // Load purchase rates for GP calculation
    try { _purchaseRates = await api('/api/purchase-rates'); } catch(e) { _purchaseRates = []; }
    $('f-pooid').value = id;
    $('f-pootype').value = order.order_type;
    $('f-poobilling').value = order.billing_site || '';
    onBillingSiteChange();
    $('f-pooshipping').value = order.shipping_site || '';
    $('f-poofreight').value = order.freight_amount || 0;
    $('f-poopaystatus').value = order.payment_status;
    $('f-poopaymethod').value = order.payment_method;
    $('f-poodelivery').value = order.delivery_days || 30;
    $('f-poonotes').value = order.notes || '';
    $('m-po-title').textContent = 'View Order - ' + order.pi_no;

    // Restore discount scheme state
    if ($('f-poodiscount')) $('f-poodiscount').checked = order.discount_scheme_applied === 1;

    await refreshDropdowns();
    $('f-poocust').value = order.customer_id;

    _proformaItems = order.items.map(function(item) {
        return {
            product_id: item.product_id,
            part_no: item.part_no,
            description: item.description,
            size: item.size,
            category: item.category,
            qty_boxes: item.qty_boxes,
            std_packaging: item.std_packaging,
            pieces_per_box: item.pieces_per_box,
            final_qty: item.final_qty,
            mrp: item.mrp,
            d1: item.d1, d2: item.d2, d3: item.d3, d4: item.d4, d5: item.d5,
            cd: item.cd,
            discount_percent: item.discount_percent,
            net_rate: item.net_rate,
            lock_hinge: item.lock_hinge,
            basic_amount: item.basic_amount
        };
    });
    renderProformaItems();
    calcProformaTotals();
    $('m-proforma-order').classList.remove('hidden');
}

async function deleteProformaOrder(id) {
    if (!confirm('Delete this order?')) return;
    await api('/api/proforma-orders/' + id, {method: 'DELETE'});
    toast('Order deleted');
    loadAllOrders();
}

function addProformaItem() {
    _proformaItems.push({
        product_id: 0, part_no: '', description: '', size: '', category: '',
        qty_boxes: 1, std_packaging: 1, pieces_per_box: 1, final_qty: 0,
        mrp: 0, d1: 0, d2: 0, d3: 0, d4: 0, d5: 0, cd: 0,
        discount_percent: 0, net_rate: 0, lock_hinge: 0, basic_amount: 0
    });
    renderProformaItems();
}

function removeProformaItem(idx) {
    _proformaItems.splice(idx, 1);
    renderProformaItems();
    calcProformaTotals();
}

function renderProformaItems() {
    var h = '';
    _proformaItems.forEach(function(item, idx) {
        var prodOpts = '<option value="0">-- Select --</option>';
        _products.forEach(function(p) {
            prodOpts += '<option value="' + p.id + '"' + (item.product_id == p.id ? ' selected' : '') + '>' + escapeHtml(p.part_no) + ' - ' + escapeHtml(p.name) + ' (' + escapeHtml(p.size || 'N/A') + ') [' + escapeHtml(p.load_rating || '5 Ton') + ']</option>';
        });
        h += '<tr class="border-b">';
        h += '<td style="padding:4px;width:30px;">' + (idx + 1) + '</td>';
        h += '<td style="padding:4px;width:180px;"><select style="width:100%;border:1px solid #d1d5db;border-radius:4px;padding:2px;font-size:12px;" onchange="onProformaProductChange(' + idx + ', this.value)">' + prodOpts + '</select></td>';
        h += '<td style="padding:4px;width:70px;background:#f9fafb;font-size:12px;">' + escapeHtml(item.category || '') + '</td>';
        h += '<td style="padding:4px;width:60px;background:#f9fafb;font-size:12px;">' + escapeHtml(item.size || '') + '</td>';
        h += '<td style="padding:4px;width:80px;background:#f9fafb;font-size:12px;">' + escapeHtml(item.part_no || '') + '</td>';
        h += '<td style="padding:4px;width:50px;"><input type="number" min="0" value="' + (item.qty_boxes || '') + '" style="width:100%;border:1px solid #d1d5db;border-radius:4px;padding:2px;font-size:12px;text-align:center;" onchange="updateProformaItem(' + idx + ', \'qty_boxes\', Math.max(0,parseInt(this.value)||0)); calcProformaItemQty(' + idx + '); renderProformaItems(); calcProformaTotals()"></td>';
        h += '<td style="padding:4px;width:55px;background:#f9fafb;text-align:center;font-size:12px;">Boxes</td>';
        h += '<td style="padding:4px;width:65px;background:#f9fafb;text-align:center;font-size:12px;font-weight:bold;">' + (item.std_packaging || '') + '</td>';
        h += '<td style="padding:4px;width:50px;background:#f9fafb;text-align:center;font-size:12px;font-weight:bold;">' + (item.final_qty || 0) + '</td>';
        h += '<td style="padding:4px;width:55px;background:#f9fafb;text-align:center;font-size:12px;">Pieces</td>';
        h += '<td style="padding:4px;width:75px;background:#f9fafb;text-align:right;font-size:12px;">' + fmt(item.mrp) + '</td>';
        h += '<td style="padding:4px;width:40px;"><input type="number" min="0" max="100" step="0.01" value="' + (item.d1 || '') + '" style="width:100%;border:1px solid #d1d5db;border-radius:4px;padding:2px;font-size:12px;text-align:center;" onchange="updateProformaItem(' + idx + ', \'d1\', Math.max(0,Math.min(100,parseFloat(this.value)||0))); calcProformaItemNetRate(' + idx + '); calcProformaTotals()"></td>';
        h += '<td style="padding:4px;width:40px;"><input type="number" min="0" max="100" step="0.01" value="' + (item.d2 || '') + '" style="width:100%;border:1px solid #d1d5db;border-radius:4px;padding:2px;font-size:12px;text-align:center;" onchange="updateProformaItem(' + idx + ', \'d2\', Math.max(0,Math.min(100,parseFloat(this.value)||0))); calcProformaItemNetRate(' + idx + '); calcProformaTotals()"></td>';
        h += '<td style="padding:4px;width:40px;"><input type="number" min="0" max="100" step="0.01" value="' + (item.d3 || '') + '" style="width:100%;border:1px solid #d1d5db;border-radius:4px;padding:2px;font-size:12px;text-align:center;" onchange="updateProformaItem(' + idx + ', \'d3\', Math.max(0,Math.min(100,parseFloat(this.value)||0))); calcProformaItemNetRate(' + idx + '); calcProformaTotals()"></td>';
        h += '<td style="padding:4px;width:40px;"><input type="number" min="0" max="100" step="0.01" value="' + (item.d4 || '') + '" style="width:100%;border:1px solid #d1d5db;border-radius:4px;padding:2px;font-size:12px;text-align:center;" onchange="updateProformaItem(' + idx + ', \'d4\', Math.max(0,Math.min(100,parseFloat(this.value)||0))); calcProformaItemNetRate(' + idx + '); calcProformaTotals()"></td>';
        h += '<td style="padding:4px;width:40px;"><input type="number" min="0" max="100" step="0.01" value="' + (item.d5 || '') + '" style="width:100%;border:1px solid #d1d5db;border-radius:4px;padding:2px;font-size:12px;text-align:center;" onchange="updateProformaItem(' + idx + ', \'d5\', Math.max(0,Math.min(100,parseFloat(this.value)||0))); calcProformaItemNetRate(' + idx + '); calcProformaTotals()"></td>';
        h += '<td style="padding:4px;width:40px;"><input type="number" min="0" max="100" step="0.01" value="' + (item.cd || '') + '" style="width:100%;border:1px solid #d1d5db;border-radius:4px;padding:2px;font-size:12px;text-align:center;" onchange="updateProformaItem(' + idx + ', \'cd\', Math.max(0,Math.min(100,parseFloat(this.value)||0))); calcProformaItemNetRate(' + idx + '); calcProformaTotals()"></td>';
        h += '<td style="padding:4px;width:80px;background:#f9fafb;font-weight:bold;text-align:right;font-size:12px;">' + fmt(item.net_rate) + '</td>';
        h += '<td style="padding:4px;width:55px;"><input type="number" min="0" value="' + (item.lock_hinge || '') + '" style="width:100%;border:1px solid #d1d5db;border-radius:4px;padding:2px;font-size:12px;text-align:center;" onchange="updateProformaItem(' + idx + ', \'lock_hinge\', Math.max(0,parseInt(this.value)||0)); calcProformaItemAmount(' + idx + '); calcProformaTotals()"></td>';
        h += '<td style="padding:4px;width:90px;background:#f9fafb;font-weight:bold;text-align:right;color:#16a34a;font-size:12px;">' + fmt(item.basic_amount) + '</td>';
        h += '<td style="padding:4px;width:35px;text-align:center;"><button type="button" onclick="removeProformaItem(' + idx + ')" style="color:#ef4444;border:none;background:none;cursor:pointer;font-size:14px;"><i class="fas fa-times"></i></button></td>';
        h += '</tr>';
    });
    $('po-items-body').innerHTML = h;
}

function updateProformaItem(idx, field, value) {
    _proformaItems[idx][field] = value;
}

async function onProformaProductChange(idx, pid) {
    if (!pid || pid == 0) return;
    try {
        var details = await api('/api/products/' + pid + '/details');
        _proformaItems[idx].product_id = details.id;
        _proformaItems[idx].part_no = details.part_no || '';
        _proformaItems[idx].description = details.name;
        _proformaItems[idx].size = details.size;
        _proformaItems[idx].category = details.category;
        _proformaItems[idx].mrp = details.mrp;
        _proformaItems[idx].std_packaging = details.std_packaging;
        _proformaItems[idx].pieces_per_box = details.pieces_per_box;
        calcProformaItemQty(idx);
        calcProformaItemNetRate(idx);
        calcProformaItemAmount(idx);
        renderProformaItems();
        calcProformaTotals();
    } catch(e) {
        console.error('Error fetching product details:', e);
    }
}

function calcProformaItemQty(idx) {
    var item = _proformaItems[idx];
    var ppb = item.std_packaging || item.pieces_per_box || 1;
    item.final_qty = (item.qty_boxes || 0) * ppb;
}

function calcProformaItemNetRate(idx) {
    var item = _proformaItems[idx];
    var net = item.mrp;
    net = net * (1 - (item.d1 || 0) / 100);
    net = net * (1 - (item.d2 || 0) / 100);
    net = net * (1 - (item.d3 || 0) / 100);
    net = net * (1 - (item.d4 || 0) / 100);
    net = net * (1 - (item.d5 || 0) / 100);
    net = net * (1 - (item.cd || 0) / 100);
    item.net_rate = Math.round(net * 100) / 100;
    item.discount_percent = item.mrp > 0 ? Math.round((1 - item.net_rate / item.mrp) * 10000) / 100 : 0;
    calcProformaItemAmount(idx);
}

function calcProformaItemAmount(idx) {
    var item = _proformaItems[idx];
    item.basic_amount = item.final_qty * item.net_rate;
}

function calcProformaTotals() {
    var totalQty = 0;
    var totalAmount = 0;
    _proformaItems.forEach(function(item) {
        totalQty += item.final_qty || 0;
        totalAmount += item.basic_amount || 0;
    });
    var freight = parseFloat($('f-poofreight').value) || 0;
    
    // Calculate discount scheme
    var discountApplied = $('f-poodiscount') && $('f-poodiscount').checked;
    var discountAmount = 0;
    var additionalDiscount = 0;
    var slabInfo = '';
    
    if (discountApplied && totalAmount >= 50100) {
        var slabs = [
            {min: 50100, max: 75000, additional: 2.50, info: '\u20B950,100 to \u20B975,000'},
            {min: 75100, max: 100000, additional: 5.00, info: '\u20B975,100 to \u20B91,00,000'},
            {min: 100001, max: 200000, additional: 7.00, info: '\u20B91,01,000 to \u20B92,00,000'},
            {min: 200001, max: Infinity, additional: 9.00, info: '\u20B92,00,000 & Above'}
        ];
        for (var i = 0; i < slabs.length; i++) {
            if (totalAmount >= slabs[i].min && totalAmount <= slabs[i].max) {
                additionalDiscount = slabs[i].additional;
                slabInfo = slabs[i].info;
                break;
            }
        }
        var totalDiscount = 54 + additionalDiscount;
        discountAmount = totalAmount * totalDiscount / 100;
    }
    
    var afterDiscount = totalAmount - discountAmount;
    var gst = afterDiscount * 0.18;
    var grandTotal = afterDiscount + gst + freight;

    $('po-total-qty').textContent = totalQty;
    $('po-total-amount').textContent = fmt(totalAmount);
    $('pov-subtotal').textContent = fmt(totalAmount);
    
    // Update discount display
    if ($('discount-row')) $('discount-row').style.display = discountAmount > 0 ? 'block' : 'none';
    if ($('pov-additional-discount')) $('pov-additional-discount').textContent = additionalDiscount;
    if ($('pov-discount-amount')) $('pov-discount-amount').textContent = '-' + fmt(discountAmount);
    if ($('pov-slab-info')) $('pov-slab-info').textContent = slabInfo || '-';
    
    $('pov-gst').textContent = fmt(gst);
    $('pov-freight').textContent = fmt(freight);
    $('pov-total').textContent = fmt(grandTotal);

    // Calculate GP from purchase rates
    var purchaseTotal = 0;
    _proformaItems.forEach(function(item) {
        if (item.product_id && item.final_qty) {
            var pr = _purchaseRates.find(function(r) { return r.product_id == item.product_id; });
            if (pr) {
                purchaseTotal += item.final_qty * pr.rate;
            }
        }
    });
    var gp = afterDiscount - purchaseTotal - freight;
    var gpPercent = afterDiscount > 0 ? (gp / afterDiscount * 100) : 0;
    var np = gp - gst;

    $('pov-purchase-total').textContent = fmt(purchaseTotal);
    $('pov-transport-cost').textContent = fmt(freight);
    $('pov-gp').textContent = fmt(gp);
    $('pov-gp-percent').textContent = gpPercent.toFixed(1) + '%';
    $('pov-np').textContent = fmt(np);
}

function onDiscountSchemeChange() {
    calcProformaTotals();
}

$('f-proforma-order').addEventListener('submit', async function(e) {
    e.preventDefault();
    var data = {
        customer_id: parseInt($('f-poocust').value),
        billing_site: $('f-poobilling').value,
        shipping_site: $('f-pooshipping').value,
        freight_amount: parseFloat($('f-poofreight').value) || 0,
        payment_status: $('f-poopaystatus').value,
        payment_method: $('f-poopaymethod').value,
        delivery_days: parseInt($('f-poodelivery').value) || 30,
        notes: $('f-poonotes').value,
        order_type: $('f-pootype').value,
        discount_scheme_applied: $('f-poodiscount') && $('f-poodiscount').checked ? 1 : 0,
        items: _proformaItems.filter(function(item) { return item.product_id > 0; })
    };
    if (data.items.length === 0) {
        toast('Please add at least one item', true);
        return;
    }
    try {
        var id = $('f-pooid').value;
        if (id) {
            await api('/api/proforma-orders/' + id, {method: 'PUT', body: JSON.stringify(data)});
            toast('Order updated!');
        } else {
            var res = await api('/api/proforma-orders', {method: 'POST', body: JSON.stringify(data)});
            toast('Order created! ' + res.pi_no);
        }
        hideModal('m-proforma-order');
        $('f-proforma-order').reset();
        _editingProformaId = null;
        _proformaItems = [];
        loadAllOrders();
    } catch(e) {
        toast('Error: ' + e.message, true);
    }
});

function generateProformaPDF() {
    var orderType = $('f-pootype').value;
    var customerName = $('f-poocust').options[$('f-poocust').selectedIndex].text;
    var piNo = $('f-pooid').value ? 'RFC/' + new Date().toISOString().slice(0,7).replace('-','') + '-' + $('f-pooid').value.padStart(3,'0') : 'NEW';
    var piDate = new Date().toLocaleDateString('en-IN', {day:'2-digit', month:'short', year:'numeric'});
    var billingSite = $('f-poobilling').value;
    var shippingSite = $('f-pooshipping').value;

    var bs = _selectedBillingSite || {};
    var bsName = bs.name || 'Raksha Pipes Private Limited';
    var bsAddress = bs.address || '';
    var bsPhone = bs.phone || '';
    var bsEmail = bs.email || '';
    var bsWebsite = bs.website || 'www.rakshapipes.com';
    var bsGstin = bs.gstin || '';
    var bsStateCode = bs.state_code || '';
    var bsPan = bs.pan || '';
    var bsShortName = bsName.replace('Private Limited', 'Pvt. Ltd.');

    var COMPANY_HEADER = '<div style="text-align:center;border-bottom:3px double #000;padding-bottom:10px;margin-bottom:10px;">';
    COMPANY_HEADER += '<h1 style="margin:0;font-size:22px;font-weight:bold;letter-spacing:1px;">' + escapeHtml(bsShortName) + '</h1>';
    COMPANY_HEADER += '<p style="margin:2px 0;font-size:11px;">' + escapeHtml(bsAddress) + '</p>';
    COMPANY_HEADER += '<table style="width:100%;font-size:10px;margin-top:6px;"><tr>';
    COMPANY_HEADER += '<td style="text-align:left;">Phone: +91 - ' + escapeHtml(bsPhone) + '</td>';
    COMPANY_HEADER += '<td style="text-align:center;">Email: ' + escapeHtml(bsEmail) + '</td>';
    COMPANY_HEADER += '<td style="text-align:right;">Website: ' + escapeHtml(bsWebsite) + '</td>';
    COMPANY_HEADER += '</tr><tr>';
    COMPANY_HEADER += '<td style="text-align:left;">State Code: ' + escapeHtml(bsStateCode) + '</td>';
    COMPANY_HEADER += '<td style="text-align:center;">GSTIN: ' + escapeHtml(bsGstin) + '</td>';
    COMPANY_HEADER += '<td style="text-align:right;">PAN No: ' + escapeHtml(bsPan) + '</td>';
    COMPANY_HEADER += '</tr></table></div>';

    var BANK_DETAILS = '<div style="margin-top:15px;font-size:11px;">';
    BANK_DETAILS += '<h4 style="margin:0 0 6px 0;font-size:13px;">Bank Details</h4>';
    BANK_DETAILS += '<table style="font-size:11px;">';
    BANK_DETAILS += '<tr><td style="font-weight:bold;padding-right:10px;">Name:</td><td>Raksha Pipes Pvt. Ltd.</td></tr>';
    BANK_DETAILS += '<tr><td style="font-weight:bold;padding-right:10px;">Account Number:</td><td>004705011678</td></tr>';
    BANK_DETAILS += '<tr><td style="font-weight:bold;padding-right:10px;">Bank Name:</td><td>ICICI Bank Ltd.</td></tr>';
    BANK_DETAILS += '<tr><td style="font-weight:bold;padding-right:10px;">Branch Name:</td><td>Koramangala, Bengaluru</td></tr>';
    BANK_DETAILS += '<tr><td style="font-weight:bold;padding-right:10px;">IFSC Code:</td><td>ICIC0000047</td></tr>';
    BANK_DETAILS += '</table></div>';

    var itemsHtml = '';
    var totalBox = 0;
    var totalPcs = 0;
    var totalBasic = 0;
    var totalLockHinge = 0;

    if (orderType === 'PO') {
        _proformaItems.forEach(function(item, idx) {
            if (item.product_id <= 0) return;
            var box = item.qty_boxes || 0;
            var pcs = item.final_qty || 0;
            var amt = item.basic_amount || 0;
            totalBox += box;
            totalPcs += pcs;
            totalBasic += amt;
            itemsHtml += '<tr>';
            itemsHtml += '<td style="padding:5px 8px;border:1px solid #ccc;font-size:10px;">' + escapeHtml(item.part_no || '') + '</td>';
            itemsHtml += '<td style="padding:5px 8px;border:1px solid #ccc;font-size:10px;">' + escapeHtml(item.description || '') + ' ' + escapeHtml(item.size || '') + '</td>';
            itemsHtml += '<td style="padding:5px 8px;border:1px solid #ccc;text-align:center;font-size:10px;">Box</td>';
            itemsHtml += '<td style="padding:5px 8px;border:1px solid #ccc;text-align:center;font-size:10px;">' + (item.std_packaging || 0) + '</td>';
            itemsHtml += '<td style="padding:5px 8px;border:1px solid #ccc;text-align:center;font-size:10px;">' + pcs + '</td>';
            itemsHtml += '<td style="padding:5px 8px;border:1px solid #ccc;text-align:right;font-size:10px;">&#8377;' + Number(item.mrp || 0).toLocaleString('en-IN') + '</td>';
            itemsHtml += '<td style="padding:5px 8px;border:1px solid #ccc;text-align:right;font-size:10px;">&#8377;' + Number(amt || 0).toLocaleString('en-IN') + '</td>';
            itemsHtml += '</tr>';
        });

        var gst = totalBasic * 0.18;
        var grandTotal = totalBasic + gst;

        var html = '<!DOCTYPE html><html><head><title>Purchase Order</title>';
        html += '<style>body{font-family:Arial,sans-serif;margin:15px;font-size:11px;color:#000;}';
        html += 'table{width:100%;border-collapse:collapse;}';
        html += '@page{size:A4;margin:10mm;}';
        html += '@media print{body{margin:5mm;}}</style></head><body>';

        html += COMPANY_HEADER;

        html += '<table style="width:100%;margin-bottom:6px;font-size:11px;">';
        html += '<tr>';
        html += '<td style="width:20%;font-weight:bold;">Anand No.:</td>';
        html += '<td style="width:15%;"></td>';
        html += '<td style="width:30%;text-align:center;font-size:16px;font-weight:bold;border-top:2px solid #000;border-bottom:2px solid #000;padding:4px;">PURCHASE ORDER</td>';
        html += '<td style="width:15%;text-align:right;font-weight:bold;">PO No:</td>';
        html += '<td style="width:20%;text-align:right;">' + piNo + '</td>';
        html += '</tr>';
        html += '<tr>';
        html += '<td style="font-weight:bold;">PO Date:</td>';
        html += '<td>' + piDate + '</td>';
        html += '<td></td>';
        html += '<td style="text-align:right;font-weight:bold;">Amd No.:</td>';
        html += '<td></td>';
        html += '</tr></table>';

        html += '<table style="width:100%;border:1px solid #ccc;margin-top:8px;">';
        html += '<thead><tr style="background:#f0f0f0;">';
        html += '<th style="padding:6px;border:1px solid #ccc;text-align:left;font-size:10px;width:18%;">Part No</th>';
        html += '<th style="padding:6px;border:1px solid #ccc;text-align:left;font-size:10px;width:30%;">Description</th>';
        html += '<th style="padding:6px;border:1px solid #ccc;text-align:center;font-size:10px;width:8%;">Box</th>';
        html += '<th style="padding:6px;border:1px solid #ccc;text-align:center;font-size:10px;width:10%;">Pcs</th>';
        html += '<th style="padding:6px;border:1px solid #ccc;text-align:center;font-size:10px;width:10%;">Total Pcs</th>';
        html += '<th style="padding:6px;border:1px solid #ccc;text-align:right;font-size:10px;width:12%;">Rate</th>';
        html += '<th style="padding:6px;border:1px solid #ccc;text-align:right;font-size:10px;width:12%;">Amount</th>';
        html += '</tr></thead><tbody>' + itemsHtml + '</tbody>';
        html += '<tfoot>';
        html += '<tr style="font-weight:bold;background:#f9f9f9;">';
        html += '<td colspan="2" style="padding:6px 8px;border:1px solid #ccc;font-size:11px;">Total</td>';
        html += '<td style="padding:6px 8px;border:1px solid #ccc;text-align:center;font-size:11px;">' + totalBox + '</td>';
        html += '<td style="padding:6px 8px;border:1px solid #ccc;text-align:center;font-size:11px;">' + totalPcs + '</td>';
        html += '<td style="padding:6px 8px;border:1px solid #ccc;text-align:center;font-size:11px;">' + totalPcs + '</td>';
        html += '<td style="padding:6px 8px;border:1px solid #ccc;"></td>';
        html += '<td style="padding:6px 8px;border:1px solid #ccc;text-align:right;font-size:11px;">&#8377;' + totalBasic.toLocaleString('en-IN') + '</td>';
        html += '</tr>';
        html += '<tr style="font-weight:bold;">';
        html += '<td colspan="6" style="padding:6px 8px;border:1px solid #ccc;text-align:right;font-size:11px;">GST  18%</td>';
        html += '<td style="padding:6px 8px;border:1px solid #ccc;text-align:right;font-size:11px;">&#8377;' + gst.toLocaleString('en-IN') + '</td>';
        html += '</tr>';
        html += '<tr style="font-weight:bold;background:#f0f0f0;">';
        html += '<td colspan="6" style="padding:8px;border:1px solid #ccc;text-align:right;font-size:13px;">GRAND TOTAL</td>';
        html += '<td style="padding:8px;border:1px solid #ccc;text-align:right;font-size:13px;">&#8377;' + grandTotal.toLocaleString('en-IN') + '</td>';
        html += '</tr></tfoot></table>';

        html += '<table style="width:100%;margin-top:40px;font-size:11px;border:none;">';
        html += '<tr>';
        html += '<td style="width:33%;text-align:center;border-top:1px solid #000;padding-top:8px;">CREATED BY</td>';
        html += '<td style="width:33%;text-align:center;border-top:1px solid #000;padding-top:8px;">REVIEWED BY</td>';
        html += '<td style="width:33%;text-align:center;border-top:1px solid #000;padding-top:8px;">APPROVED BY</td>';
        html += '</tr></table>';

        html += '</body></html>';

    } else {
        // PI template with discount columns
        _proformaItems.forEach(function(item, idx) {
            if (item.product_id <= 0) return;
            var box = item.qty_boxes || 0;
            var pcs = item.final_qty || 0;
            var mrp = item.mrp || 0;
            var d1 = item.d1 || 0;
            var d2 = item.d2 || 0;
            var d3 = item.d3 || 0;
            var d4 = item.d4 || 0;
            var d5 = item.d5 || 0;
            var cd = item.cd || 0;
            var lock = item.lock_hinge || 0;
            var net = item.net_rate || 0;
            var amt = item.basic_amount || 0;
            totalBox += box;
            totalPcs += pcs;
            totalBasic += amt;
            totalLockHinge += lock;

            var base = mrp;
            var afterD1 = d1 ? base - (base * d1 / 100) : base;
            var afterD2 = d2 ? afterD1 - (afterD1 * d2 / 100) : afterD1;
            var afterD3 = d3 ? afterD2 - (afterD2 * d3 / 100) : afterD2;
            var afterD4 = d4 ? afterD3 - (afterD3 * d4 / 100) : afterD3;
            var afterD5 = d5 ? afterD4 - (afterD4 * d5 / 100) : afterD4;
            var afterCD = cd ? afterD5 - (afterD5 * cd / 100) : afterD5;

            itemsHtml += '<tr>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">' + (idx + 1) + '</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;font-size:9px;">' + escapeHtml(item.description || '') + ' (' + escapeHtml(item.size || '') + ')</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;font-size:9px;">' + escapeHtml(item.category || '') + '</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;font-size:9px;">' + escapeHtml(item.part_no || '') + '</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">FRP</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">Box</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">' + (item.std_packaging || 0) + '</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">' + pcs + '</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">Pieces</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;">' + mrp.toLocaleString('en-IN') + '</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">' + d1 + '%</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;">' + afterD1.toFixed(2) + '</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">' + d2 + '%</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;">' + afterD2.toFixed(2) + '</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">' + d3 + '%</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;">' + afterD3.toFixed(2) + '</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">' + d4 + '%</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;">' + afterD4.toFixed(2) + '</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">' + d5 + '%</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;">' + afterD5.toFixed(2) + '</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">' + cd + '%</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;font-weight:bold;">' + afterCD.toFixed(2) + '</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;">' + lock.toLocaleString('en-IN') + '</td>';
            itemsHtml += '<td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;font-weight:bold;">' + amt.toFixed(2) + '</td>';
            itemsHtml += '</tr>';
        });

        var packingCharges = 0;
        var subTotal = totalBasic + packingCharges;
        var gst = subTotal * 0.18;
        var totalValue = subTotal + gst;
        var tcsAmount = totalValue * 0.001;
        var finalValue = totalValue + tcsAmount;

        var html = '<!DOCTYPE html><html><head><title>Quotation cum Proforma Invoice</title>';
        html += '<style>body{font-family:Arial,sans-serif;margin:10px;font-size:10px;color:#000;}';
        html += 'table{width:100%;border-collapse:collapse;}';
        html += '@page{size:landscape A4;margin:8mm;}';
        html += '@media print{body{margin:5mm;}}</style></head><body>';

        html += COMPANY_HEADER;

        html += '<table style="width:100%;border:1px solid #ccc;font-size:9px;">';
        html += '<thead><tr style="background:#1a365d;color:white;">';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">SN</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Product Specification</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Size</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">ERP Part No</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Item Grp.</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Base UOM</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Std Packing</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Final Qty</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Final UOM</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Gen</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">D-1</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Net</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">D-2</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Net Rt</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">D-3</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Net Rt</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">D-4</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Net Rt</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">D-5</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Net Rt</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">CD</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Net Rt</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Lock &amp; Hings</th>';
        html += '<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Basic Amt</th>';
        html += '</tr></thead><tbody>' + itemsHtml + '</tbody>';
        html += '<tfoot>';
        html += '<tr style="font-weight:bold;background:#f0f0f0;">';
        html += '<td colspan="5" style="padding:5px 8px;border:1px solid #ccc;font-size:10px;">TOTAL</td>';
        html += '<td style="padding:5px 8px;border:1px solid #ccc;text-align:center;">Box</td>';
        html += '<td style="padding:5px 8px;border:1px solid #ccc;text-align:center;">' + totalBox + '</td>';
        html += '<td style="padding:5px 8px;border:1px solid #ccc;text-align:center;">' + totalPcs + '</td>';
        html += '<td style="padding:5px 8px;border:1px solid #ccc;text-align:center;">Pieces</td>';
        html += '<td colspan="11" style="padding:5px 8px;border:1px solid #ccc;"></td>';
        html += '<td style="padding:5px 8px;border:1px solid #ccc;text-align:right;">' + totalLockHinge.toLocaleString('en-IN') + '</td>';
        html += '<td style="padding:5px 8px;border:1px solid #ccc;text-align:right;">' + totalBasic.toFixed(2) + '</td>';
        html += '</tr></tfoot></table>';

        html += '<table style="width:100%;margin-top:10px;font-size:11px;">';
        html += '<tr>';
        html += '<td style="width:50%;vertical-align:top;">' + BANK_DETAILS + '</td>';
        html += '<td style="width:50%;vertical-align:top;text-align:right;">';
        html += '<table style="float:right;font-size:11px;">';
        html += '<tr><td style="padding:2px 8px;font-weight:bold;">BASIC VALUE</td><td style="text-align:right;padding:2px 8px;">&#8377;' + totalBasic.toLocaleString('en-IN') + '</td></tr>';
        html += '<tr><td style="padding:2px 8px;font-weight:bold;">ADD PACKING &amp; FORWARDING CHARGES</td><td style="text-align:right;padding:2px 8px;">&#8377;0</td></tr>';
        html += '<tr><td style="padding:2px 8px;font-weight:bold;">SUB TOTAL</td><td style="text-align:right;padding:2px 8px;">&#8377;' + subTotal.toLocaleString('en-IN') + '</td></tr>';
        html += '<tr><td style="padding:2px 8px;font-weight:bold;">GST @ 18.00%</td><td style="text-align:right;padding:2px 8px;">&#8377;' + gst.toLocaleString('en-IN') + '</td></tr>';
        html += '<tr><td style="padding:2px 8px;font-weight:bold;">TOTAL VALUE</td><td style="text-align:right;padding:2px 8px;">&#8377;' + totalValue.toLocaleString('en-IN') + '</td></tr>';
        html += '<tr><td style="padding:2px 8px;font-weight:bold;">TCS On Sales 0.1%</td><td style="text-align:right;padding:2px 8px;">&#8377;' + tcsAmount.toFixed(2) + '</td></tr>';
        html += '<tr><td style="padding:2px 8px;font-weight:bold;">ROUND OFF DIFF</td><td style="text-align:right;padding:2px 8px;">&#8377;0.00</td></tr>';
        html += '<tr style="font-size:14px;font-weight:bold;border-top:2px solid #000;">';
        html += '<td style="padding:6px 8px;">FINAL PI VALUE</td>';
        html += '<td style="text-align:right;padding:6px 8px;">&#8377;' + finalValue.toLocaleString('en-IN') + '</td></tr>';
        html += '</table></td></tr></table>';

        html += '<div style="margin-top:40px;text-align:right;font-size:11px;">';
        html += '<p>For <b>' + escapeHtml(bsShortName) + '</b></p>';
        html += '<p style="margin-top:30px;">Authorized Signatory</p></div>';

        html += '</body></html>';
    }

    var printWindow = window.open('', '_blank');
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.print();
}

// ---- INIT ----
// ---- INIT ----
try { $('today-date').textContent = new Date().toLocaleDateString('en-IN', {weekday:'long', year:'numeric', month:'long', day:'numeric'}); } catch(e) {}
try { $('f-edate').value = new Date().toISOString().split('T')[0]; } catch(e) {}
var _user = getUser();
if (!_user || !localStorage.getItem('access_token')) {
    showLogin();
} else {
    applyRoleUI();
    go('dashboard');
}

// ---- KEYBOARD SHORTCUTS ----
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        var modals = document.querySelectorAll('.modal-bg:not(.hidden)');
        modals.forEach(function(m) { m.classList.add('hidden'); });
    }
});

// ---- MODAL FOCUS MANAGEMENT ----
var origShowModal = showModal;
showModal = async function(id) {
    await origShowModal(id);
    var modal = $(id);
    if (modal) {
        var firstInput = modal.querySelector('input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled])');
        if (firstInput) setTimeout(function() { firstInput.focus(); }, 100);
    }
};

// ---- SETTINGS ----
async function loadSettings() {
    try {
        var s = await api('/api/settings');
        var h = '<div style="display:flex;flex-direction:column;gap:20px;">';
        h += '<div><label style="display:block;font-size:13px;font-weight:600;color:#374151;margin-bottom:6px;">Company Name</label><input type="text" id="s-company" value="' + escapeHtml(s.company_name || 'Raksha') + '" style="width:100%;border:1.5px solid #e2e8f0;border-radius:8px;padding:10px 14px;font-size:14px;font-family:\'Inter\',sans-serif;"></div>';
        h += '<div><label style="display:block;font-size:13px;font-weight:600;color:#374151;margin-bottom:6px;">Default GST Rate %</label><input type="number" min="0" max="100" step="0.01" id="s-gst" value="' + (s.default_gst_rate || '18') + '" style="width:100%;border:1.5px solid #e2e8f0;border-radius:8px;padding:10px 14px;font-size:14px;font-family:\'Inter\',sans-serif;"></div>';
        h += '<div><label style="display:block;font-size:13px;font-weight:600;color:#374151;margin-bottom:6px;">Invoice Prefix</label><input type="text" id="s-invprefix" value="' + escapeHtml(s.invoice_prefix || 'RFRP-') + '" style="width:100%;border:1.5px solid #e2e8f0;border-radius:8px;padding:10px 14px;font-size:14px;font-family:\'Inter\',sans-serif;"></div>';
        h += '<div><label style="display:block;font-size:13px;font-weight:600;color:#374151;margin-bottom:6px;">Tax Rate for P&L %</label><input type="number" min="0" max="100" step="0.01" id="s-taxrate" value="' + (s.tax_rate || '25') + '" style="width:100%;border:1.5px solid #e2e8f0;border-radius:8px;padding:10px 14px;font-size:14px;font-family:\'Inter\',sans-serif;"></div>';
        h += '<button onclick="saveSettings()" style="background:linear-gradient(135deg,#10b981,#059669);color:white;padding:10px 28px;border-radius:8px;font-weight:700;font-size:14px;cursor:pointer;box-shadow:0 2px 8px rgba(16,185,129,0.3);transition:all 0.15s;border:none;margin-top:12px;" onmouseover="this.style.transform=\'translateY(-1px)\';this.style.boxShadow=\'0 4px 16px rgba(16,185,129,0.4)\'" onmouseout="this.style.transform=\'translateY(0)\';this.style.boxShadow=\'0 2px 8px rgba(16,185,129,0.3)\'">Save Settings</button>';
        h += '</div>';
        if (hasPermission('users', 'view')) {
            h += '<div style="margin-top:32px;border-top:2px solid #f1f5f9;padding-top:24px;">';
            h += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;"><h3 style="font-weight:700;font-size:18px;">User Management</h3>';
            h += '<button onclick="showAddUserModal()" style="background:linear-gradient(135deg,#10b981,#059669);color:white;padding:8px 16px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;"><i class="fas fa-plus" style="margin-right:4px;"></i>Add User</button></div>';
            h += '<table class="w-full text-sm"><thead class="bg-gray-50"><tr>';
            h += '<th class="px-3 py-2 text-left">Username</th><th class="px-3 py-2 text-left">Full Name</th>';
            h += '<th class="px-3 py-2 text-left">Role</th><th class="px-3 py-2 text-left">Status</th>';
            h += '<th class="px-3 py-2 text-left">Last Login</th><th class="px-3 py-2 text-left">Actions</th>';
            h += '</tr></thead><tbody id="t-users"></tbody></table></div>';
        }
        h += '</div>';
        $('settings-body').innerHTML = h;
        if (hasPermission('users', 'view')) loadUsers();
    } catch(e) { console.error('Settings error:', e); }
}

async function loadUsers() {
    var users = await api('/api/users');
    var h = '';
    users.forEach(function(u) {
        var statusBadge = u.is_active ? '<span style="color:#16a34a;font-weight:600;">Active</span>' : '<span style="color:#dc2626;font-weight:600;">Disabled</span>';
        var roleColor = u.role==='admin'?'#fef2f2;color:#dc2626':u.role==='manager'?'#eff6ff;color:#2563eb':'#f0fdf4;color:#16a34a';
        h += '<tr style="border-bottom:1px solid #f1f5f9;">';
        h += '<td class="px-3 py-3">' + escapeHtml(u.username) + '</td>';
        h += '<td class="px-3 py-3">' + escapeHtml(u.full_name || '-') + '</td>';
        h += '<td class="px-3 py-3"><span style="font-size:11px;padding:2px 8px;border-radius:6px;font-weight:600;background:' + roleColor + ';">' + u.role.toUpperCase() + '</span></td>';
        h += '<td class="px-3 py-3">' + statusBadge + '</td>';
        h += '<td class="px-3 py-3" style="font-size:12px;color:#64748b;">' + (u.last_login ? new Date(u.last_login).toLocaleString() : 'Never') + '</td>';
        h += '<td class="px-3 py-3">';
        if (hasPermission('users', 'edit')) h += '<button onclick="editUser(' + u.id + ')" style="color:#4f46e5;font-size:12px;margin-right:8px;font-weight:600;">Edit</button>';
        if (hasPermission('users', 'delete') && u.username !== 'admin') h += '<button onclick="deleteUser(' + u.id + ')" style="color:#ef4444;font-size:12px;font-weight:600;">Delete</button>';
        h += '</td></tr>';
    });
    var tbody = document.getElementById('t-users');
    if (tbody) tbody.innerHTML = h || '<tr><td colspan="6" class="text-center py-4 text-gray-400">No users found</td></tr>';
}

function showAddUserModal() {
    $('f-uid').value = '';
    $('f-uusername').value = '';
    $('f-ufullname').value = '';
    $('f-uemail').value = '';
    $('f-upassword').value = '';
    $('f-urole').value = 'viewer';
    $('f-uisactive').checked = true;
    $('m-user-title').textContent = 'Add User';
    $('f-upw-hint').textContent = '(required)';
    $('f-uusername').disabled = false;
    showModal('m-user');
}

async function editUser(id) {
    var users = await api('/api/users');
    var u = users.find(function(x) { return x.id === id; });
    if (!u) return;
    $('f-uid').value = u.id;
    $('f-uusername').value = u.username;
    $('f-ufullname').value = u.full_name || '';
    $('f-uemail').value = u.email || '';
    $('f-upassword').value = '';
    $('f-urole').value = u.role;
    $('f-uisactive').checked = u.is_active;
    $('m-user-title').textContent = 'Edit User';
    $('f-upw-hint').textContent = '(leave blank to keep)';
    $('f-uusername').disabled = true;
    showModal('m-user');
}

async function deleteUser(id) {
    if (!confirm('Delete this user?')) return;
    await api('/api/users/' + id, {method: 'DELETE'});
    toast('User deleted');
    loadUsers();
}

async function saveSettings() {
    var data = {
        company_name: $('s-company').value,
        default_gst_rate: $('s-gst').value,
        invoice_prefix: $('s-invprefix').value,
        tax_rate: $('s-taxrate').value
    };
    await api('/api/settings', {method: 'PUT', body: JSON.stringify(data)});
    toast('Settings saved!');
}

document.getElementById('f-user').onsubmit = async function(e) {
    e.preventDefault();
    var id = $('f-uid').value;
    var data = {
        username: $('f-uusername').value,
        full_name: $('f-ufullname').value,
        email: $('f-uemail').value,
        role: $('f-urole').value,
        is_active: $('f-uisactive').checked ? 1 : 0,
    };
    var pw = $('f-upassword').value;
    if (pw) data.password = pw;
    try {
        if (id) {
            await api('/api/users/' + id, {method: 'PUT', body: JSON.stringify(data)});
            toast('User updated');
        } else {
            if (!pw) { alert('Password is required for new users'); return; }
            await api('/api/users', {method: 'POST', body: JSON.stringify(data)});
            toast('User created');
        }
        hideModal('m-user');
        loadUsers();
    } catch(err) {
        alert(err.message || 'Error saving user');
    }
};
