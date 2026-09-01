import requests
import json

login_url = "https://raksha-erp-deploy.onrender.com/api/auth/login"
r = requests.post(login_url, json={"username": "admin", "password": "RS@2026"}, timeout=30)
token = r.json().get("access_token", "")
headers = {"Authorization": f"Bearer {token}"}

base = "https://raksha-erp-deploy.onrender.com"

# Check OpenAPI docs
for doc_url in ["/docs", "/openapi.json", "/api/docs", "/redoc", "/api/openapi.json"]:
    try:
        rr = requests.get(f"{base}{doc_url}", headers=headers, timeout=15)
        if rr.status_code == 200:
            content = rr.text[:3000]
            print(f"=== {doc_url} (status={rr.status_code}) ===")
            print(content)
            print("...")
            print()
    except Exception as e:
        print(f"{doc_url}: ERROR {e}")
