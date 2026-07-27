import urllib.request, json

req = urllib.request.Request('https://raksha-erp-deploy.onrender.com/api/sales?limit=500')
resp = urllib.request.urlopen(req, timeout=30)
data = json.loads(resp.read())
print(f"Total sales fetched: {len(data)}")

indore = [s for s in data if s.get('source_csv') == 'From Indore' or 'INDORE' in (s.get('invoice_no') or '').upper() or 'Indore' in (s.get('location') or '')]
print(f"INDORE records: {len(indore)}")

for s in indore:
    sid = s["id"]
    inv = s.get("invoice_no", "")
    party = s.get("party_name", "")
    loc = s.get("location", "")
    total = s.get("total_amount", 0)
    inv_val = s.get("invoice_value", 0)
    print(f"  ID={sid}, Invoice={inv}, Party={party}, Location={loc}, Total={total}, InvoiceValue={inv_val}")
