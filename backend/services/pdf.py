"""PDF generation helpers for PI/PO documents."""
from html import escape as escape_html
from config import TCS_RATE
from services.discount import calculate_discount_scheme


def _get_gst_rate():
    """Lazy import to avoid circular dependency."""
    from database import SessionLocal
    from models import Settings
    try:
        db = SessionLocal()
        row = db.query(Settings).filter(Settings.key == "default_gst_rate").first()
        db.close()
        return float(row.value) if row else 18.0
    except Exception:
        return 18.0


COMPANY_BANK_DETAILS = """
<div style="margin-top:15px;font-size:11px;">
<h4 style="margin:0 0 6px 0;font-size:13px;">Bank Details</h4>
<table style="font-size:11px;">
<tr><td style="font-weight:bold;padding-right:10px;">Name:</td><td>Raksha Pipes Pvt. Ltd.</td></tr>
<tr><td style="font-weight:bold;padding-right:10px;">Account Number:</td><td>004705011678</td></tr>
<tr><td style="font-weight:bold;padding-right:10px;">Bank Name:</td><td>ICICI Bank Ltd.</td></tr>
<tr><td style="font-weight:bold;padding-right:10px;">Branch Name:</td><td>Koramangala, Bengaluru</td></tr>
<tr><td style="font-weight:bold;padding-right:10px;">IFSC Code:</td><td>ICIC0000047</td></tr>
</table>
</div>
"""


def _billing_site_header(bs=None):
    name = (bs.name if bs else "Raksha Pipes Private Limited").replace("Private Limited", "Pvt. Ltd.") if bs else "Raksha Pipes Pvt. Ltd."
    address = bs.address if bs else ""
    phone = bs.phone if bs else ""
    email = bs.email if bs else ""
    website = bs.website if bs else "www.rakshapipes.com"
    gstin = bs.gstin if bs else ""
    state_code = bs.state_code if bs else ""
    pan = bs.pan if bs else ""
    return f"""
<div style="text-align:center;border-bottom:3px double #000;padding-bottom:10px;margin-bottom:10px;">
<h1 style="margin:0;font-size:22px;font-weight:bold;letter-spacing:1px;">{escape_html(name)}</h1>
<p style="margin:2px 0;font-size:11px;">{escape_html(address)}</p>
<table style="width:100%;font-size:10px;margin-top:6px;"><tr>
<td style="text-align:left;">Phone: +91 - {escape_html(phone)}</td>
<td style="text-align:center;">Email: {escape_html(email)}</td>
<td style="text-align:right;">Website: {escape_html(website)}</td>
</tr><tr>
<td style="text-align:left;">State Code: {escape_html(state_code)}</td>
<td style="text-align:center;">GSTIN: {escape_html(gstin)}</td>
<td style="text-align:right;">PAN No: {escape_html(pan)}</td>
</tr></table>
</div>
"""


