import openpyxl, csv, io, requests

BASE = "https://raksha-erp-deploy.onrender.com"

# Check existing customers
r = requests.get(f"{BASE}/api/customers")
data = r.json()
print(f"Existing customers: {len(data)}")
for c in data[:5]:
    print(f"  {c.get('customer_id')} | {c.get('name','')} | {c.get('gstin','')}")

# Build CSV with proper upsert - one at a time
wb = openpyxl.load_workbook(r"C:\Users\BusinessIntelligence\Desktop\Order & Sales (U).xlsx", read_only=True)
ws = wb["Customers"]
rows = list(ws.iter_rows(values_only=True))

# Build list of customers
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

print(f"\nTotal to import: {len(customers)}")

# Upload as CSV batch (the import endpoint handles upsert)
buf = io.StringIO()
w = csv.writer(buf)
w.writerow(["Customer ID", "Name", "GSTIN", "City", "State", "Contact Name", "Contact Number"])
for c in customers:
    w.writerow([c["customer_id"], c["name"], c["gstin"], c["city"], c["state"], c["contact_name"], c["contact_number"]])

csv_text = buf.getvalue()
files = {"file": ("customers.csv", csv_text.encode("utf-8-sig"), "text/csv")}
r = requests.post(f"{BASE}/api/import/customers", files=files, timeout=120)
print(f"[{r.status_code}] {r.text[:500]}")
