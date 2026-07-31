import requests
BASE = "https://raksha-erp-deploy.onrender.com"

# Get all sales
r = requests.get(f"{BASE}/api/sales")
sales = r.json()
print(f"Total sales: {len(sales)}")

# Check current statuses
pending_payment = [s for s in sales if s.get("payment_status") != "Paid"]
not_delivered = [s for s in sales if s.get("lr_tracking_status") != "Delivered"]
print(f"Not Paid: {len(pending_payment)}")
print(f"Not Delivered: {len(not_delivered)}")

# Update all sales: payment_status=Paid, lr_tracking_status=Delivered
updated = 0
errors = 0
for s in sales:
    sid = s["id"]
    payload = {
        "invoice_no": s.get("invoice_no", ""),
        "sale_date": s.get("sale_date"),
        "party_name": s.get("party_name", ""),
        "location": s.get("location", ""),
        "transporter_name": s.get("transporter_name", ""),
        "lr_no": s.get("lr_no", ""),
        "freight_amount": s.get("freight_amount", 0),
        "weight_kgs": s.get("weight_kgs", 0),
        "invoice_value": s.get("invoice_value", 0),
        "payment_status": "Paid",
        "payment_method": s.get("payment_method", "Cash"),
        "lr_tracking_status": "Delivered",
        "lr_tracking_url": s.get("lr_tracking_url", ""),
        "source_csv": s.get("source_csv", ""),
        "notes": s.get("notes", ""),
        "sales_person": s.get("sales_person", ""),
        "pg_fiber_invoice_no": s.get("pg_fiber_invoice_no", ""),
        "pg_fiber_invoice_value": s.get("pg_fiber_invoice_value", 0),
        "gp": s.get("gp", 0),
        "gp_percent": s.get("gp_percent", 0),
    }
    r2 = requests.put(f"{BASE}/api/sales/{sid}/lr-tracking", json=payload)
    if r2.status_code == 200:
        updated += 1
    else:
        errors += 1
        if errors <= 3:
            print(f"  Error sale {sid}: [{r2.status_code}] {r2.text[:150]}")

print(f"\nUpdated: {updated}, Errors: {errors}")

# Now set id=392 (latest Meerut) to In Transit
r3 = requests.get(f"{BASE}/api/sales/392")
sale392 = r3.json()
sale392["lr_tracking_status"] = "In Transit"
r4 = requests.put(f"{BASE}/api/sales/392/lr-tracking", json=sale392)
print(f"Set Meerut id=392 to In Transit: [{r4.status_code}] {r4.text[:100]}")

# Verify
r = requests.get(f"{BASE}/api/sales")
sales = r.json()
delivered = [s for s in sales if s.get("lr_tracking_status") == "Delivered"]
in_transit = [s for s in sales if s.get("lr_tracking_status") == "In Transit"]
paid = [s for s in sales if s.get("payment_status") == "Paid"]
print(f"\nVerification:")
print(f"  Paid: {len(paid)}/{len(sales)}")
print(f"  Delivered: {len(delivered)}/{len(sales)}")
print(f"  In Transit: {len(in_transit)}/{len(sales)}")