def generate_po_html(order, customer, items, pi_date, billing_site=None):
    """Generate Purchase Order HTML. Called from routes."""
    # Import here to avoid circular imports at module level
    from services.discount import calculate_discount_scheme as _calc_disc
    gst_rate = _get_gst_rate()

    cust_name = customer.contact_name if customer else (order.billing_site or "")
    cust_gstin = customer.gstin if customer else ""
    cust_state = customer.state if customer else ""

    bs_name = (billing_site.name if billing_site else "Raksha Pipes Private Limited").replace("Private Limited", "Pvt. Ltd.") if billing_site else "Raksha Pipes Pvt. Ltd."
    bs_address = billing_site.address if billing_site else ""
    bs_phone = billing_site.phone if billing_site else ""
    bs_email = billing_site.email if billing_site else ""
    bs_website = billing_site.website if billing_site else "www.rakshapipes.com"
    bs_gstin = billing_site.gstin if billing_site else ""
    bs_state_code = billing_site.state_code if billing_site else ""
    bs_pan = billing_site.pan if billing_site else ""

    items_html = ""
    total_box = 0
    total_pcs = 0
    total_amount = 0
    for item in items:
        box = item.qty_boxes or 0
        pcs = item.final_qty or 0
        amt = item.basic_amount or 0
        total_box += box
        total_pcs += pcs
        total_amount += amt
        items_html += f"""
        <tr>
            <td style="padding:5px 8px;border:1px solid #ccc;font-size:10px;">{item.part_no or ''}</td>
            <td style="padding:5px 8px;border:1px solid #ccc;font-size:10px;">{escape_html(item.description or '')} {escape_html(item.size or '')}</td>
            <td style="padding:5px 8px;border:1px solid #ccc;text-align:center;font-size:10px;">Box</td>
            <td style="padding:5px 8px;border:1px solid #ccc;text-align:center;font-size:10px;">{item.std_packaging or 0}</td>
            <td style="padding:5px 8px;border:1px solid #ccc;text-align:center;font-size:10px;">{pcs}</td>
            <td style="padding:5px 8px;border:1px solid #ccc;text-align:right;font-size:10px;">&#8377;{item.mrp:,.0f}</td>
            <td style="padding:5px 8px;border:1px solid #ccc;text-align:right;font-size:10px;">&#8377;{amt:,.0f}</td>
        </tr>"""

    gst_amount = total_amount * gst_rate / 100
    grand_total = total_amount + gst_amount

    discount_html = ""
    discount_amount = 0
    if order.discount_scheme_applied:
        total_discount_pct, _, _ = _calc_disc(total_amount)
        if total_discount_pct > 0:
            discount_amount = total_amount * total_discount_pct / 100
            after_discount = total_amount - discount_amount
            gst_amount = after_discount * gst_rate / 100
            grand_total = after_discount + gst_amount
        discount_html = f"""
        <tr style="font-weight:bold;color:#059669;">
            <td colspan="6" style="padding:6px 8px;border:1px solid #ccc;text-align:right;font-size:11px;">Discount Scheme ({total_discount_pct}%)</td>
            <td style="padding:6px 8px;border:1px solid #ccc;text-align:right;font-size:11px;">-&#8377;{discount_amount:,.0f}</td>
        </tr>
        <tr style="font-weight:bold;">
            <td colspan="6" style="padding:6px 8px;border:1px solid #ccc;text-align:right;font-size:11px;">After Discount</td>
            <td style="padding:6px 8px;border:1px solid #ccc;text-align:right;font-size:11px;">&#8377;{after_discount:,.0f}</td>
        </tr>"""

    html = f"""<!DOCTYPE html><html><head><title>Purchase Order</title>
<style>
body{{font-family:Arial,sans-serif;margin:15px;font-size:11px;color:#000;}}
table{{width:100%;border-collapse:collapse;}}
@page{{size:A4;margin:10mm;}}
@media print{{body{{margin:5mm;}}}}
</style></head><body>

{_billing_site_header(billing_site)}

<table style="margin-bottom:8px;font-size:11px;width:100%;">
<tr>
<td style="width:50%;vertical-align:top;">
<b>VENDOR / Supplier Details</b><br>
<table style="font-size:10px;margin-top:4px;">
<tr><td style="padding:1px 8px 1px 0;font-weight:bold;">Company Name:</td><td>{escape_html(cust_name)}</td></tr>
<tr><td style="padding:1px 8px 1px 0;font-weight:bold;">Address:</td><td>{escape_html(order.billing_site or '')}</td></tr>
<tr><td style="padding:1px 8px 1px 0;font-weight:bold;">State Code:</td><td>{escape_html(cust_state)}</td></tr>
<tr><td style="padding:1px 8px 1px 0;font-weight:bold;">GSTIN:</td><td>{escape_html(cust_gstin)}</td></tr>
</table>
</td>
<td style="width:50%;vertical-align:top;">
<table style="font-size:10px;float:right;">
<tr><td style="padding:1px 8px 1px 0;font-weight:bold;">Contact Person:</td><td>{escape_html(customer.contact_name if customer else '')}</td></tr>
<tr><td style="padding:1px 8px 1px 0;font-weight:bold;">Mobile No:</td><td>{escape_html(customer.contact_number if customer else '')}</td></tr>
<tr><td style="padding:1px 8px 1px 0;font-weight:bold;">Email:</td><td>{escape_html(customer.contact_email if customer else '')}</td></tr>
<tr><td style="padding:1px 8px 1px 0;font-weight:bold;">Payment Terms:</td><td>100% Advance</td></tr>
</table>
</td>
</tr>
</table>

<table style="width:100%;margin-bottom:6px;font-size:11px;">
<tr>
<td style="width:20%;font-weight:bold;">Anand No.:</td>
<td style="width:15%;"></td>
<td style="width:30%;text-align:center;font-size:16px;font-weight:bold;border-top:2px solid #000;border-bottom:2px solid #000;padding:4px;">PURCHASE ORDER</td>
<td style="width:15%;text-align:right;font-weight:bold;">PO No:</td>
<td style="width:20%;text-align:right;">{order.pi_no or ''}</td>
</tr>
<tr>
<td style="font-weight:bold;">PO Date:</td>
<td>{pi_date}</td>
<td></td>
<td style="text-align:right;font-weight:bold;">Amd No.:</td>
<td></td>
</tr>
</table>

<table style="width:100%;border:1px solid #ccc;margin-top:8px;">
<thead><tr style="background:#f0f0f0;">
<th style="padding:6px;border:1px solid #ccc;text-align:left;font-size:10px;width:18%;">Part No</th>
<th style="padding:6px;border:1px solid #ccc;text-align:left;font-size:10px;width:30%;">Description</th>
<th style="padding:6px;border:1px solid #ccc;text-align:center;font-size:10px;width:8%;">Box</th>
<th style="padding:6px;border:1px solid #ccc;text-align:center;font-size:10px;width:10%;">Pcs</th>
<th style="padding:6px;border:1px solid #ccc;text-align:center;font-size:10px;width:10%;">Total Pcs</th>
<th style="padding:6px;border:1px solid #ccc;text-align:right;font-size:10px;width:12%;">Rate</th>
<th style="padding:6px;border:1px solid #ccc;text-align:right;font-size:10px;width:12%;">Amount</th>
</tr></thead>
<tbody>{items_html}</tbody>
<tfoot>
<tr style="font-weight:bold;background:#f9f9f9;">
<td colspan="2" style="padding:6px 8px;border:1px solid #ccc;font-size:11px;">Total</td>
<td style="padding:6px 8px;border:1px solid #ccc;text-align:center;font-size:11px;">{total_box}</td>
<td style="padding:6px 8px;border:1px solid #ccc;text-align:center;font-size:11px;">{total_pcs}</td>
<td style="padding:6px 8px;border:1px solid #ccc;text-align:center;font-size:11px;">{total_pcs}</td>
<td style="padding:6px 8px;border:1px solid #ccc;"></td>
<td style="padding:6px 8px;border:1px solid #ccc;text-align:right;font-size:11px;">&#8377;{total_amount:,.0f}</td>
</tr>
{discount_html}
<tr style="font-weight:bold;">
<td colspan="6" style="padding:6px 8px;border:1px solid #ccc;text-align:right;font-size:11px;">GST  18%</td>
<td style="padding:6px 8px;border:1px solid #ccc;text-align:right;font-size:11px;">&#8377;{gst_amount:,.0f}</td>
</tr>
<tr style="font-weight:bold;background:#f0f0f0;">
<td colspan="6" style="padding:8px;border:1px solid #ccc;text-align:right;font-size:13px;">GRAND TOTAL</td>
<td style="padding:8px;border:1px solid #ccc;text-align:right;font-size:13px;">&#8377;{grand_total:,.0f}</td>
</tr>
</tfoot></table>

<table style="width:100%;margin-top:40px;font-size:11px;border:none;">
<tr>
<td style="width:33%;text-align:center;border-top:1px solid #000;padding-top:8px;">CREATED BY</td>
<td style="width:33%;text-align:center;border-top:1px solid #000;padding-top:8px;">REVIEWED BY</td>
<td style="width:33%;text-align:center;border-top:1px solid #000;padding-top:8px;">APPROVED BY</td>
</tr>
</table>

</body></html>"""
    return html


