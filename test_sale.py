import requests

BASE='https://raksha-erp-deploy.onrender.com'
r=requests.post(f'{BASE}/api/auth/login',json={'username':'admin','password':'RS@2026'})
token=r.json()['access_token']
h={'Authorization':f'Bearer {token}'}

# Check first 5 sales - their customer_id values
sales=requests.get(f'{BASE}/api/sales',headers=h).json()
for s in sales[:10]:
    inv=s.get('invoice_no','')
    cid=s.get('customer_id')
    party=s.get('party_name','')
    print(f'{inv}: customer_id={cid} (type={type(cid).__name__}), party_name={party}')
