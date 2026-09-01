import requests
import json

login_url = "https://raksha-erp-deploy.onrender.com/api/auth/login"
r = requests.post(login_url, json={"username": "admin", "password": "RS@2026"}, timeout=30)
token = r.json().get("access_token", "")
headers = {"Authorization": f"Bearer {token}"}
base = "https://raksha-erp-deploy.onrender.com"

# 1) Check product details endpoint
for pid in [1, 2, 3]:
    try:
        rr = requests.get(f"{base}/api/products/{pid}/details", headers=headers, timeout=15)
        print(f"=== Product {pid} details (status={rr.status_code}) ===")
        print(json.dumps(rr.json(), indent=2)[:2000])
        print()
    except Exception as e:
        print(f"Product {pid} details error: {e}")

# 2) Check product pricing endpoint
for pid in [1, 2, 3]:
    try:
        rr = requests.get(f"{base}/api/products/{pid}/pricing", headers=headers, timeout=15)
        print(f"=== Product {pid} pricing (status={rr.status_code}) ===")
        print(json.dumps(rr.json(), indent=2)[:2000])
        print()
    except Exception as e:
        print(f"Product {pid} pricing error: {e}")

# 3) Check purchase-rates endpoint
try:
    rr = requests.get(f"{base}/api/purchase-rates", headers=headers, timeout=15)
    print(f"=== Purchase rates (status={rr.status_code}) ===")
    data = rr.json()
    print(json.dumps(data[:3] if isinstance(data, list) else data, indent=2)[:3000])
    print()
except Exception as e:
    print(f"Purchase rates error: {e}")

# 4) Check dashboard for any stock info
try:
    rr = requests.get(f"{base}/api/dashboard", headers=headers, timeout=15)
    print(f"=== Dashboard (status={rr.status_code}) ===")
    print(json.dumps(rr.json(), indent=2)[:3000])
    print()
except Exception as e:
    print(f"Dashboard error: {e}")
