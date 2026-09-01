import requests
import json

# Login
login_url = "https://raksha-erp-deploy.onrender.com/api/auth/login"
r = requests.post(login_url, json={"username": "admin", "password": "RS@2026"}, timeout=30)
token = r.json().get("access_token", "")
headers = {"Authorization": f"Bearer {token}"}

# Check product keys and stock data
r_products = requests.get("https://raksha-erp-deploy.onrender.com/api/products", headers=headers, timeout=30)
prods = r_products.json()
if prods:
    print("Product keys:", list(prods[0].keys()) if prods else "empty")
    for p in prods[:3]:
        pid = p.get("id")
        pno = p.get("part_no", "")
        stk = p.get("stock", "N/A")
        print(f"  id={pid}, part_no={pno}, stock={stk}")
else:
    print("No products returned")
