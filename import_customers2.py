import openpyxl, csv, io, requests

BASE = "https://raksha-erp-deploy.onrender.com"

# First check what customers exist
r = requests.get(f"{BASE}/api/customers")
existing = r.json()
existing_ids = {c["customer_id"] for c in existing}
print(f"Existing customers: {len(existing_ids)}")

# Build customer list from Excel
wb = openpyxl.load_workbook(r"C:\Users\BusinessIntelligence\Desktop\Order & Sales (U).xlsx", read_only=True)
ws = wb["Customers"]
rows = list(ws.iter_rows(values_only=True))

customers = []
for r in rows[1:]:
    sl, sd_code, gstin, name, city, state, phone, exec_name, status = (list(r) + [None]*9)[:9]
    cust_id = str(sd_code).strip() if sd_code else ""
    if not cust_id:
        cust_id = str(gstin).strip() if gstin else ""
    if not cust_id:
        continue
    state_val = str(state).strip() if state and not str(state).startswith("=") else ""
    phone_str = str(int(phone)) if phone and isinstance(phone, (int, float)) else str(phone).strip() if phone else ""
    customers.append({
        "customer_id": cust_id,
        "name": str(name).strip() if name else "",
        "gstin": str(gstin).strip() if gstin else "",
        "city": str(city).strip() if city else "",
        "state": state_val,
        "contact_name": str(name).strip() if name else "",
        "contact_number": phone_str,
    })
wb.close()

# Split: new customers and existing (to update)
new_customers = [c for c in customers if c["customer_id"] not in existing_ids]
update_customers = [c for c in customers if c["customer_id"] in existing_ids]

print(f"New customers: {len(new_customers)}")
print(f"Existing to update: {len(update_customers)}")

# Import new customers as batch
if new_customers:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Customer ID", "Name", "GSTIN", "City", "State", "Contact Name", "Contact Number"])
    for c in new_customers:
        w.writerow([c["customer_id"], c["name"], c["gstin"], c["city"], c["state"], c["contact_name"], c["contact_number"]])
    
    files = {"file": ("customers.csv", buf.getvalue().encode("utf-8-sig"), "text/csv")}
    r = requests.post(f"{BASE}/api/import/customers", files=files, timeout=120)
    print(f"Import new: [{r.status_code}] {r.text[:300]}")

# Update existing customers via API
for c in update_customers:
    cid = c["customer_id"]
    # Find the id from existing
    match = [x for x in existing if x["customer_id"] == cid]
    if match:
        db_id = match[0]["id"]
        r = requests.put(f"{BASE}/api/customers/{db_id}", json=c, timeout=30)
        print(f"Update {cid}: [{r.status_code}]")

print("\nDone!")
