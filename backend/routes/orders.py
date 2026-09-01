from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from ..models import (
    Order, ProformaOrder, ProformaOrderItem, Customer, BillingSite,
    PurchaseRate, Transporter, Product, Pricing, Settings, User,
)
from ..schemas import (
    OrderIn, ProformaOrderIn, ProformaOrderItemIn,
    TransportUpdateIn, OrderStatusIn,
)
from ..auth import get_current_user, require_permission, audit_log
from ..database import SessionLocal
from ..services.discount import calculate_discount_scheme
from ..services.pdf import generate_po_html, generate_pi_html

import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger("raksha-erp")

router = APIRouter(tags=["orders"])


# ---- Helpers ----

def _get_setting(key, default=""):
    try:
        db = SessionLocal()
        row = db.query(Settings).filter(Settings.key == key).first()
        db.close()
        return row.value if row else default
    except Exception:
        return default


def _get_gst_rate():
    val = _get_setting("default_gst_rate", "18")
    try:
        return float(val)
    except Exception:
        return 18.0


def _order_to_dict(o):
    return {"id": o.id, "sl_no": o.sl_no, "po_no": o.po_no, "po_date": o.po_date,
             "customer_name": o.customer_name or "",
             "billing_site": o.billing_site, "shipping_site": o.shipping_site,
             "no_of_boxes": o.no_of_boxes, "value_excl_gst_freight": o.value_excl_gst_freight,
             "invoice_no": o.invoice_no, "invoice_date": o.invoice_date,
             "invoice_amount_excl_gst": o.invoice_amount_excl_gst,
             "weight_kgs": o.weight_kgs, "freight_rate_per_kg": o.freight_rate_per_kg,
             "transport_charges": o.transport_charges, "invoice_amount": o.invoice_amount,
             "eway_bill_no": o.eway_bill_no, "lr_no": o.lr_no, "entry_date": o.entry_date,
             "credit_note_amount": o.credit_note_amount, "credit_note_no": o.credit_note_no,
             "transporter": o.transporter, "transporter_no": o.transporter_no}


# ---- COGS Order CRUD ----

