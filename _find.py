import requests
BASE = "https://raksha-erp-deploy.onrender.com"
r = requests.get(f"{BASE}/api/sales")
sales = r.json()
print(f"Total sales: {len(sales)}")
meerut = [s for s in sales if "Meerut" in (s.get("location","") + s.get("party_name",""))]
print(f"Meerut sales: {len(meerut)}")
for s in meerut:
    print(f"  id={s['id']} inv={s.get('invoice_no','')} party={s.get('party_name','')} loc={s.get('location','')} date={s.get('sale_date','')}")
# Find latest Meerut by date or id
if meerut:
    latest = max(meerut, key=lambda x: x.get("sale_date") or "")
    print(f"\nLatest Meerut: id={latest['id']} inv={latest.get('invoice_no','')} date={latest.get('sale_date','')}")
