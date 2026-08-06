import requests

BASE='https://raksha-erp-deploy.onrender.com'
r=requests.post(f'{BASE}/api/auth/login',json={'username':'admin','password':'RS@2026'})
token=r.json()['access_token']
h={'Authorization':f'Bearer {token}'}

sales=requests.get(f'{BASE}/api/sales',headers=h).json()

# Check the new sale
s=next((x for x in sales if x.get('invoice_no')=='RFRP-00393'),None)
if s:
    print('New sale RFRP-00393:')
    print('  party_name:', repr(s['party_name']))
    print('  location:', repr(s['location']))
    print('  customer_id:', s['customer_id'])
else:
    print('Sale RFRP-00393 not found')

# Check old sales with Raksha Distributor
old=[x for x in sales if x.get('party_name')=='Raksha Distributor']
print(f'Old sales with Raksha Distributor: {len(old)}')
if old:
    o=old[0]
    inv=o.get('invoice_no','')
    cid=o.get('customer_id','')
    print(f'  First one: id={o["id"]}, invoice={inv}, customer_id={cid}')

# Check edit single-sale endpoint
if s:
    single=requests.get(f'{BASE}/api/sales/{s["id"]}',headers=h).json()
    print(f'Single fetch party_name: {repr(single.get("party_name",""))}')
