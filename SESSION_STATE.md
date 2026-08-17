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
- **Commit**: a30150b

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
- [x] Cache Busting: `app.js?v=20260805v1`
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
- [x] **Order Status Tracking**: `PUT /api/proforma-orders/{oid}/status` endpoint with draft→confirmed→po_created→transport_pending→transport_finalized→billing→completed workflow
- [x] **Order Status UI**: Status column with dropdown in orders table, color-coded badges, search support
- **Commit**: b72ce6d
- [x] **Sales Edit Fix**: Edit modal now shows stored invoice value as Total (not recalculated)
- [x] **Orders Table Split**: "Customer Name" and "Billing / Shipping Site" are now separate searchable columns
- [x] **Sales Multi-Item Support**: SaleItem model, items table in modal, add/remove/render/calc functions
- [x] **Sales Page N+1 Fix**: Batch-loaded customers + items in GET /api/sales (354 queries → 3)
- [x] **Single Sale Endpoint**: GET /api/sales/{id} for efficient single-sale fetch
- [x] **editSale() Optimization**: Fetches single sale instead of all 177
- [x] **Freight Summary Endpoint**: GET /api/sales/freight-summary (lightweight, no items)
- [x] **loadExpenses() Optimization**: Uses freight-summary instead of full sales list
- [x] **Sale Form Error Handling**: try-catch on submit, null checks in calcSaleTotals()
- [x] **Sales Customer Name Fix**: party_name/location/state now populated from Customer on create/update
- [x] **showModal Fix**: Only refreshDropdowns for new sales, not edits (was wiping customer selection)
- [x] **Customer Dropdown Fix**: Shows party_name for unlinked CSV-imported sales

## Important: Two Git Remotes
- `origin` = raksha-erp-deploy.git
- `original` = raksha-erp.git ← **Render connects here, deploy from `main` branch**
- Always push to: `git push original master:main`
- **Commit**: 5447f78 + 1c9234b + 8209112 + 72f7b54 + (N+1 fix + customer name fix + showModal fix)

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
- [x] Cache Busting: `app.js?v=20260805v1`
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
- [x] **Order Status Tracking**: `PUT /api/proforma-orders/{oid}/status` endpoint with draft→confirmed→po_created→transport_pending→transport_finalized→billing→completed workflow
- [x] **Order Status UI**: Status column with dropdown in orders table, color-coded badges, search support
- [x] **Sales Edit Fix**: Edit modal now shows stored invoice value as Total (not recalculated)
- [x] **Orders Table Split**: "Customer Name" and "Billing / Shipping Site" are now separate searchable columns
- [x] **Sales Multi-Item Support**: SaleItem model, items table in modal, add/remove/render/calc functions
- [x] **Sales Page N+1 Fix**: Batch-loaded customers + items in GET /api/sales (354 queries → 3)
- [x] **Single Sale Endpoint**: GET /api/sales/{id} for efficient single-sale fetch
- [x] **editSale() Optimization**: Fetches single sale instead of all 177
- [x] **Freight Summary Endpoint**: GET /api/sales/freight-summary (lightweight, no items)
- [x] **loadExpenses() Optimization**: Uses freight-summary instead of full sales list
- [x] **Sale Form Error Handling**: try-catch on submit, null checks in calcSaleTotals()
- [x] **Sales Customer Name Fix**: party_name/location/state now populated from Customer on create/update
- [x] **showModal Fix**: Only refreshDropdowns for new sales, not edits (was wiping customer selection)
- [x] **Customer Dropdown Fix**: Shows party_name for unlinked CSV-imported sales

## Bug Fixes (Aug 10, 2026)
- [x] **Discount Checkbox ID Fix**: `f-podiscount-scheme` → `f-poodiscount` (PDF discount never applied)
- [x] **Discount Slab Boundary Fix**: `min: 100100` → `min: 100001` (₹100,001-100,100 wrong slab)
- [x] **DELETE /api/transporters/{tid}**: Added missing endpoint (frontend called it but 404)
- [x] **CORS Fix**: Removed localhost origins (production-only)
- [x] **Admin Password Change**: Now requires current password even for admins changing own password
- [x] **Dashboard N+1 Fix**: Charts now use SQL GROUP BY instead of loading all Sales
- [x] **GST Rate Dynamic**: Now reads from Settings model instead of hardcoded 18%

## Code Quality (Aug 12, 2026)
- [x] **Logging Added**: `import logging` + `logger = logging.getLogger("raksha-erp")` at top of main.py
- [x] **15 Silent Error Handlers Fixed**: All `except: pass` blocks now log warnings/errors with context
- [x] **19 Pydantic Validation Models**: Added LoginIn, RefreshIn, UserCreateIn, UserUpdateIn, ChangePasswordIn, PurchaseRateIn, PurchaseRateUpdateIn, BulkPurchaseRateIn, TransportUpdateIn, OrderStatusIn, WhatsAppSendIn, WhatsAppSendPIIn, WhatsAppSendPOIn, WhatsAppTestIn, SaleInvoiceIn, BulkPaymentIn, BulkLRIn, LRTrackingIn, SettingsUpdateIn
- [x] **19 Endpoints Updated**: All raw `dict` params replaced with typed Pydantic models
- [x] **Hardcoded Secrets Removed**: WhatsApp token/phone ID/business account ID no longer hardcoded as fallbacks in main.py
- [x] **Test Files Cleaned**: test_sale.py and test_pdf.py now use env vars instead of hardcoded credentials
- [x] **Frontend Silent Catch Fixed**: app.js auto-generate-tracking-urls now logs errors instead of swallowing them
- [x] **SESSION_STATE.md Cleaned**: WhatsApp permanent token removed from plaintext
- [x] **P&L Tax Rate Dynamic**: Now reads from Settings model instead of hardcoded 25%
- [x] **editOrder Optimization**: Fetches single order instead of all orders
- [x] **editExpense Optimization**: Fetches single expense instead of all expenses
- [x] **editUser Optimization**: Fetches single user instead of all users
- [x] **Empty Catch Blocks**: All 7 empty catch(e){} blocks now log errors
- [x] **Sale Form Validation**: customer_id validated before submission
- [x] **Net Profit Calculation**: Now subtracts GST from gross profit
- [x] **fix-urls Method**: Changed from GET to POST (mutates data)
- [x] **Imports Cleanup**: Moved inline imports to top level (time, re, tempfile, uuid, csv, io)
- [x] **get_gst_rate() Helper**: Reads GST rate from Settings, used in all PDF/calc functions

