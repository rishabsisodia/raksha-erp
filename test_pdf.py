import requests
import os

PERM_TOKEN = os.environ.get('WHATSAPP_TOKEN', '')
PHONE_ID = os.environ.get('WHATSAPP_PHONE_ID', '')

url = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"
headers = {"Authorization": f"Bearer {PERM_TOKEN}", "Content-Type": "application/json"}
payload = {
    "messaging_product": "whatsapp",
    "to": "916366263535",
    "type": "document",
    "document": {
        "id": "2486233731850643",
        "filename": "PI_RFC2608-003.pdf"
    }
}
resp = requests.post(url, json=payload, headers=headers, timeout=30)
print(resp.status_code)
print(resp.json())
