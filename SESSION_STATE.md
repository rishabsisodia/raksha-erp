# Raksha ERP - Session State

## What We're Building
Raksha ERP system for **Raksha Pipes Private Limited** (FRP products, manufacturing, sales, orders, expenses).

## Key Details
- **Company**: Raksha Pipes Private Limited (Pvt. Ltd. = short form for Private Limited)
- **Roles**: Admin (full + user mgmt), Manager (create/edit), Viewer (read-only)
- **Auth**: JWT (8hr access, 30day refresh), bcrypt hashing
- **Login**: `admin` / `admin123` (default, auto-migrated from SHA-256 to bcrypt)
- **GSTIN**: 23AACCV0019M1ZJ | **PAN**: AAVCR0941M | **State Code**: 23
- **Bank**: ICICI Bank Ltd., A/C 004705011678, IFSC ICIC0000047
- **16 Billing Sites** seeded from Excel (dynamic PO/PI headers)

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

## Just Completed (Current Session)
- [x] **Removed Terms & Conditions** from PO/PI PDFs:
  - Backend: `COMPANY_TERMS = ""` (was 10 lines of payment/delivery/freight terms)
  - Frontend: Removed `var TERMS` block and `html += TERMS;` reference
  - Verified: No remaining TERMS references in either file

## Next Steps (Do This First)
1. **Test PDF Generation** — Start the server, create a test PO/PI, verify:
   - PO PDF: No terms section, correct company header, signature block present
   - PI PDF: No terms section, correct discount chain (D-1 through D-5, CD, Lock & Hings), TCS 0.1%, packing charges
   - Both: Correct billing site header based on dropdown selection
2. Wait for user feedback on PDF output
3. Potential further template refinements

## How to Test
```bash
# Start server
cd C:\Users\BusinessIntelligence\raksha-erp-deploy
python -m uvicorn backend.main:app --reload --port 8000

# Open browser
http://localhost:8000

# Login: admin / admin123
# Create test order → Generate PO/PI PDF
```

## Files Modified
- `backend\main.py` (~4000+ lines) — auth, bug fixes, endpoints, billing sites, PDF generation
- `frontend\js\app.js` (~2400+ lines) — auth, escapeHtml, user mgmt, PO/PI form/PDF, billing site dropdown
- `frontend\index.html` (~814 lines) — full UI with login overlay, user header, modals
- `requirements.txt` — fastapi, bcrypt, PyJWT, etc.
