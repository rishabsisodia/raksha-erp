import urllib.request, json

BASE = "https://raksha-erp-deploy.onrender.com"

updates = [
    (213, 1665336.0),
    (220, 207406.0),
    (222, 198812.0),
    (227, 142363.0),
    (244, 877393.0),
]

for sid, new_val in updates:
    payload = json.dumps({"invoice_value": new_val, "total_amount": new_val}).encode()
    req = urllib.request.Request(f"{BASE}/api/sales/{sid}/invoice", data=payload, method="PATCH")
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        print(f"OK ID={sid}: invoice_value={new_val} -> {result}")
    except Exception as e:
        print(f"ERROR ID={sid}: {e}")
