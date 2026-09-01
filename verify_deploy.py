import requests, re

BASE = "https://raksha-erp-deploy.onrender.com"

# 1. Check static/app.js content
print("=== STATIC APP.JS VERIFICATION ===")
r = requests.get(f"{BASE}/static/js/app.js", timeout=30)
js = r.text
print(f"Size: {len(js)} bytes")

# Key functions/features to verify
checks = [
    ("escapeHtml function", r"function\s+escapeHtml|const\s+escapeHtml|escapeHtml\s*=", js, 0),
    ("applyRoleUI function", r"function\s+applyRoleUI|applyRoleUI\s*\(", js, 0),
    ("deleteEntity helper", r"function\s+deleteEntity|deleteEntity\s*\(", js, 0),
    ("dedupEntity helper", r"function\s+dedupEntity|dedupEntity\s*\(", js, 0),
    ("importFile helper", r"function\s+importFile|importFile\s*\(", js, 0),
    ("token refresh in api()", r"refresh.*token|token.*refresh|refreshToken", js, re.IGNORECASE),
    ("XSS - onclick escape", r"escapeHtml.*onclick|onclick.*escapeHtml|onclick.*\\\\u0027|onclick.*'", js, 0),
    ("N+1 fix - batch load", r"batch|freight.summary|freight-summary", js, re.IGNORECASE),
    ("ORDER_STATUS_LABELS", r"ORDER_STATUS_LABELS|ORDER_STATUSES", js, 0),
    ("toast() not alert()", r"function\s+toast|toast\(", js, 0),
]

alert_count = len(re.findall(r'(?<!\w)alert\s*\(', js))
print(f"  alert() calls: {alert_count}")

for label, pattern, text, flags in checks:
    found = bool(re.search(pattern, text, flags))
    status = "YES" if found else "NO"
    print(f"  {label}: {status}")

# 2. Check static/style.css content
print("\n=== STATIC STYLE.CSS VERIFICATION ===")
r_css = requests.get(f"{BASE}/static/css/style.css", timeout=30)
css = r_css.text
print(f"Size: {len(css)} bytes")

css_checks = [
    ("Responsive @media queries", r"@media"),
    ("Mobile 480px", r"480px"),
    ("Tablet 768px", r"768px"),
    ("Desktop 1024px", r"1024px"),
    ("cursor:pointer (not cursor-pointer)", r"cursor\s*:\s*pointer"),
    ("ARIA attributes", r"aria-label|role="),
]

for label, pattern in css_checks:
    found = bool(re.search(pattern, css))
    status = "YES" if found else "NO"
    print(f"  {label}: {status}")

# 3. Check HTML for security headers and ARIA
print("\n=== HTML VERIFICATION ===")
r_html = requests.get(BASE, timeout=30)
html = r_html.text

html_checks = [
    ("Login overlay", r"login-overlay|id=.login"),
    ("User header bar", r"user-header|user-header-bar"),
    ("meta description", r'<meta.*name="description"'),
    ("noscript fallback", r"<noscript>"),
    ("ARIA nav", r'role="navigation"|aria-label.*nav'),
    ("Discount scheme", r"discount.scheme|Apply Discount"),
    ("Create a PI", r"Create a PI"),
    ("Order Status column", r"Order Status|order.status"),
    ("Sale items table", r"Add Item|sale.items"),
    ("Billing Site dropdown", r"Billing Site|billing.site"),
    ("Purchase Rates", r"Purchase Rates"),
    ("GP section", r"Gross Profit|GP"),
    ("Mobile viewport meta", r"viewport.*width=device-width"),
]

for label, pattern in html_checks:
    found = bool(re.search(pattern, html, re.IGNORECASE))
    status = "YES" if found else "NO"
    print(f"  {label}: {status}")

# 4. Security headers
print("\n=== SECURITY HEADERS ===")
for h in ['x-content-type-options', 'x-frame-options', 'x-xss-protection', 'strict-transport-security', 'content-security-policy', 'referrer-policy', 'permissions-policy']:
    val = r_html.headers.get(h, "MISSING")
    display = val[:80] if val != "MISSING" else "MISSING"
    print(f"  {h}: {display}")
