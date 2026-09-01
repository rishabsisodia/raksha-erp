from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from datetime import datetime, timezone
import uuid
import logging

from models import Sale, SaleItem, Customer, Product, Pricing, Settings
from schemas import SaleIn, SaleItemIn, SaleInvoiceIn, BulkPaymentIn, BulkLRIn
from auth import get_current_user, require_permission
from database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sales"])


def _get_setting(key, default=""):
    try:
        db = SessionLocal()
        row = db.query(Settings).filter(Settings.key == key).first()
        db.close()
        return row.value if row else default
    except Exception:
        return default


def get_gst_rate():
    val = _get_setting("default_gst_rate", "18")
    try:
        return float(val)
    except Exception:
        return 18.0


def _sale_to_dict(s, sale_items=None, cust_name=""):
    party = s.party_name or cust_name or ""
    loc = s.location or ""
    items = sale_items if sale_items is not None else []
    return {
        "id": s.id, "invoice_no": s.invoice_no or "",
        "customer_id": s.customer_id or None,
        "product_id": s.product_id or None,
        "quantity": s.quantity or 0,
        "unit_price": s.unit_price or 0,
        "discount_percent": s.discount_percent or 0,
        "taxable_amount": s.taxable_amount or 0,
        "cgst_amount": s.cgst_amount or 0,
        "sgst_amount": s.sgst_amount or 0,
        "freight_amount": s.freight_amount or 0,
        "payment_status": s.payment_status or "",
        "payment_method": s.payment_method or "",
        "notes": s.notes or "",
        "party_name": party, "location": loc,
        "state": s.state or "",
        "transporter_name": s.transporter_name or "",
        "lr_no": s.lr_no or "",
        "weight_kgs": s.weight_kgs or 0,
        "gp": s.gp or 0,
        "gp_percent": s.gp_percent or 0,
        "invoice_value": s.invoice_value or 0,
        "total_amount": s.total_amount or 0,
        "sale_date": s.sale_date.isoformat() if s.sale_date else None,
        "payment_terms": s.payment_terms or "",
        "source_csv": s.source_csv or "",
        "lr_tracking_status": s.lr_tracking_status or "",
        "lr_tracking_url": s.lr_tracking_url or "",
        "lr_last_checked": s.lr_last_checked.isoformat() if s.lr_last_checked else None,
        "items": items,
    }


def _sale_item_dict(si):
    return {
        "id": si.id, "sl_no": si.sl_no,
        "product_id": si.product_id,
        "quantity": si.quantity, "unit_price": si.unit_price,
        "discount_percent": si.discount_percent,
        "taxable_amount": si.taxable_amount,
        "gst_rate": si.gst_rate,
        "cgst_amount": si.cgst_amount,
        "sgst_amount": si.sgst_amount,
        "total_amount": si.total_amount,
    }


