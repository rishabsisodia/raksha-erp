import requests
BASE = "https://raksha-erp-deploy.onrender.com"
for ep in ["products", "customers", "orders", "sales", "transporters", "expenses"]:
    r = requests.get(f"{BASE}/api/{ep}")
    d = r.json()
    print(f"{ep}: {len(d)} records")

r = requests.get(f"{BASE}/api/customers")
for c in r.json()[:5]:
    print(f"  {c['customer_id']} | {c.get('name','')} | {c.get('city','')} | {c.get('state','')} | exec={c.get('exec_name','')}")
