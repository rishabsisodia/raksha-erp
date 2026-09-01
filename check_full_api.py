import requests
import json

login_url = "https://raksha-erp-deploy.onrender.com/api/auth/login"
r = requests.post(login_url, json={"username": "admin", "password": "RS@2026"}, timeout=30)
token = r.json().get("access_token", "")
headers = {"Authorization": f"Bearer {token}"}

base = "https://raksha-erp-deploy.onrender.com"

# Get full OpenAPI spec
rr = requests.get(f"{base}/openapi.json", headers=headers, timeout=30)
spec = rr.json()

# Print all paths
print("=== ALL API PATHS ===")
for path in sorted(spec.get("paths", {}).keys()):
    methods = list(spec["paths"][path].keys())
    print(f"  {path} [{', '.join(methods)}]")

print()

# Print all schemas
print("=== ALL SCHEMAS ===")
for schema_name in sorted(spec.get("components", {}).get("schemas", {}).keys()):
    schema = spec["components"]["schemas"][schema_name]
    props = list(schema.get("properties", {}).keys())
    print(f"  {schema_name}: {props}")

# Also try db-info endpoint
print()
print("=== DB INFO ===")
try:
    rr2 = requests.get(f"{base}/api/db-info", headers=headers, timeout=15)
    print(f"Status: {rr2.status_code}")
    print(f"Body: {rr2.text[:5000]}")
except Exception as e:
    print(f"Error: {e}")