@router.get("/api/sales")
def list_sales(limit: int = 500, offset: int = 0, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        total = db.query(func.count(Sale.id)).scalar()
        rows = db.query(Sale).order_by(Sale.id.desc()).offset(offset).limit(limit).all()
        cust_ids = list(set(s.customer_id for s in rows if s.customer_id))
        cust_map = {}
        if cust_ids:
            custs = db.query(Customer).filter(Customer.id.in_(cust_ids)).all()
            cust_map = {c.id: c.contact_name for c in custs}
        sale_ids = [s.id for s in rows]
        all_items = db.query(SaleItem).filter(SaleItem.sale_id.in_(sale_ids)).order_by(SaleItem.sl_no).all()
        items_map = {}
        for si in all_items:
            items_map.setdefault(si.sale_id, []).append(si)
        out = []
        for s in rows:
            try:
                cust_name = cust_map.get(s.customer_id, "") if s.customer_id else ""
                sale_items = [_sale_item_dict(si) for si in items_map.get(s.id, [])]
                out.append(_sale_to_dict(s, sale_items, cust_name))
            except Exception as e:
                logger.error(f"Error loading sale {s.id}: {e}")
                continue
        return {"total": total, "items": out}
    finally:
        db.close()


@router.get("/api/sales/freight-summary")
def freight_summary(user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        rows = db.query(Sale).filter(Sale.freight_amount > 0, Sale.weight_kgs > 0).order_by(Sale.id.desc()).all()
        out = []
        for s in rows:
            out.append({
                "id": s.id, "invoice_no": s.invoice_no or "",
                "sale_date": s.sale_date.isoformat() if s.sale_date else None,
                "freight_amount": s.freight_amount or 0,
                "weight_kgs": s.weight_kgs or 0,
                "transporter_name": s.transporter_name or "",
            })
        return out
    finally:
        db.close()


@router.get("/api/sales/{sid}")
def get_sale(sid: int, user: dict = Depends(get_current_user)):
    db = SessionLocal()
    try:
        s = db.query(Sale).filter(Sale.id == sid).first()
        if not s:
            raise HTTPException(status_code=404, detail="Sale not found")
        cust_name = ""
        if s.customer_id:
            cust = db.query(Customer).filter(Customer.id == s.customer_id).first()
            cust_name = cust.contact_name if cust else ""
        sale_items = [_sale_item_dict(si) for si in db.query(SaleItem).filter(SaleItem.sale_id == s.id).order_by(SaleItem.sl_no).all()]
        return _sale_to_dict(s, sale_items, cust_name)
    finally:
        db.close()


@router.post("/api/sales")
def create_sale(inp: SaleIn, user: dict = Depends(require_permission("sales", "create"))):
    db = SessionLocal()
    try:
        invoice_no = f"RFRP-{uuid.uuid4().hex[:8].upper()}"

        total_taxable = 0
        total_cgst = 0
        total_sgst = 0
        total_amount = 0

        s = Sale(
            invoice_no=invoice_no, customer_id=inp.customer_id,
            freight_amount=inp.freight_amount,
            payment_status=inp.payment_status, payment_method=inp.payment_method,
            notes=inp.notes, transporter_name=inp.transporter_name, lr_no=inp.lr_no,
            invoice_value=inp.invoice_value, sale_date=datetime.now(timezone.utc)
        )
        if inp.customer_id:
            cust = db.query(Customer).filter(Customer.id == inp.customer_id).first()
            if cust:
                s.party_name = cust.contact_name or cust.name or ""
                s.location = cust.billing_address or cust.city or ""
                s.state = cust.state or ""
        db.add(s)
        db.flush()

        for idx, item in enumerate(inp.items):
            prod = db.query(Product).filter(Product.id == item.product_id).first()
            if not prod:
                continue
            pr = db.query(Pricing).filter(Pricing.product_id == item.product_id).first()
            gst_rate = pr.gst_rate if pr else 18

            taxable = item.quantity * item.unit_price
            disc_amt = taxable * item.discount_percent / 100
            taxable -= disc_amt
            cgst = taxable * gst_rate / 200
            sgst = taxable * gst_rate / 200
            item_total = taxable + cgst + sgst

            total_taxable += taxable
            total_cgst += cgst
            total_sgst += sgst
            total_amount += item_total

            db.add(SaleItem(
                sale_id=s.id, sl_no=idx + 1,
                product_id=item.product_id, quantity=item.quantity,
                unit_price=item.unit_price, discount_percent=item.discount_percent,
                discount_amount=disc_amt, taxable_amount=taxable,
                gst_rate=gst_rate, cgst_amount=cgst, sgst_amount=sgst,
                total_amount=item_total, basic_amount=item_total
            ))

        grand_total = total_amount + inp.freight_amount
        s.taxable_amount = total_taxable
        s.cgst_amount = total_cgst
        s.sgst_amount = total_sgst
        s.total_amount = grand_total
        if not s.invoice_value:
            s.invoice_value = grand_total

        if not inp.product_id and inp.items:
            s.product_id = inp.items[0].product_id
            s.quantity = sum(i.quantity for i in inp.items)
            s.unit_price = inp.items[0].unit_price
            s.discount_percent = inp.items[0].discount_percent

        db.commit()
        return {"invoice_no": invoice_no, "total": grand_total}
    finally:
        db.close()


@router.delete("/api/sales/{sid}")
def delete_sale(sid: int, user: dict = Depends(require_permission("sales", "delete"))):
    db = SessionLocal()
    try:
        s = db.query(Sale).filter(Sale.id == sid).first()
        if not s:
            raise HTTPException(404, "Not found")
        db.query(SaleItem).filter(SaleItem.sale_id == sid).delete()
        db.delete(s)
        db.commit()
        return {"message": "Deleted"}
    finally:
        db.close()


@router.patch("/api/sales/{sid}/invoice")
def patch_sale_invoice(sid: int, body: SaleInvoiceIn, user: dict = Depends(require_permission("sales", "edit"))):
    db = SessionLocal()
    try:
        s = db.query(Sale).filter(Sale.id == sid).first()
        if not s:
            raise HTTPException(404, "Not found")
        if body.invoice_value:
            s.invoice_value = body.invoice_value
        db.commit()
        return {"message": "Patched", "id": sid, "invoice_value": s.invoice_value}
    finally:
        db.close()


@router.put("/api/sales/{sid}")
def update_sale(sid: int, inp: SaleIn, user: dict = Depends(require_permission("sales", "edit"))):
    db = SessionLocal()
    try:
        s = db.query(Sale).filter(Sale.id == sid).first()
        if not s:
            raise HTTPException(404, "Not found")

        total_taxable = 0
        total_cgst = 0
        total_sgst = 0
        total_amount = 0

        db.query(SaleItem).filter(SaleItem.sale_id == sid).delete()

        for idx, item in enumerate(inp.items):
            prod = db.query(Product).filter(Product.id == item.product_id).first()
            if not prod:
                continue
            pr = db.query(Pricing).filter(Pricing.product_id == item.product_id).first()
            gst_rate = pr.gst_rate if pr else 18

            taxable = item.quantity * item.unit_price
            disc_amt = taxable * item.discount_percent / 100
            taxable -= disc_amt
            cgst = taxable * gst_rate / 200
            sgst = taxable * gst_rate / 200
            item_total = taxable + cgst + sgst

            total_taxable += taxable
            total_cgst += cgst
            total_sgst += sgst
            total_amount += item_total

            db.add(SaleItem(
                sale_id=s.id, sl_no=idx + 1,
                product_id=item.product_id, quantity=item.quantity,
                unit_price=item.unit_price, discount_percent=item.discount_percent,
                discount_amount=disc_amt, taxable_amount=taxable,
                gst_rate=gst_rate, cgst_amount=cgst, sgst_amount=sgst,
                total_amount=item_total, basic_amount=item_total
            ))

        grand_total = total_amount + inp.freight_amount
        s.customer_id = inp.customer_id
        if inp.customer_id:
            cust = db.query(Customer).filter(Customer.id == inp.customer_id).first()
            if cust:
                s.party_name = cust.contact_name or cust.name or ""
                s.location = cust.billing_address or cust.city or ""
                s.state = cust.state or ""
        s.freight_amount = inp.freight_amount
        s.taxable_amount = total_taxable
        s.cgst_amount = total_cgst
        s.sgst_amount = total_sgst
        s.total_amount = grand_total
        s.invoice_value = inp.invoice_value or grand_total
        s.payment_status = inp.payment_status
        s.payment_method = inp.payment_method
        s.notes = inp.notes
        s.transporter_name = inp.transporter_name or s.transporter_name or ""
        s.lr_no = inp.lr_no or s.lr_no or ""

        if inp.items:
            s.product_id = inp.items[0].product_id
            s.quantity = sum(i.quantity for i in inp.items)
            s.unit_price = inp.items[0].unit_price
            s.discount_percent = inp.items[0].discount_percent

        db.commit()
        return {"message": "Sale updated", "total": grand_total}
    finally:
        db.close()


@router.patch("/api/sales/bulk-payment")
def bulk_update_payment_status(body: BulkPaymentIn, user: dict = Depends(require_permission("sales", "bulk_edit"))):
    status = body.status
    db = SessionLocal()
    try:
        updated = db.query(Sale).filter(Sale.id.in_(body.ids)).update({"payment_status": status}, synchronize_session=False)
        db.commit()
        return {"updated": updated, "message": f"Updated {updated} sales to {status}"}
    finally:
        db.close()


@router.patch("/api/sales/bulk-lr-status")
def bulk_update_lr_status(body: BulkLRIn, user: dict = Depends(require_permission("sales", "bulk_edit"))):
    status = body.lr_no or "Delivered"
    db = SessionLocal()
    try:
        q = db.query(Sale)
        if body.ids:
            q = q.filter(Sale.id.in_(body.ids))
        updated = q.filter(Sale.lr_tracking_status != status).update({"lr_tracking_status": status}, synchronize_session=False)
        db.commit()
        return {"updated": updated, "message": f"Updated {updated} sales to {status}"}
    finally:
        db.close()
