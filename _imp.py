import openpyxl, csv, io, requests

BASE = "https://raksha-erp-deploy.onrender.com"
XLSX = r"C:\Users\BusinessIntelligence\Desktop\Order & Sales (U).xlsx"
wb = openpyxl.load_workbook(XLSX, read_only=True)

# First delete existing transport expenses
r = requests.get(f"{BASE}/api/expenses")
expenses = r.json()
deleted = 0
for e in expenses:
    if e.get("category") == "Transport":
        requests.delete(f"{BASE}/api/expenses/{e['id']}")
        deleted += 1
print(f"Deleted {deleted} old transport expenses")

# Sales (2) - Freight = rate per kg, amount = rate * weight
ws = wb["Sales (2)"]
rows = list(ws.iter_rows(values_only=True))

buf = io.StringIO()
w = csv.writer(buf)
w.writerow(["Category", "Amount", "Description", "Vendor", "Date"])

total = 0
count = 0
for r in rows[1:]:
    vals = list(r) + [None]*9
    inv, date, party, loc, transporter, freight_rate, inv_val, weight, lr = vals[:9]
    
    try:
        rate = float(freight_rate) if freight_rate and str(freight_rate).strip() not in ("-", "", "None") else 0
    except (ValueError, TypeError):
        rate = 0
    try:
        wt = float(weight) if weight and str(weight).strip() not in ("-", "", "None") else 0
    except (ValueError, TypeError):
        wt = 0
    
    freight_amt = rate * wt
    if freight_amt <= 0:
        continue
    
    vendor = str(transporter).strip() if transporter and str(transporter).strip() not in ("-", "", "None") else ""
    inv_str = str(inv).strip() if inv and str(inv).strip() not in ("-", "", "None") else ""
    desc = f"Freight - {inv_str} ({party})" if inv_str else f"Freight - {party}"
    dt = ""
    if date and hasattr(date, "strftime"):
        dt = date.strftime("%Y-%m-%d")
    
    w.writerow(["Transport", round(freight_amt, 2), desc, vendor, dt])
    total += freight_amt
    count += 1

wb.close()

print(f"Prepared {count} freight expenses from Sales, total: {total:,.2f}")
csv_text = buf.getvalue()
files = {"file": ("expenses.csv", csv_text.encode("utf-8-sig"), "text/csv")}
r = requests.post(f"{BASE}/api/import/expenses", files=files, timeout=120)
print(f"[{r.status_code}] {r.text[:300]}")
