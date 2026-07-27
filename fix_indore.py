import urllib.request, json

BASE = "https://raksha-erp-deploy.onrender.com"

updates = [
    (213, 1665336.0),
    (220, 207406.0),
    (222, 198812.0),
    (227, 142363.0),
    (244, 877393.0),
]
delete_id = 202

# First, fetch current records to get full data for updates
req = urllib.request.Request(f"{BASE}/api/sales?limit=500")
resp = urllib.request.urlopen(req, timeout=30)
all_sales = json.loads(resp.read())
sales_map = {s["id"]: s for s in all_sales}

for sid, new_val in updates:
    s = sales_map.get(sid)
    if not s:
        print(f"SKIP: ID {sid} not found")
        continue
    payload = {
        "customer_id": s.get("customer_id") or 0,
        "product_id": s.get("product_id") or 0,
        "quantity": s.get("quantity") or 0,
        "unit_price": s.get("unit_price") or 0,
        "discount_percent": s.get("discount_percent") or 0,
        "freight_amount": s.get("freight_amount") or 0,
        "invoice_value": new_val,
        "payment_status": s.get("payment_status") or "Pending",
        "payment_method": s.get("payment_method") or "Cash",
        "notes": s.get("notes") or "",
        "transporter_name": s.get("transporter_name") or "",
        "lr_no": s.get("lr_no") or "",
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{BASE}/api/sales/{sid}", data=data, method="PUT")
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read())
        print(f"UPDATED ID={sid}: invoice_value={new_val} -> {result}")
    except Exception as e:
        print(f"ERROR updating ID={sid}: {e}")

# Delete Maniram record
try:
    req = urllib.request.Request(f"{BASE}/api/sales/{delete_id}", method="DELETE")
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read())
    print(f"DELETED ID={delete_id}: {result}")
except Exception as e:
    print(f"ERROR deleting ID={delete_id}: {e}")
