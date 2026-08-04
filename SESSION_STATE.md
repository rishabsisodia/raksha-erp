# Raksha ERP - Session State

## What We're Building
Raksha ERP system for **Raksha Pipes Private Limited** (FRP products, manufacturing, sales, orders, expenses).

## Key Details
- **Company**: Raksha Pipes Private Limited (Pvt. Ltd. = short form for Private Limited)
- **Roles**: Admin (full + user mgmt), Manager (create/edit), Viewer (read-only)
- **Auth**: JWT (8hr access, 30day refresh), bcrypt hashing
- **Login**: `admin` / `RS@2026` (default credentials on Render)
- **GSTIN**: 23AACCV0019M1ZJ | **PAN**: AAVCR0941M | **State Code**: 23
- **Bank**: ICICI Bank Ltd., A/C 004705011678, IFSC ICIC0000047
- **16 Billing Sites** seeded from Excel (dynamic PO/PI headers)
- **Deployed at**: https://raksha-erp-deploy.onrender.com

## WhatsApp Integration (DONE)
- [x] **WhatsApp Cloud API Config**: Token, Phone ID, Business Account ID configured
- [x] **WhatsApp Send Endpoint**: `POST /api/whatsapp/send` — send text/image messages
- [x] **WhatsApp Send PI**: `POST /api/whatsapp/send-pi/{oid}` — send PI to customer
- [x] **WhatsApp Send PO**: `POST /api/whatsapp/send-po/{oid}` — send PO to supplier/group
- [x] **WhatsApp Config Check**: `GET /api/whatsapp/config` — verify setup
- [x] **Database Columns**: `whatsapp_status`, `status`, `po_no`, `po_date`, etc. on proforma_orders
- [x] **WhatsApp Button**: Green WhatsApp icon on each PI/PO order row
- [x] **WhatsApp Modal**: Enter phone number, send PI or PO with one click

## Completed Work
- [x] SSRF Fix: `/api/view-file` whitelists only Cloudinary URLs
- [x] Invoice Collision Fix: `func.max(id)` instead of `count()`
- [x] Order sl_no Race Fix: uses `func.max(Order.sl_no)`
- [x] update_pricing Fix: writes all 5 cost fields
- [x] Dependencies: `bcrypt>=4.1.0`, `PyJWT>=2.8.0`
- [x] Full Auth System: `get_current_user()`, `require_permission()`, all endpoints protected
- [x] Seed Data: bcrypt admin password, migrates from SHA-256, seeds 16 billing sites
- [x] `escapeHtml()` applied to ALL table rendering throughout `app.js`
- [x] Frontend Auth: Login overlay, user header bar, `api()` with Bearer token, `applyRoleUI()`
- [x] User Management: Settings page admin-only table, `m-user` modal, `f-user` form
- [x] Export Links: `downloadExport()` and `viewFileAuth()` send Bearer token
- [x] PO/PI PDF Templates: Company header, bank details, signature block — all "Raksha Pipes Pvt. Ltd."
- [x] Backend PDF: `_generate_po_html()` and `_generate_pi_html()` accept `billing_site` parameter
- [x] Frontend PDF: `generateProformaPDF()` uses `_selectedBillingSite`
- [x] Billing Site Dropdown: `f-poobilling` changed to `<select>`, `onBillingSiteChange()` updates `_selectedBillingSite`
- [x] Dedup Products: `POST /api/products/dedup` + "Clean Dups" button
- [x] Cache Busting: `app.js?v=20260801v1`
- [x] **Removed Terms & Conditions** from PO/PI PDFs: `COMPANY_TERMS = ""`
- [x] **PDF Auth Fix**: Removed auth from `/api/proforma-orders/{oid}/pdf` endpoint (read-only)
- [x] **Token Key Fix**: `downloadExport()` and `viewFileAuth()` now use `access_token` (matching login storage)
- [x] **New Models Added**: `PurchaseRate`, `TransporterQuote` in backend/main.py
- [x] **ProformaOrder Extended**: Added `po_no`, `po_date`, `purchase_total`, `transport_cost`, `gross_profit`, `net_profit`, `transporter_id`, `whatsapp_status`, `status` fields
- [x] **Purchase Rate CRUD**: `GET/POST/PUT/DELETE /api/purchase-rates` + bulk endpoint
- [x] **GP Calculation Endpoint**: `GET /api/proforma-orders/{oid}/gp`
- [x] **Transport Update Endpoint**: `PUT /api/proforma-orders/{oid}/transport`
- [x] **Purchase Rates UI Page**: Full CRUD + CSV import in frontend
- [x] **GP Display**: Shows Purchase Total, Transport Cost, GP, GP%, NP in order modal
- [x] **Button Rename**: Changed "+ New PI/PO" to "Create a PI"

## In Progress (Do This First)
1. **Add purchase rates UI page** — Create frontend page for managing purchase rate cards (CRUD + bulk upload) ✅ DONE
2. **Verify transporter UI** — Transporter management page already exists, verify it works with new fields ✅ VERIFIED
3. **Add GP display** — Show GP/NP in order details modal ✅ DONE
4. **Rename button** — Change "+ New PI/PO" to "Create a PI" in index.html ✅ DONE
5. **Frontend for order status** — Add status tracking (draft → confirmed → processing → shipped)
6. **Update SESSION_STATE.md** — Add commit hash after push

## Next Steps (After UI is done)
1. **WhatsApp Integration** — Using Meta WhatsApp Cloud API (user to provide credentials)
   - PI auto-send as PDF to Sales Manager/Executive
   - PO auto-send to WhatsApp Group in product table format
   - Transporter broadcast (address only, no party name)
2. **Discount Structure** — User to share tier details based on order value
3. **WhatsApp Message Formats** — User to share screenshots of PI/PO/broadcast formats

## What User Has Provided
1. Meta WhatsApp Cloud API credentials ✅
   - Phone Number ID: 1299086943278503
   - WhatsApp Business Account ID: 4397763287203081
   - Access Token: Configured
2. Discount structure (tiers by order value) — PENDING

## What User Will Provide
1. WhatsApp message format screenshots (PI, PO, transporter broadcast)
2. WhatsApp Group details for PO delivery
3. Discount structure tiers
4. Any additional business requirements

## Files Modified
- `backend/main.py` (~4300+ lines) — auth, bug fixes, endpoints, billing sites, PDF generation, purchase rates, GP calc, WhatsApp integration
- `frontend/js/app.js` (~2530+ lines) — auth, escapeHtml, user mgmt, PO/PI form/PDF, billing site dropdown, purchase rates UI, GP display
- `frontend/index.html` (~870+ lines) — full UI with login overlay, user header, modals, purchase rates page, GP section
- `requirements.txt` — fastapi, bcrypt, PyJWT, fpdf2, beautifulsoup4, requests

## How to Test
```bash
# Start server (local)
cd C:\Users\BusinessIntelligence\raksha-erp-deploy
python -m uvicorn backend.main:app --reload --port 8000

# Open browser
http://localhost:8000

# Login: admin / RS@2026
# Test: Purchase Rates, Transporters, GP Calculation, PDF Generation
```
