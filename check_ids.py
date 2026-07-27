import urllib.request, json

BASE = "https://raksha-erp-deploy.onrender.com"
req = urllib.request.Request(f"{BASE}/api/sales?limit=500")
resp = urllib.request.urlopen(req, timeout=30)
all_sales = json.loads(resp.read())

for sid in [213, 220, 222, 227, 244]:
    s = next((x for x in all_sales if x["id"] == sid), None)
    if s:
        print(f"ID={sid}: customer_id={s.get('customer_id')}, product_id={s.get('product_id')}, invoice_value={s.get('invoice_value')}, total_amount={s.get('total_amount')}")
    else:
        print(f"ID={sid}: NOT FOUND")