@router.get("/api/orders")
def list_orders(user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        rows = db.query(Order).order_by(Order.id).all()
        return [_order_to_dict(o) for o in rows]
    finally:
        db.close()


@router.get("/api/orders/{oid}")
def get_order(oid: int, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        o = db.query(Order).filter(Order.id == oid).first()
        if not o:
            raise HTTPException(404, "Order not found")
        return _order_to_dict(o)
    finally:
        db.close()


@router.post("/api/orders")
def create_order(inp: OrderIn, user: User = Depends(require_permission("orders", "create"))):
    db = SessionLocal()
    try:
        max_sl = db.query(func.max(Order.sl_no)).scalar()
        next_sl = (max_sl + 1) if max_sl else 1
        data = inp.dict()
        data["sl_no"] = next_sl
        o = Order(**data)
        db.add(o)
        db.commit()
        db.refresh(o)
        return {"id": o.id, "sl_no": next_sl, "message": "Order created"}
    finally:
        db.close()


@router.put("/api/orders/{oid}")
def update_order(oid: int, inp: OrderIn, user: User = Depends(require_permission("orders", "edit"))):
    db = SessionLocal()
    try:
        o = db.query(Order).filter(Order.id == oid).first()
        if not o:
            raise HTTPException(404, "Not found")
        for k, v in inp.dict().items():
            setattr(o, k, v)
        db.commit()
        return {"message": "Updated"}
    finally:
        db.close()


@router.delete("/api/orders/{oid}")
def delete_order(oid: int, user: User = Depends(require_permission("orders", "delete"))):
    db = SessionLocal()
    try:
        o = db.query(Order).filter(Order.id == oid).first()
        if not o:
            raise HTTPException(404, "Not found")
        db.delete(o)
        db.commit()
        return {"message": "Deleted"}
    finally:
        db.close()


# ---- Proforma Order CRUD ----

@router.get("/api/proforma-orders")
def list_proforma_orders(order_type: str = None, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        query = db.query(ProformaOrder)
        if order_type:
            query = query.filter(ProformaOrder.order_type == order_type)
        rows = query.order_by(ProformaOrder.created_at.desc()).all()
        cust_ids = list(set(o.customer_id for o in rows if o.customer_id))
        cust_map = {}
        if cust_ids:
            custs = db.query(Customer).filter(Customer.id.in_(cust_ids)).all()
            cust_map = {c.id: c.contact_name for c in custs}
        order_ids = [o.id for o in rows]
        all_items = db.query(ProformaOrderItem).filter(ProformaOrderItem.proforma_order_id.in_(order_ids)).all()
        items_count_map = {}
        for item in all_items:
            items_count_map[item.proforma_order_id] = items_count_map.get(item.proforma_order_id, 0) + 1
        out = []
        for o in rows:
            out.append({
                "id": o.id, "pi_no": o.pi_no,
                "pi_date": o.pi_date.isoformat() if o.pi_date else None,
                "customer_name": cust_map.get(o.customer_id, "?"),
                "customer_id": o.customer_id,
                "billing_site": o.billing_site, "shipping_site": o.shipping_site,
                "no_of_boxes": o.no_of_boxes, "total_qty": o.total_qty,
                "value_excl_gst": o.value_excl_gst, "gst_amount": o.gst_amount,
                "total_amount": o.total_amount, "freight_amount": o.freight_amount,
                "payment_status": o.payment_status, "payment_method": o.payment_method,
                "transport_mode": o.transport_mode, "delivery_days": o.delivery_days,
                "notes": o.notes, "terms": o.terms, "order_type": o.order_type,
                "status": o.status or "draft",
                "discount_scheme_applied": o.discount_scheme_applied or 0,
                "discount_percent": o.discount_percent or 0,
                "discount_amount": o.discount_amount or 0,
                "item_count": items_count_map.get(o.id, 0),
                "created_at": o.created_at.isoformat() if o.created_at else None
            })
        return out
    finally:
        db.close()


@router.get("/api/proforma-orders/{oid}")
def get_proforma_order(oid: int, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        o = db.query(ProformaOrder).filter(ProformaOrder.id == oid).first()
        if not o:
            raise HTTPException(404, "Order not found")
        cust = db.query(Customer).filter(Customer.id == o.customer_id).first()
        items = db.query(ProformaOrderItem).filter(ProformaOrderItem.proforma_order_id == o.id).order_by(ProformaOrderItem.sl_no).all()
        product_ids = list(set(item.product_id for item in items if item.product_id))
        products_map = {}
        if product_ids:
            products = db.query(Product).filter(Product.id.in_(product_ids)).all()
            products_map = {p.id: p for p in products}
        items_out = []
        for item in items:
            prod = products_map.get(item.product_id)
            items_out.append({
                "id": item.id, "sl_no": item.sl_no,
                "product_id": item.product_id,
                "product_name": prod.name if prod else "?",
                "part_no": item.part_no, "description": item.description,
                "size": item.size, "category": item.category,
                "qty_boxes": item.qty_boxes, "std_packaging": item.std_packaging,
                "pieces_per_box": item.pieces_per_box, "final_qty": item.final_qty,
                "mrp": item.mrp, "d1": item.d1, "d2": item.d2, "d3": item.d3,
                "d4": item.d4, "d5": item.d5, "cd": item.cd,
                "discount_percent": item.discount_percent,
                "net_rate": item.net_rate, "lock_hinge": item.lock_hinge,
                "basic_amount": item.basic_amount
            })
        return {
            "id": o.id, "pi_no": o.pi_no,
            "pi_date": o.pi_date.isoformat() if o.pi_date else None,
            "customer_id": o.customer_id,
            "customer_name": cust.contact_name if cust else "?",
            "customer_gst": cust.gstin if cust else "",
            "customer_state": cust.state if cust else "",
            "customer_address": cust.billing_address if cust else "",
            "billing_site": o.billing_site, "shipping_site": o.shipping_site,
            "no_of_boxes": o.no_of_boxes, "total_qty": o.total_qty,
            "value_excl_gst": o.value_excl_gst, "gst_amount": o.gst_amount,
            "total_amount": o.total_amount, "freight_amount": o.freight_amount,
            "payment_status": o.payment_status, "payment_method": o.payment_method,
            "transport_mode": o.transport_mode, "delivery_days": o.delivery_days,
            "notes": o.notes, "terms": o.terms, "order_type": o.order_type,
            "status": o.status or "draft",
            "discount_scheme_applied": o.discount_scheme_applied or 0,
            "discount_percent": o.discount_percent or 0,
            "discount_amount": o.discount_amount or 0,
            "items": items_out,
            "created_at": o.created_at.isoformat() if o.created_at else None
        }
    finally:
        db.close()


@router.post("/api/proforma-orders")
def create_proforma_order(inp: ProformaOrderIn, user: User = Depends(require_permission("proforma_orders", "create"))):
    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.id == inp.customer_id).first()
        if not customer:
            raise HTTPException(404, "Customer not found")

        max_retries = 5
        pi_no = None
        for attempt in range(max_retries):
            try:
                max_id = db.query(func.max(ProformaOrder.id)).scalar() or 0
                pi_no = f"RFC/{datetime.now().strftime('%y%m')}-{max_id + 1:03d}"
                existing = db.query(ProformaOrder).filter(ProformaOrder.pi_no == pi_no).first()
                if not existing:
                    break
                db.rollback()
                time.sleep(0.1)
            except Exception:
                if attempt == max_retries - 1:
                    raise
                db.rollback()
                time.sleep(0.1)
        if not pi_no:
            raise HTTPException(500, "Failed to generate unique PI number")

        total_qty = 0
        total_basic = 0
        total_basic_excl_cd = 0

        for item in inp.items:
            net = item.mrp
            for d in [item.d1, item.d2, item.d3, item.d4, item.d5]:
                net = net * (1 - d / 100)
            net_excl_cd = round(net, 2)
            net_incl_cd = round(net * (1 - (item.cd or 0) / 100), 2)
            item.net_rate = net_incl_cd
            item.basic_amount = item.final_qty * net_incl_cd
            total_qty += item.final_qty
            total_basic += item.basic_amount
            total_basic_excl_cd += item.final_qty * net_excl_cd

        discount_pct = 0
        discount_amount = 0
        if inp.discount_scheme_applied:
            discount_pct, additional_pct, slab_info = calculate_discount_scheme(total_basic_excl_cd)
            if discount_pct > 0:
                discount_amount = total_basic_excl_cd * discount_pct / 100

        final_basic = total_basic - discount_amount
        gst_amount = final_basic * _get_gst_rate() / 100
        total_amount = final_basic + gst_amount + inp.freight_amount

        order = ProformaOrder(
            pi_no=pi_no, customer_id=inp.customer_id,
            billing_site=inp.billing_site, shipping_site=inp.shipping_site,
            total_qty=total_qty, no_of_boxes=sum(i.qty_boxes for i in inp.items),
            value_excl_gst=total_basic, gst_amount=gst_amount,
            total_amount=total_amount, freight_amount=inp.freight_amount,
            payment_status=inp.payment_status, payment_method=inp.payment_method,
            transport_mode=inp.transport_mode, delivery_days=inp.delivery_days,
            notes=inp.notes, terms=inp.terms, order_type=inp.order_type,
            discount_scheme_applied=inp.discount_scheme_applied,
            discount_percent=discount_pct, discount_amount=discount_amount
        )
        db.add(order)
        db.flush()

        for idx, item in enumerate(inp.items):
            db.add(ProformaOrderItem(
                proforma_order_id=order.id, sl_no=idx + 1,
                product_id=item.product_id, part_no=item.part_no,
                description=item.description, size=item.size,
                category=item.category, qty_boxes=item.qty_boxes,
                std_packaging=item.std_packaging, pieces_per_box=item.pieces_per_box,
                final_qty=item.final_qty, mrp=item.mrp,
                d1=item.d1, d2=item.d2, d3=item.d3, d4=item.d4, d5=item.d5,
                cd=item.cd, discount_percent=item.discount_percent,
                net_rate=item.net_rate, lock_hinge=item.lock_hinge,
                basic_amount=item.basic_amount
            ))

        db.commit()
        return {"id": order.id, "pi_no": pi_no, "total": total_amount}
    finally:
        db.close()


@router.put("/api/proforma-orders/{oid}")
def update_proforma_order(oid: int, inp: ProformaOrderIn, user: User = Depends(require_permission("proforma_orders", "edit"))):
    db = SessionLocal()
    try:
        order = db.query(ProformaOrder).filter(ProformaOrder.id == oid).first()
        if not order:
            raise HTTPException(404, "Order not found")

        customer = db.query(Customer).filter(Customer.id == inp.customer_id).first()
        if not customer:
            raise HTTPException(404, "Customer not found")

        order.customer_id = inp.customer_id
        order.billing_site = inp.billing_site
        order.shipping_site = inp.shipping_site
        order.freight_amount = inp.freight_amount
        order.payment_status = inp.payment_status
        order.payment_method = inp.payment_method
        order.transport_mode = inp.transport_mode
        order.delivery_days = inp.delivery_days
        order.notes = inp.notes
        order.terms = inp.terms
        order.order_type = inp.order_type
        order.discount_scheme_applied = inp.discount_scheme_applied

        db.query(ProformaOrderItem).filter(ProformaOrderItem.proforma_order_id == oid).delete()

        total_qty = 0
        total_basic = 0
        total_basic_excl_cd = 0
        for idx, item in enumerate(inp.items):
            net = item.mrp
            for d in [item.d1, item.d2, item.d3, item.d4, item.d5]:
                net = net * (1 - d / 100)
            net_excl_cd = round(net, 2)
            net_incl_cd = round(net * (1 - (item.cd or 0) / 100), 2)
            item.net_rate = net_incl_cd
            item.basic_amount = item.final_qty * net_incl_cd
            total_qty += item.final_qty
            total_basic += item.basic_amount
            total_basic_excl_cd += item.final_qty * net_excl_cd
            db.add(ProformaOrderItem(
                proforma_order_id=oid, sl_no=idx + 1,
                product_id=item.product_id, part_no=item.part_no,
                description=item.description, size=item.size,
                category=item.category, qty_boxes=item.qty_boxes,
                std_packaging=item.std_packaging, pieces_per_box=item.pieces_per_box,
                final_qty=item.final_qty, mrp=item.mrp,
                d1=item.d1, d2=item.d2, d3=item.d3, d4=item.d4, d5=item.d5,
                cd=item.cd, discount_percent=item.discount_percent,
                net_rate=item.net_rate, lock_hinge=item.lock_hinge,
                basic_amount=item.basic_amount
            ))

        discount_pct = 0
        discount_amount = 0
        if inp.discount_scheme_applied:
            discount_pct, additional_pct, slab_info = calculate_discount_scheme(total_basic_excl_cd)
            if discount_pct > 0:
                discount_amount = total_basic_excl_cd * discount_pct / 100

        final_basic = total_basic - discount_amount
        gst_amount = final_basic * _get_gst_rate() / 100
        order.total_qty = total_qty
        order.no_of_boxes = sum(i.qty_boxes for i in inp.items)
        order.value_excl_gst = total_basic
        order.discount_percent = discount_pct
        order.discount_amount = discount_amount
        order.gst_amount = gst_amount
        order.total_amount = final_basic + gst_amount + inp.freight_amount
        order.updated_at = datetime.now(timezone.utc)

        db.commit()
        return {"message": "Order updated"}
    finally:
        db.close()


@router.delete("/api/proforma-orders/{oid}")
def delete_proforma_order(oid: int, user: User = Depends(require_permission("proforma_orders", "delete"))):
    db = SessionLocal()
    try:
        order = db.query(ProformaOrder).filter(ProformaOrder.id == oid).first()
        if not order:
            raise HTTPException(404, "Order not found")
        db.query(ProformaOrderItem).filter(ProformaOrderItem.proforma_order_id == oid).delete()
        db.delete(order)
        db.commit()
        return {"message": "Order deleted"}
    finally:
        db.close()



# ---- PDF Generation ----

@router.get("/api/proforma-orders/{oid}/pdf")
def generate_proforma_order_pdf(oid: int, user: User = Depends(require_permission("proforma_orders", "view"))):
    db = SessionLocal()
    try:
        order = db.query(ProformaOrder).filter(ProformaOrder.id == oid).first()
        if not order:
            raise HTTPException(404, "Order not found")
        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        items = db.query(ProformaOrderItem).filter(ProformaOrderItem.proforma_order_id == oid).order_by(ProformaOrderItem.sl_no).all()

        pi_date = order.pi_date.strftime("%d-%b-%Y") if order.pi_date else ""

        billing_site = None
        if order.billing_site:
            try:
                billing_site = db.query(BillingSite).filter(BillingSite.id == int(order.billing_site)).first()
            except (ValueError, TypeError):
                logger.warning("Invalid billing_site ID '%s' for order %s", order.billing_site, order.id)

        if order.order_type == "PO":
            html = generate_po_html(order, customer, items, pi_date, billing_site)
        else:
            html = generate_pi_html(order, customer, items, pi_date, billing_site)

        return HTMLResponse(content=html)
    finally:
        db.close()


# ---- GP Calculation ----

@router.get("/api/proforma-orders/{oid}/gp")
def calculate_gp(oid: int, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        order = db.query(ProformaOrder).filter(ProformaOrder.id == oid).first()
        if not order:
            raise HTTPException(404, "Order not found")
        items = db.query(ProformaOrderItem).filter(ProformaOrderItem.proforma_order_id == oid).all()

        purchase_total = 0
        for item in items:
            pr = db.query(PurchaseRate).filter(PurchaseRate.product_id == item.product_id).order_by(PurchaseRate.effective_date.desc()).first()
            if pr:
                purchase_total += (item.final_qty or 0) * pr.rate

        sales_value = order.value_excl_gst or 0
        transport = order.transport_cost or 0
        gp = sales_value - purchase_total - transport
        gst_component = order.gst_amount or 0
        np_val = gp - gst_component

        order.purchase_total = purchase_total
        order.gross_profit = gp
        order.net_profit = np_val
        db.commit()

        return {
            "sales_value": sales_value, "purchase_total": purchase_total,
            "transport_cost": transport, "gross_profit": gp,
            "gst_amount": gst_component, "net_profit": np_val,
            "gp_percent": round(gp / sales_value * 100, 2) if sales_value else 0
        }
    finally:
        db.close()


# ---- Transport Update ----

@router.put("/api/proforma-orders/{oid}/transport")
def update_transport(oid: int, inp: TransportUpdateIn, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        order = db.query(ProformaOrder).filter(ProformaOrder.id == oid).first()
        if not order:
            raise HTTPException(404, "Order not found")
        order.transport_cost = inp.transport_cost
        db.commit()
        return {"message": "Transport updated"}
    finally:
        db.close()


# ---- Status Update ----

ORDER_STATUS_TRANSITIONS = {
    "draft": ["confirmed"],
    "confirmed": ["po_created", "draft"],
    "po_created": ["transport_pending", "confirmed"],
    "transport_pending": ["transport_finalized", "po_created"],
    "transport_finalized": ["billing", "transport_pending"],
    "billing": ["completed", "transport_finalized"],
    "completed": [],
}


@router.put("/api/proforma-orders/{oid}/status")
def update_order_status(oid: int, inp: OrderStatusIn, user: User = Depends(require_permission("proforma_orders", "edit"))):
    db = SessionLocal()
    try:
        order = db.query(ProformaOrder).filter(ProformaOrder.id == oid).first()
        if not order:
            raise HTTPException(404, "Order not found")
        new_status = inp.status
        valid_statuses = ["draft", "confirmed", "po_created", "transport_pending", "transport_finalized", "billing", "completed"]
        if new_status not in valid_statuses:
            raise HTTPException(400, f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        current_status = order.status or "draft"
        allowed_next = ORDER_STATUS_TRANSITIONS.get(current_status, [])
        if new_status not in allowed_next:
            raise HTTPException(400, f"Cannot transition from '{current_status}' to '{new_status}'. Allowed: {', '.join(allowed_next) or 'none (terminal)'}")
        order.status = new_status
        order.updated_at = datetime.now(timezone.utc)
        audit_log(user, "order_status_change", resource="proforma_order", resource_id=oid,
                  details=f"Status: {current_status} → {new_status}")
        db.commit()
        return {"message": f"Order status updated to {new_status}"}
    finally:
        db.close()
