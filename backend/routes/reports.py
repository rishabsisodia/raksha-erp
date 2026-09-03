from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from datetime import datetime
from ..models import Sale, SaleItem, Order, ProformaOrder, Expense, Settings, BillingSite, Customer, Product
from ..schemas import SettingsUpdateIn
from ..auth import get_current_user, require_permission
from ..database import SessionLocal
from ..services.discount import DISCOUNT_SCHEME, calculate_discount_scheme
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reports"])


def get_setting(key, default=""):
    try:
        db = SessionLocal()
        row = db.query(Settings).filter(Settings.key == key).first()
        db.close()
        return row.value if row else default
    except Exception:
        return default


def get_gst_rate():
    val = get_setting("default_gst_rate", "18")
    try:
        return float(val)
    except Exception:
        return 18.0


# ---- REPORTS ----
@router.get("/api/reports/profit-loss")
def profit_loss(start_date: str = None, end_date: str = None, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        sales_q = db.query(Sale)
        expenses_q = db.query(Expense)
        orders_q = db.query(Order)

        if start_date:
            try:
                sd = datetime.strptime(start_date, "%Y-%m-%d")
                sales_q = sales_q.filter(Sale.sale_date >= sd)
                expenses_q = expenses_q.filter(Expense.expense_date >= sd)
                orders_q = orders_q.filter(Order.entry_date >= sd.strftime("%Y-%m-%d"))
            except Exception:
                logger.warning("Invalid start_date for P&L: %s", start_date)
        if end_date:
            try:
                ed = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                sales_q = sales_q.filter(Sale.sale_date <= ed)
                expenses_q = expenses_q.filter(Expense.expense_date <= ed)
                orders_q = orders_q.filter(Order.entry_date <= ed.strftime("%Y-%m-%d"))
            except Exception:
                logger.warning("Invalid end_date for P&L: %s", end_date)

        sales = sales_q.all()
        expenses = expenses_q.all()
        orders = orders_q.all()

        # Revenue from Sales
        sale_revenue = sum(s.invoice_value or s.total_amount or 0 for s in sales)
        units = sum(s.quantity or 0 for s in sales)
        gst = sum((s.cgst_amount or 0) + (s.sgst_amount or 0) for s in sales)
        gp_from_sales = sum(s.gp or 0 for s in sales)
        gp_values = [s.gp_percent for s in sales if s.gp_percent and s.gp_percent > 0]
        gp_avg = sum(gp_values) / len(gp_values) if gp_values else 0

        # Freight from sales (rate per kg * weight = total freight cost)
        sale_freight = sum((s.freight_amount or 0) * (s.weight_kgs or 0) for s in sales)

        # COGS from Orders (cost of goods)
        order_cogs = sum(o.value_excl_gst_freight or 0 for o in orders)
        order_freight_cost = sum(o.transport_charges or 0 for o in orders)
        order_invoice_total = sum(o.invoice_amount or 0 for o in orders)
        order_boxes = sum(o.no_of_boxes or 0 for o in orders)
        order_weight = sum(o.weight_kgs or 0 for o in orders)
        order_credit_notes = sum(o.credit_note_amount or 0 for o in orders)

        # Total revenue = sales invoice values (which may or may not include freight)
        total_revenue = sale_revenue

        # Total COGS (order cost + transport)
        total_cogs = order_cogs + order_freight_cost

        exp_by_cat = {}
        for e in expenses:
            exp_by_cat[e.category] = exp_by_cat.get(e.category, 0) + e.amount
        total_opex = sum(exp_by_cat.values())

        # Gross Profit = Revenue - COGS - Credit Notes
        gross_profit = total_revenue - total_cogs - order_credit_notes
        gross_margin = (gross_profit / total_revenue * 100) if total_revenue else 0

        ebitda = gross_profit - total_opex
        tax_rate = float(get_setting("tax_rate", "25"))
        tax = ebitda * tax_rate / 100 if ebitda > 0 else 0
        pat = ebitda - tax

        return {
            "total_revenue": total_revenue,
            "sale_revenue": sale_revenue, "sale_freight": sale_freight,
            "total_cogs": total_cogs,
            "order_cogs": order_cogs, "order_freight_cost": order_freight_cost,
            "order_invoice_total": order_invoice_total,
            "order_boxes": order_boxes, "order_weight": order_weight,
            "order_credit_notes": order_credit_notes,
            "gst": gst, "units": units,
            "gross_profit": gross_profit, "gross_margin": gross_margin,
            "gp_from_sales": gp_from_sales, "gp_avg": gp_avg,
            "expenses": exp_by_cat, "total_opex": total_opex,
            "ebitda": ebitda, "ebitda_margin": (ebitda / total_revenue * 100) if total_revenue else 0,
            "tax_rate": float(get_setting("tax_rate", "25")), "tax": tax, "pat": pat,
            "total_orders": len(orders), "total_sales": len(sales),
        }
    finally:
        db.close()


# ---- DASHBOARD ----
@router.get("/api/dashboard")
def dashboard(user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        # Use SQL aggregations instead of loading all records
        revenue = db.query(func.coalesce(func.sum(Sale.invoice_value), 0)).scalar() or 0
        # Fallback to total_amount if invoice_value is not set
        if revenue == 0:
            revenue = db.query(func.coalesce(func.sum(Sale.total_amount), 0)).scalar() or 0
        
        freight = db.query(func.coalesce(func.sum(Sale.freight_amount * Sale.weight_kgs), 0)).scalar() or 0
        gp_total = db.query(func.coalesce(func.sum(Sale.gp), 0)).scalar() or 0
        pending = db.query(func.coalesce(func.sum(Sale.total_amount), 0)).filter(Sale.payment_status == "Pending").scalar() or 0
        
        total_order_value = db.query(func.coalesce(func.sum(Order.invoice_amount), 0)).scalar() or 0
        total_order_cost = db.query(func.coalesce(func.sum(Order.value_excl_gst_freight), 0)).scalar() or 0

        lr_in_transit = db.query(func.count(Sale.id)).filter(Sale.lr_tracking_status == "In Transit").scalar() or 0
        lr_delivered = db.query(func.count(Sale.id)).filter(Sale.lr_tracking_status == "Delivered").scalar() or 0
        lr_delayed = db.query(func.count(Sale.id)).filter(Sale.lr_tracking_status == "Delayed").scalar() or 0
        lr_pending = db.query(func.count(Sale.id)).filter(Sale.lr_no.isnot(None), Sale.lr_no != "", Sale.lr_tracking_status.is_(None)).scalar() or 0

        # Recent sales with batch-loaded customers
        recent_sales_raw = db.query(Sale).order_by(Sale.id.desc()).limit(5).all()
        customer_ids = list(set(s.customer_id for s in recent_sales_raw if s.customer_id))
        customers_map = {}
        if customer_ids:
            customers = db.query(Customer).filter(Customer.id.in_(customer_ids)).all()
            customers_map = {c.id: c for c in customers}
        
        recent_sales = []
        for s in recent_sales_raw:
            try:
                cust_name = ""
                if s.customer_id and s.customer_id in customers_map:
                    cust_name = customers_map[s.customer_id].contact_name or ""
                dt_str = ""
                if s.sale_date:
                    if hasattr(s.sale_date, 'strftime'):
                        dt_str = s.sale_date.strftime("%d %b %Y")
                    else:
                        dt_str = str(s.sale_date)[:10]
                recent_sales.append({
                    "id": s.id, "invoice": s.invoice_no or "",
                    "customer": s.party_name or cust_name or "",
                    "amount": s.total_amount or 0, "status": s.payment_status or "",
                    "date": dt_str
                })
            except Exception as ex:
                logger.warning(f"Dashboard recent sale {s.id} failed: {ex}")
                continue

        recent_orders = []
        for o in db.query(Order).order_by(Order.id.desc()).limit(5).all():
            recent_orders.append({
                "id": o.id, "sl_no": o.sl_no or 0,
                "po_no": o.po_no or "", "customer_name": o.customer_name or "",
                "billing_site": o.billing_site or "",
                "invoice_no": o.invoice_no or "",
                "invoice_amount": o.invoice_amount or 0,
                "entry_date": o.entry_date or ""
            })

        # Monthly revenue chart using SQL
        monthly_revenue = {}
        try:
            monthly_rows = db.execute(text("""
                SELECT substr(sale_date::text, 1, 7) as month, 
                       COALESCE(sum(total_amount), 0) as total
                FROM sales 
                WHERE sale_date IS NOT NULL 
                GROUP BY month 
                ORDER BY month
            """)).fetchall()
            for row in monthly_rows:
                monthly_revenue[row[0]] = row[1]
        except Exception as e:
            logger.error("Dashboard monthly revenue query failed: %s", e)
        sorted_months = sorted(monthly_revenue.keys())[-12:]
        revenue_chart = {"labels": sorted_months, "data": [monthly_revenue[m] for m in sorted_months]}

        party_revenue = {}
        party_rows = db.query(
            Sale.party_name,
            func.coalesce(func.sum(Sale.total_amount), 0).label("total")
        ).filter(Sale.party_name.isnot(None)).group_by(Sale.party_name).order_by(func.sum(Sale.total_amount).desc()).limit(8).all()
        for row in party_rows:
            party_revenue[row.party_name] = row.total
        party_chart = {"labels": list(party_revenue.keys()), "data": list(party_revenue.values())}

        location_revenue = {}
        loc_rows = db.query(
            Sale.location,
            func.coalesce(func.sum(Sale.total_amount), 0).label("total")
        ).filter(Sale.location.isnot(None)).group_by(Sale.location).order_by(func.sum(Sale.total_amount).desc()).limit(8).all()
        for row in loc_rows:
            location_revenue[row.location] = row.total
        location_chart = {"labels": list(location_revenue.keys()), "data": list(location_revenue.values())}

        # Category breakdown
        category_counts = {}
        cat_rows = db.query(
            Product.category,
            func.count(Product.id).label("cnt")
        ).filter(Product.category.isnot(None), Product.category != "").group_by(Product.category).all()
        for row in cat_rows:
            category_counts[row.category] = row.cnt

        return {
            "total_products": db.query(Product).count(),
            "total_customers": db.query(Customer).count(),
            "total_orders": db.query(Order).count(),
            "total_sales": db.query(Sale).count(),
            "revenue": revenue,
            "freight": freight,
            "gp_total": gp_total,
            "pending": pending,
            "total_order_value": total_order_value,
            "total_order_cost": total_order_cost,
            "recent_sales": recent_sales,
            "recent_orders": recent_orders,
            "lr_in_transit": lr_in_transit,
            "lr_delivered": lr_delivered,
            "lr_delayed": lr_delayed,
            "lr_pending": lr_pending,
            "revenue_chart": revenue_chart,
            "party_chart": party_chart,
            "location_chart": location_chart,
            "category_counts": category_counts,
        }
    except Exception as e:
        return {"error": str(e), "total_products": 0, "total_customers": 0,
                "total_orders": 0, "total_sales": 0, "revenue": 0, "freight": 0,
                "gp_total": 0, "pending": 0, "total_order_value": 0,
                "total_order_cost": 0, "recent_sales": [], "recent_orders": [],
                "lr_in_transit": 0, "lr_delivered": 0, "lr_delayed": 0, "lr_pending": 0,
                "revenue_chart": {"labels": [], "data": []},
                "party_chart": {"labels": [], "data": []},
                "location_chart": {"labels": [], "data": []}}
    finally:
        db.close()


# ---- BILLING SITES ----
@router.get("/api/billing-sites")
def list_billing_sites(user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        sites = db.query(BillingSite).order_by(BillingSite.name).all()
        return [{"id": s.id, "name": s.name, "address": s.address, "phone": s.phone,
                 "email": s.email, "website": s.website, "gstin": s.gstin,
                 "state_code": s.state_code, "pan": s.pan} for s in sites]
    finally:
        db.close()


# ---- SETTINGS ----
@router.get("/api/settings")
def get_settings(user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        rows = db.query(Settings).all()
        return {s.key: s.value for s in rows}
    finally:
        db.close()


@router.put("/api/settings")
def update_settings(body: SettingsUpdateIn, user=Depends(require_permission("settings", "edit"))):
    db = SessionLocal()
    try:
        for k, v in body.settings.items():
            row = db.query(Settings).filter(Settings.key == k).first()
            if row:
                row.value = str(v)
            else:
                db.add(Settings(key=k, value=str(v)))
        db.commit()
        return {"message": "Settings updated"}
    finally:
        db.close()


# ---- DISCOUNT SCHEME ----
@router.get("/api/discount-scheme")
def get_discount_scheme(user=Depends(get_current_user)):
    return DISCOUNT_SCHEME

@router.get("/api/discount-calculate/{basic_value}")
def get_discount_calculate(basic_value: float, user=Depends(get_current_user)):
    total_pct, additional_pct, slab_info = calculate_discount_scheme(basic_value)
    discount_amount = basic_value * total_pct / 100 if total_pct > 0 else 0
    return {
        "basic_value": basic_value,
        "total_discount_percent": total_pct,
        "additional_percent": additional_pct,
        "slab_info": slab_info,
        "discount_amount": round(discount_amount, 2),
        "final_value": round(basic_value - discount_amount, 2)
    }


# ---- DB INFO ----
@router.get("/api/db-info")
def db_info(user=Depends(require_permission("settings", "view"))):
    return {
        "has_database_url_key": "DATABASE_URL" in os.environ,
        "env_key_count": len(os.environ)
    }
