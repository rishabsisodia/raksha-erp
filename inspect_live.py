import requests
import re

BASE = "https://raksha-erp-deploy.onrender.com"

# 1. Check what app.js actually contains
print("=== APP.JS RAW CONTENT ===")
r = requests.get(f"{BASE}/js/app.js", timeout=30)
print(f"Status: {r.status_code}, Size: {len(r.text)}")
print(f"Content: {repr(r.text[:500])}")

# 2. Check app.js with cache buster
print("\n=== APP.JS WITH CACHE BUSTER ===")
r2 = requests.get(f"{BASE}/js/app.js?v=20260817v2", timeout=30)
print(f"Status: {r2.status_code}, Size: {len(r2.text)}")
print(f"Content: {repr(r2.text[:500])}")

# 3. Try other JS paths
print("\n=== JS FILE DISCOVERY ===")
for path in ["/js/app.js", "/static/js/app.js", "/app.js", "/static/app.js"]:
    try:
        r = requests.get(f"{BASE}{path}", timeout=10)
        print(f"  {path}: {r.status_code} ({len(r.text)} bytes)")
    except Exception as e:
        print(f"  {path}: ERROR {e}")

# 4. Check CSS paths
print("\n=== CSS FILE DISCOVERY ===")
for path in ["/css/style.css", "/static/css/style.css", "/style.css", "/static/style.css"]:
    try:
        r = requests.get(f"{BASE}{path}", timeout=10)
        print(f"  {path}: {r.status_code} ({len(r.text)} bytes)")
    except Exception as e:
        print(f"  {path}: ERROR {e}")

# 5. Check the HTML to see how JS/CSS are referenced
print("\n=== HTML SCRIPT/LINK TAGS ===")
r_html = requests.get(BASE, timeout=30)
scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)["\']', r_html.text)
links = re.findall(r'<link[^>]*href=["\']([^"\']+)["\']', r_html.text)
print("Scripts:", scripts)
print("Links:", links)

# 6. Check if JS/CSS are inline in the HTML
print("\n=== INLINE CONTENT CHECKS ===")
html = r_html.text
print(f"Total HTML size: {len(html)} bytes")
# Check for inline script blocks
inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Inline script blocks: {len(inline_scripts)}")
for i, s in enumerate(inline_scripts):
    print(f"  Script {i}: {len(s)} bytes, starts with: {repr(s[:80].strip())}")
# Check for inline style blocks
inline_styles = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
print(f"Inline style blocks: {len(inline_styles)}")
for i, s in enumerate(inline_styles):
    print(f"  Style {i}: {len(s)} bytes")

# 7. Check if the HTML itself contains all the JS (maybe it's all inline)
print(f"\n=== FULL HTML SIZE: {len(html)} bytes ===")
# Check for key JS functions in the HTML
for fn in ["escapeHtml", "applyRoleUI", "loadProducts", "loadSales", "calcSaleTotals", "generateProformaPDF", "dedupEntity", "deleteEntity"]:
    found = fn in html
    print(f"  {fn} in HTML: {found}")