## Code Quality - Round 2 (Aug 13, 2026)
- [x] **5 Form Submit Handlers**: Added try-catch to product, pricing, order, customer, expense forms
- [x] **XSS Fix**: onclick attributes now escape single quotes properly
- [x] **Bank Details Dynamic**: PDF generation reads bank account info from Settings API (not hardcoded)
- [x] **Discount Scheme Dynamic**: Frontend fetches discount scheme from API (not hardcoded)
- [x] **Token Refresh**: api() function now attempts token refresh before logout on 401
- [x] **CSS Fix**: `cursor-pointer` corrected to `cursor:pointer` on Send PO button
- [x] **Responsive Design**: Added mobile breakpoints (1024px, 768px, 480px) for sidebar, tables, modals
- [x] **Accessibility**: Added ARIA attributes to nav, search inputs, and all 12 modals
- [x] **Meta Tags**: Added description, noscript fallback
- [x] **Settings UI**: Added bank detail fields (account name, number, bank, branch, IFSC)
- [x] **Cache Busting**: Updated to `?v=20260813v1`

## IMPORTANT: WhatsApp PDF Fix Needed on Render
- **Root cause**: Test token can send text but NOT PDFs. Permanent token works for both.
- **What user must do**: Update `WHATSAPP_TOKEN` env var on Render to permanent token, then Manual Deploy.
- **Permanent token**: Set `WHATSAPP_TOKEN` env var on Render (see Render dashboard)
- **Test phone**: +916366263535
- **Verified**: Media upload + send works with permanent token (tested locally)

## Discount Scheme (Aug 1 - Oct 31, 2026)
- **Base discount**: 54%
- **Slab additional** (on basic value excl. C.D & GST):
  - ₹50,100 - ₹75,000: +2.5% (total 56.5%)
  - ₹75,100 - ₹1,00,000: +5% (total 59%)
  - ₹1,01,000 - ₹2,00,000: +7% (total 61%)
  - ₹2,00,001 & Above: +9% (total 63%)
- **Backend**: `DISCOUNT_SCHEME` constants + `calculate_discount_scheme()` function
- **Endpoints**: `GET /api/discount-scheme`, `GET /api/discount-calculate/{basic_value}`
- **DB columns**: `discount_scheme_applied`, `discount_percent`, `discount_amount` on ProformaOrder
- **UI**: Checkbox toggle in PI/PO modal, real-time discount display in totals
- **PDF**: Discount breakdown shown in both PI and PO PDFs
- **Commit**: 8e09a53

## WhatsApp Token
- **Phone**: +1 555-203-8077 (test number)
- **Phone ID**: 1299086943278503
- **Business Account ID**: 4397763287203081
- **Tested with**: +916366263535 ✅

## Next Steps
1. **WhatsApp Integration** — Using Meta WhatsApp Cloud API (user to provide credentials)
   - PI auto-send as PDF to Sales Manager/Executive
   - PO auto-send to WhatsApp Group in product table format
   - Transporter broadcast (address only, no party name)
2. **WhatsApp Message Formats** — User to share screenshots of PI/PO/broadcast formats

## What User Has Provided
1. Meta WhatsApp Cloud API credentials ✅
   - Phone Number ID: 1299086943278503
   - WhatsApp Business Account ID: 4397763287203081
   - Access Token: Configured
2. Discount structure (tiers by order value) — ✅ IMPLEMENTED

## What User Will Provide
1. WhatsApp message format screenshots (PI, PO, transporter broadcast)
2. WhatsApp Group details for PO delivery
3. Any additional business requirements

## Files Modified
- `backend/main.py` (~4900+ lines) — auth, bug fixes, endpoints, billing sites, PDF generation, purchase rates, GP calc, WhatsApp integration, order status endpoint, SaleItem model, multi-item sales CRUD, discount scheme
- `frontend/js/app.js` (~2860+ lines) — auth, escapeHtml, user mgmt, PO/PI form/PDF, billing site dropdown, purchase rates UI, GP display, order status UI, sales multi-item functions, discount scheme UI
- `frontend/index.html` (~910+ lines) — full UI with login overlay, user header, modals, purchase rates page, GP section, order status column, sales items table, discount scheme checkbox
- `requirements.txt` — fastapi, bcrypt, PyJWT, fpdf2, beautifulsoup4, requests

## How to Test
```bash
# Everything is LIVE on Render — no local server needed
# API base: https://raksha-erp-deploy.onrender.com
# Login: admin / RS@2026

# IMPORTANT: Do NOT try localhost — nothing runs locally
# IMPORTANT: Render deploys from 'original' remote, 'main' branch
# Push with: git push original master:main

# Test via API:
# python -c "import requests; r=requests.post('https://raksha-erp-deploy.onrender.com/api/auth/login', json={'username':'admin','password':'RS@2026'}); print(r.json())"
```

## Next Task
Fix WhatsApp token (update WHATSAPP_TOKEN env var on Render), then test WhatsApp PDF sending.
