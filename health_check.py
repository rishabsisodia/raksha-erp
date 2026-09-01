import requests, json, re

BASE = "https://raksha-erp-deploy.onrender.com"

# 1. Check if site is up
print("=== SITE CHECK ===")
try:
    r = requests.get(BASE, timeout=30)
    print(f"Homepage: {r.status_code} ({len(r.text)} bytes)")
    if "app.js?v=" in r.text:
        v = re.search(r'app\.js\?v=([^"\']+)', r.text)
        print(f"app.js version: {v.group(1) if v else 'unknown'}")
    else:
        print("WARNING: No cache-busted app.js found")
except Exception as e:
    print(f"Homepage FAILED: {e}")

# 2. Login
print("\n=== LOGIN ===")
try:
    r = requests.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "RS@2026"}, timeout=30)
    print(f"Login: {r.status_code}")
    token = r.json().get("access_token", "")
    print(f"Token: {'OK' if token else 'MISSING'}")
except Exception as e:
    print(f"Login FAILED: {e}")
    token = ""

if not token:
    exit()

headers = {"Authorization": f"Bearer {token}"}

# 3. Core endpoints
print("\n=== CORE ENDPOINTS ===")
endpoints = [
    ("GET", "/api/products", "Products list"),
    ("GET", "/api/customers", "Customers list"),
    ("GET", "/api/sales?limit=5", "Sales list"),
    ("GET", "/api/proforma-orders", "Proforma orders"),
    ("GET", "/api/transporters", "Transporters"),
    ("GET", "/api/purchase-rates", "Purchase rates"),
    ("GET", "/api/settings", "Settings"),
    ("GET", "/api/users", "Users list"),
    ("GET", "/api/sales/freight-summary", "Freight summary"),
    ("GET", "/api/whatsapp/config", "WhatsApp config"),
    ("GET", "/health", "Health check"),
]
for method, path, label in endpoints:
    try:
        if method == "GET":
            r = requests.get(f"{BASE}{path}", headers=headers, timeout=30)
        else:
            r = requests.post(f"{BASE}{path}", headers=headers, timeout=30)
        status = "OK" if r.status_code == 200 else f"FAIL({r.status_code})"
        detail = ""
        if r.status_code == 200:
            try:
                d = r.json()
                if isinstance(d, list):
                    detail = f" ({len(d)} items)"
                elif isinstance(d, dict):
                    detail = f" ({len(d)} keys)"
            except:
                pass
        print(f"  {label}: {status}{detail}")
    except Exception as e:
        print(f"  {label}: ERROR ({e})")

# 4. Check if dedup was already run
print("\n=== DEDUP STATUS ===")
try:
    r = requests.get(f"{BASE}/api/products", headers=headers, timeout=30)
    prods = r.json()
    print(f"Products remaining: {len(prods)}")
    part_nos = [p.get('part_no','') for p in prods if p.get('part_no')]
    dupes = [pn for pn in part_nos if part_nos.count(pn) > 1]
    if dupes:
        print(f"Still has duplicates: {set(dupes)}")
    else:
        print("No duplicate part_nos found")
except Exception as e:
    print(f"Products check FAILED: {e}")
