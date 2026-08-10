import requests

PERM_TOKEN = "EAIh7PXiG5U4BSC9DVTzhQAqwCA9oB2ZB4lB8OKYggcDqmBCBISoUWFpQtS97JgBFOGwgcgNB005tHuKedF8ORr3ccmEMDYoZCrDQPNYRD3l9yPAy6y4LngHZCZB2SjgneJj2i9oBzc6bonTVOUa45ZANFXXZBNLlFOPpcgr5hv2iS2ZCY88CubYhLK1L0KRGlRNagZDZD"
PHONE_ID = "1299086943278503"

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