def generate_pi_html(order, customer, items, pi_date, billing_site=None):
    """Generate Proforma Invoice HTML. Called from routes."""
    from services.discount import calculate_discount_scheme as _calc_disc
    gst_rate = _get_gst_rate()

    cust_name = customer.contact_name if customer else (order.billing_site or "")
    cust_gstin = customer.gstin if customer else ""
    cust_state = customer.state if customer else ""
    cust_id = customer.customer_id if customer else ""

    items_html = ""
    total_box = 0
    total_pcs = 0
    total_basic = 0
    total_lock_hinge = 0
    for item in items:
        box = item.qty_boxes or 0
        pcs = item.final_qty or 0
        mrp = item.mrp or 0
        d1 = item.d1 or 0
        d2 = item.d2 or 0
        d3 = item.d3 or 0
        d4 = item.d4 or 0
        d5 = item.d5 or 0
        cd = item.cd or 0
        lock = item.lock_hinge or 0
        net = item.net_rate or 0
        amt = item.basic_amount or 0
        total_box += box
        total_pcs += pcs
        total_basic += amt
        total_lock_hinge += lock

        base = mrp
        after_d1 = base - (base * d1 / 100) if d1 else base
        after_d2 = after_d1 - (after_d1 * d2 / 100) if d2 else after_d1
        after_d3 = after_d2 - (after_d2 * d3 / 100) if d3 else after_d2
        after_d4 = after_d3 - (after_d3 * d4 / 100) if d4 else after_d3
        after_d5 = after_d4 - (after_d4 * d5 / 100) if d5 else after_d4
        after_cd = after_d5 - (after_d5 * cd / 100) if cd else after_d5

        items_html += f"""
        <tr>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">{item.sl_no}</td>
            <td style="padding:4px 6px;border:1px solid #ccc;font-size:9px;">{escape_html(item.description or '')} ({escape_html(item.size or '')})</td>
            <td style="padding:4px 6px;border:1px solid #ccc;font-size:9px;">{escape_html(item.category or '')}</td>
            <td style="padding:4px 6px;border:1px solid #ccc;font-size:9px;">{escape_html(item.part_no or '')}</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">FRP</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">Box</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">{item.std_packaging or 0}</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">{pcs}</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">Pieces</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;">{mrp:,.0f}</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">{d1}%</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;">{after_d1:,.2f}</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">{d2}%</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;">{after_d2:,.2f}</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">{d3}%</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;">{after_d3:,.2f}</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">{d4}%</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;">{after_d4:,.2f}</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">{d5}%</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;">{after_d5:,.2f}</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:center;font-size:9px;">{cd}%</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;font-weight:bold;">{after_cd:,.2f}</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;">{lock:,.0f}</td>
            <td style="padding:4px 6px;border:1px solid #ccc;text-align:right;font-size:9px;font-weight:bold;">{amt:,.2f}</td>
        </tr>"""

    packing_charges = 0
    sub_total = total_basic + packing_charges

    discount_html_row = ""
    discount_amount = 0
    if order.discount_scheme_applied:
        total_discount_pct, _, _ = _calc_disc(sub_total)
        if total_discount_pct > 0:
            discount_amount = sub_total * total_discount_pct / 100
            sub_total = sub_total - discount_amount
            discount_html_row = f'<tr><td style="padding:2px 8px;font-weight:bold;color:#059669;">DISCOUNT SCHEME ({total_discount_pct}%)</td><td style="text-align:right;padding:2px 8px;color:#059669;">-&#8377;{discount_amount:,.2f}</td></tr>'

    gst = sub_total * gst_rate / 100
    total_value = sub_total + gst
    tcs_amount = total_value * TCS_RATE
    final_value = total_value + tcs_amount

    html = f"""<!DOCTYPE html><html><head><title>Quotation cum Proforma Invoice</title>
<style>
body{{font-family:Arial,sans-serif;margin:10px;font-size:10px;color:#000;}}
table{{width:100%;border-collapse:collapse;}}
@page{{size:landscape A4;margin:8mm;}}
@media print{{body{{margin:5mm;}}}}
</style></head><body>

{_billing_site_header(billing_site)}

<table style="width:100%;font-size:10px;margin-bottom:8px;">
<tr>
<td style="width:50%;vertical-align:top;">
<table style="font-size:10px;">
<tr><td style="padding:1px 6px;font-weight:bold;width:120px;">CONSIGNEE ERP CODE</td><td>{escape_html(cust_id)}</td>
<td style="padding:1px 6px;font-weight:bold;width:120px;">KYC STATUS</td><td></td></tr>
<tr><td style="padding:1px 6px;font-weight:bold;">CONSIGNEE NAME</td><td>{escape_html(cust_name)}</td>
<td style="padding:1px 6px;font-weight:bold;">NAME OF SALE EXECUTIVE</td><td>{escape_html(customer.exec_name if customer else '')}</td></tr>
<tr><td style="padding:1px 6px;font-weight:bold;">LOCATION</td><td>{escape_html(customer.city if customer else '')}</td>
<td style="padding:1px 6px;font-weight:bold;">LOCATION</td><td>{escape_html(customer.city if customer else '')}</td></tr>
<tr><td style="padding:1px 6px;font-weight:bold;">STATE</td><td>{escape_html(cust_state)}</td>
<td style="padding:1px 6px;font-weight:bold;">STATE</td><td>{escape_html(cust_state)}</td></tr>
<tr><td style="padding:1px 6px;font-weight:bold;">PURCHASE ORDER NO</td><td>{escape_html(order.pi_no or '')}</td>
<td style="padding:1px 6px;font-weight:bold;">BILL TO ADDRESS CODE</td><td></td></tr>
<tr><td style="padding:1px 6px;font-weight:bold;">PURCHASE ORDER DATE</td><td>{pi_date}</td>
<td style="padding:1px 6px;font-weight:bold;">SHIP TO ADDRESS CODE</td><td></td></tr>
<tr><td style="padding:1px 6px;font-weight:bold;">PLANNING DATE</td><td>{pi_date}</td>
<td style="padding:1px 6px;font-weight:bold;">TOTAL WEIGHT</td><td></td></tr>
<tr><td style="padding:1px 6px;font-weight:bold;">DESPATCH DATE</td><td>{pi_date}</td>
<td style="padding:1px 6px;font-weight:bold;">TOTAL VALUE</td><td>&#8377;{total_basic:,.2f}</td></tr>
<tr><td style="padding:1px 6px;font-weight:bold;">STATE SR NO</td><td></td>
<td style="padding:1px 6px;font-weight:bold;">TRADE DISCOUNT</td><td></td></tr>
</table>
</td>
</tr>
</table>

<div style="overflow-x:auto;">
<table style="width:100%;border:1px solid #ccc;font-size:9px;">
<thead><tr style="background:#1a365d;color:white;">
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">SN</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Product Specification</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Size in (Inch &amp; MM)</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">ERP Part No</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Item Grp.</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Base UOM</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Std Packing</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Final Qty</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Final UOM</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Gen</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">D-1</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Net</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">D-2</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Net Rt</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">D-3</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Net Rt</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">D-4</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Net Rt</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">D-5</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Net Rt</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">CD</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Net Rt</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Lock &amp; Hings</th>
<th style="padding:4px;border:1px solid #ccc;font-size:8px;">Basic Amt Without GST</th>
</tr></thead>
<tbody>{items_html}</tbody>
<tfoot>
<tr style="font-weight:bold;background:#f0f0f0;">
<td colspan="5" style="padding:5px 8px;border:1px solid #ccc;font-size:10px;">TOTAL</td>
<td style="padding:5px 8px;border:1px solid #ccc;text-align:center;">Box</td>
<td style="padding:5px 8px;border:1px solid #ccc;text-align:center;">{total_box}</td>
<td style="padding:5px 8px;border:1px solid #ccc;text-align:center;">{total_pcs}</td>
<td style="padding:5px 8px;border:1px solid #ccc;text-align:center;">Pieces</td>
<td colspan="11" style="padding:5px 8px;border:1px solid #ccc;"></td>
<td style="padding:5px 8px;border:1px solid #ccc;text-align:right;">{total_lock_hinge:,.0f}</td>
<td style="padding:5px 8px;border:1px solid #ccc;text-align:right;">{total_basic:,.2f}</td>
</tr>
</tfoot></table>
</div>

<table style="width:100%;margin-top:10px;font-size:11px;">
<tr>
<td style="width:50%;vertical-align:top;">
{COMPANY_BANK_DETAILS}
</td>
<td style="width:50%;vertical-align:top;text-align:right;">
<table style="float:right;font-size:11px;">
<tr><td style="padding:2px 8px;font-weight:bold;">BASIC VALUE</td><td style="text-align:right;padding:2px 8px;">&#8377;{total_basic:,.2f}</td></tr>
<tr><td style="padding:2px 8px;font-weight:bold;">ADD PACKING &amp; FORWARDING CHARGES</td><td style="text-align:right;padding:2px 8px;">&#8377;{packing_charges:,.2f}</td></tr>
{discount_html_row}
<tr><td style="padding:2px 8px;font-weight:bold;">SUB TOTAL</td><td style="text-align:right;padding:2px 8px;">&#8377;{sub_total:,.2f}</td></tr>
<tr><td style="padding:2px 8px;font-weight:bold;">GST @ 18.00%</td><td style="text-align:right;padding:2px 8px;">&#8377;{gst:,.2f}</td></tr>
<tr><td style="padding:2px 8px;font-weight:bold;">TOTAL VALUE</td><td style="text-align:right;padding:2px 8px;">&#8377;{total_value:,.2f}</td></tr>
<tr><td style="padding:2px 8px;font-weight:bold;">TCS On Sales 0.1%</td><td style="text-align:right;padding:2px 8px;">&#8377;{tcs_amount:,.2f}</td></tr>
<tr><td style="padding:2px 8px;font-weight:bold;">ROUND OFF DIFF</td><td style="text-align:right;padding:2px 8px;">&#8377;0.00</td></tr>
<tr style="font-size:14px;font-weight:bold;border-top:2px solid #000;">
<td style="padding:6px 8px;">FINAL PI VALUE</td>
<td style="text-align:right;padding:6px 8px;">&#8377;{final_value:,.2f}</td></tr>
</table>
</td>
</tr>
</table>

<div style="margin-top:40px;text-align:right;font-size:11px;">
<p>For <b>{escape_html((billing_site.name if billing_site else "Raksha Pipes Private Limited").replace("Private Limited", "Pvt. Ltd."))}</b></p>
<p style="margin-top:30px;">Authorized Signatory</p>
</div>

</body></html>"""
    return html
