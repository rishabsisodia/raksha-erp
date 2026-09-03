from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from datetime import date
from ..models import Product, Pricing, PurchaseRate, Sale, ProformaOrderItem, SaleItem
from ..schemas import ProductIn, PricingIn, PurchaseRateIn, PurchaseRateUpdateIn, BulkPurchaseRateIn
from ..auth import get_current_user, require_permission
from ..database import SessionLocal
from ..models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["products"])

PART_NO_CSV = [
    ("FRP01101-GRY", "Raksha FRP Manhole Cover 10x10 - 5 Ton Grey"),
    ("FRP01103-GRY", "Raksha FRP Manhole Cover 12x12 - 5 Ton Grey"),
    ("FRP01106-GRY", "Raksha FRP Manhole Cover 15x15 - 5 Ton Grey"),
    ("FRP01109-GRY", "Raksha FRP Manhole Cover 18x18 - 5 Ton Grey"),
    ("FRP01112-GRY", "Raksha FRP Manhole Cover 21x21 - 5 Ton Grey"),
    ("FRP01115-GRY", "Raksha FRP Manhole Cover 24x24 - 5 Ton Grey"),
    ("FRP01117-GRY", "Raksha FRP Manhole Cover 26x26 - 5 Ton Grey"),
    ("FRP01119-GRY", "Raksha FRP Manhole Cover 28x28 - 5 Ton Grey"),
    ("FRP01121-GRY", "Raksha FRP Manhole Cover 30x30 - 5 Ton Grey"),
    ("FRP01127-GRY", "Raksha FRP Manhole Cover 36x36 - 5 Ton Grey"),
    ("FRP04106-GRY", "Raksha FRP Manhole Cover 12x18 - 5 Ton Grey"),
    ("FRP04112-GRY", "Raksha FRP Manhole Cover 12x24 - 5 Ton Grey"),
    ("FRP10106-GRY", "Raksha FRP Manhole Cover 18x24 - 5 Ton Grey"),
    ("FRP01101-WH", "Raksha FRP Manhole Cover 10x10 - 5 Ton White"),
    ("FRP01103-WH", "Raksha FRP Manhole Cover 12x12 - 5 Ton White"),
    ("FRP01106-WH", "Raksha FRP Manhole Cover 15x15 - 5 Ton White"),
    ("FRP01109-WH", "Raksha FRP Manhole Cover 18x18 - 5 Ton White"),
    ("FRP01112-WH", "Raksha FRP Manhole Cover 21x21 - 5 Ton White"),
    ("FRP01115-WH", "Raksha FRP Manhole Cover 24x24 - 5 Ton White"),
    ("FRP01117-WH", "Raksha FRP Manhole Cover 26x26 - 5 Ton White"),
    ("FRP01119-WH", "Raksha FRP Manhole Cover 28x28 - 5 Ton White"),
    ("FRP01121-WH", "Raksha FRP Manhole Cover 30x30 - 5 Ton White"),
    ("FRP01127-WH", "Raksha FRP Manhole Cover 36x36 - 5 Ton White"),
    ("FRP04106-WH", "Raksha FRP Manhole Cover 12x18 - 5 Ton White"),
    ("FRP04112-WH", "Raksha FRP Manhole Cover 12x24 - 5 Ton White"),
    ("FRP10106-WH", "Raksha FRP Manhole Cover 18x24 - 5 Ton White"),
    ("FRP01112-GRYL", "Raksha FRP Manhole Cover 21x21 - 5 Ton Grey (with Lock)"),
    ("FRP01115-GRYL", "Raksha FRP Manhole Cover 24x24 - 5 Ton Grey (with Lock)"),
    ("FRP01117-GRYL", "Raksha FRP Manhole Cover 26x26 - 5 Ton Grey (with Lock)"),
    ("FRP01119-GRYL", "Raksha FRP Manhole Cover 28x28 - 5 Ton Grey (with Lock)"),
    ("FRP01121-GRYL", "Raksha FRP Manhole Cover 30x30 - 5 Ton Grey (with Lock)"),
    ("FRP01127-GRYL", "Raksha FRP Manhole Cover 36x36 - 5 Ton Grey (with Lock)"),
    ("FRP01112-WHL", "Raksha FRP Manhole Cover 21x21 - 5 Ton White (with Lock)"),
    ("FRP01115-WHL", "Raksha FRP Manhole Cover 24x24 - 5 Ton White (with Lock)"),
    ("FRP01117-WHL", "Raksha FRP Manhole Cover 26x26 - 5 Ton White (with Lock)"),
    ("FRP01119-WHL", "Raksha FRP Manhole Cover 28x28 - 5 Ton White (with Lock)"),
    ("FRP01121-WHL", "Raksha FRP Manhole Cover 30x30 - 5 Ton White (with Lock)"),
    ("FRP01127-WHL", "Raksha FRP Manhole Cover 36x36 - 5 Ton White (with Lock)"),
    ("FRP01115-GRYH", "Raksha FRP Manhole Cover 24x24 - 5 Ton Grey (Double Hinges)"),
    ("FRP01115-WHH", "Raksha FRP Manhole Cover 24x24 - 5 Ton White (Double Hinges)"),
    ("FRP01115-GRY/H&L", "Raksha FRP Manhole Cover 24x24 - 5 Ton Grey (Double Hinges & Lock)"),
    ("FRP01115-WH/H&L", "Raksha FRP Manhole Cover 24x24 - 5 Ton White (Double Hinges & Lock)"),
    ("FRP01209-GRY", "Raksha FRP Manhole Cover 18x18 - 10 Ton Grey"),
    ("FRP01215-GRY", "Raksha FRP Manhole Cover 24x24 - 10 Ton Grey"),
    ("FRP01219-GRY", "Raksha FRP Manhole Cover 28x28 - 10 Ton Grey"),
    ("FRP01221-GRY", "Raksha FRP Manhole Cover 30x30 - 10 Ton Grey"),
    ("FRP01233-GRY", "Raksha FRP Manhole Cover 42x42 - 10 Ton Grey"),
    ("FRP01209-WH", "Raksha FRP Manhole Cover 18x18 - 10 Ton White"),
    ("FRP01215-WH", "Raksha FRP Manhole Cover 24x24 - 10 Ton White"),
    ("FRP01219-WH", "Raksha FRP Manhole Cover 28x28 - 10 Ton White"),
    ("FRP01221-WH", "Raksha FRP Manhole Cover 30x30 - 10 Ton White"),
    ("FRP01233-WH", "Raksha FRP Manhole Cover 42x42 - 10 Ton White"),
    ("RGC00001-GRY", "Raksha FRP Gully Cover 10x10 - Grey"),
    ("RGC00002-GRY", "Raksha FRP Gully Cover 12x12 - Grey"),
    ("RGC00003-GRY", "Raksha FRP Gully Cover 15x15 - Grey"),
    ("RGC00004-GRY", "Raksha FRP Gully Cover 18x18 - Grey"),
    ("RGC00005-GRY", "Raksha FRP Gully Cover 24x24 - Grey"),
    ("RGC00001-WH", "Raksha FRP Gully Cover 10x10 - White"),
    ("RGC00002-WH", "Raksha FRP Gully Cover 12x12 - White"),
    ("RGC00003-WH", "Raksha FRP Gully Cover 15x15 - White"),
    ("RGC00004-WH", "Raksha FRP Gully Cover 18x18 - White"),
    ("RGC00005-WH", "Raksha FRP Gully Cover 24x24 - White"),
]

CSV_ORDER = {pn: i for i, (pn, _) in enumerate(PART_NO_CSV)}


# ---- PRODUCTS ----

@router.get("/api/products")
def list_products(user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        rows = db.query(Product).all()
        out = []
        for p in rows:
            mrp = p.pricing.mrp if p.pricing else 0
            out.append({
                "id": p.id, "part_no": p.part_no, "name": p.name, "category": p.category,
                "size": p.size, "load_rating": p.load_rating,
                "material": p.material, "color": p.color, "unit": p.unit, "hsn_code": p.hsn_code,
                "mrp": mrp
            })
        out.sort(key=lambda p: CSV_ORDER.get(p["part_no"], 999))
        return out
    finally:
        db.close()


@router.post("/api/products")
def create_product(inp: ProductIn, user: User = Depends(require_permission("products", "create"))):
    db = SessionLocal()
    try:
        p = Product(**inp.dict())
        db.add(p)
        db.commit()
        db.refresh(p)
        db.add(Pricing(product_id=p.id))
        db.commit()
        return {"id": p.id, "message": "Product created"}
    finally:
        db.close()


@router.put("/api/products/{pid}")
def update_product(pid: int, inp: ProductIn, user: User = Depends(require_permission("products", "edit"))):
    db = SessionLocal()
    try:
        p = db.query(Product).filter(Product.id == pid).first()
        if not p:
            raise HTTPException(404, "Not found")
        for k, v in inp.dict().items():
            setattr(p, k, v)
        db.commit()
        return {"message": "Updated"}
    finally:
        db.close()


@router.delete("/api/products/{pid}")
def delete_product(pid: int, user: User = Depends(require_permission("products", "delete"))):
    db = SessionLocal()
    try:
        p = db.query(Product).filter(Product.id == pid).first()
        if not p:
            raise HTTPException(404, "Not found")
        db.query(Pricing).filter(Pricing.product_id == pid).delete()
        db.delete(p)
        db.commit()
        return {"message": "Deleted"}
    finally:
        db.close()


# ---- PRICING ----

@router.get("/api/products/{pid}/pricing")
def get_pricing(pid: int, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        pr = db.query(Pricing).filter(Pricing.product_id == pid).first()
        if not pr:
            raise HTTPException(404, "Not found")
        return {
            "raw_material_cost": pr.raw_material_cost,
            "labor_cost": pr.labor_cost,
            "overhead_cost": pr.overhead_cost,
            "packing_cost": pr.packing_cost,
            "total_cost": pr.total_cost,
            "profit_margin": pr.profit_margin,
            "mrp": pr.mrp,
            "dealer_price": pr.dealer_price,
            "distributor_price": pr.distributor_price,
            "gst_rate": pr.gst_rate
        }
    finally:
        db.close()


@router.put("/api/products/{pid}/pricing")
def update_pricing(pid: int, inp: PricingIn, user: User = Depends(require_permission("products", "edit"))):
    db = SessionLocal()
    try:
        pr = db.query(Pricing).filter(Pricing.product_id == pid).first()
        if not pr:
            pr = Pricing(product_id=pid)
            db.add(pr)
        pr.raw_material_cost = inp.raw_material_cost
        pr.mrp = inp.mrp
        pr.gst_rate = inp.gst_rate
        pr.labor_cost = inp.labor_cost
        pr.overhead_cost = inp.overhead_cost
        pr.packing_cost = inp.packing_cost
        pr.profit_margin = inp.profit_margin
        total = inp.raw_material_cost + inp.labor_cost + inp.overhead_cost + inp.packing_cost
        pr.total_cost = total
        db.commit()
        return {"message": "Updated", "mrp": inp.mrp}
    finally:
        db.close()


# ---- PRODUCT DETAILS ----

@router.get("/api/products/{pid}/details")
def get_product_details(pid: int, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        p = db.query(Product).filter(Product.id == pid).first()
        if not p:
            raise HTTPException(404, "Product not found")
        pr = db.query(Pricing).filter(Pricing.product_id == pid).first()
        return {
            "id": p.id, "name": p.name, "category": p.category,
            "size": p.size, "part_no": p.part_no,
            "mrp": pr.mrp if pr else 0,
            "pieces_per_box": p.pieces_per_box or 1,
            "std_packaging": p.std_packaging or 1
        }
    finally:
        db.close()


# ---- PURCHASE RATES ----

@router.get("/api/purchase-rates")
def list_purchase_rates(user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        rates = db.query(PurchaseRate).all()
        product_ids = list(set(r.product_id for r in rates if r.product_id))
        product_map = {}
        if product_ids:
            products = db.query(Product).filter(Product.id.in_(product_ids)).all()
            product_map = {p.id: p for p in products}
        result = []
        for r in rates:
            p = product_map.get(r.product_id)
            result.append({
                "id": r.id, "product_id": r.product_id,
                "product_name": p.name if p else "", "part_no": p.part_no if p else "",
                "category": p.category if p else "", "size": p.size if p else "",
                "rate": r.rate, "supplier": r.supplier,
                "effective_date": r.effective_date.isoformat() if r.effective_date else ""
            })
        return result
    finally:
        db.close()


@router.post("/api/purchase-rates")
def create_purchase_rate(inp: PurchaseRateIn, user: User = Depends(require_permission("products", "edit"))):
    db = SessionLocal()
    try:
        pr = PurchaseRate(
            product_id=inp.product_id, rate=inp.rate,
            supplier=inp.supplier,
            effective_date=date.fromisoformat(inp.effective_date) if inp.effective_date else date.today()
        )
        db.add(pr)
        db.commit()
        return {"id": pr.id, "message": "Purchase rate added"}
    finally:
        db.close()


@router.put("/api/purchase-rates/{prid}")
def update_purchase_rate(prid: int, inp: PurchaseRateUpdateIn, user: User = Depends(require_permission("products", "edit"))):
    db = SessionLocal()
    try:
        pr = db.query(PurchaseRate).filter(PurchaseRate.id == prid).first()
        if not pr:
            raise HTTPException(404, "Not found")
        pr.rate = inp.rate
        pr.supplier = inp.supplier
        if inp.effective_date:
            pr.effective_date = date.fromisoformat(inp.effective_date)
        db.commit()
        return {"message": "Updated"}
    finally:
        db.close()


@router.delete("/api/purchase-rates/{prid}")
def delete_purchase_rate(prid: int, user: User = Depends(require_permission("products", "edit"))):
    db = SessionLocal()
    try:
        pr = db.query(PurchaseRate).filter(PurchaseRate.id == prid).first()
        if not pr:
            raise HTTPException(404, "Not found")
        db.delete(pr)
        db.commit()
        return {"message": "Deleted"}
    finally:
        db.close()


@router.post("/api/purchase-rates/bulk")
def bulk_create_purchase_rates(inp: BulkPurchaseRateIn, user: User = Depends(require_permission("products", "edit"))):
    db = SessionLocal()
    try:
        rates = inp.rates
        created = 0
        for r in rates:
            pr = PurchaseRate(
                product_id=r.product_id, rate=r.rate,
                supplier=r.supplier,
                effective_date=date.fromisoformat(r.effective_date) if r.effective_date else date.today()
            )
            db.add(pr)
            created += 1
        db.commit()
        return {"message": f"{created} rates added", "count": created}
    finally:
        db.close()


# ---- PRODUCT DEDUP ----

@router.post("/api/products/dedup")
def dedup_products(user: User = Depends(require_permission("products", "edit"))):
    db = SessionLocal()
    try:
        products = db.query(Product).order_by(Product.id).all()
        seen = {}
        removed = 0
        for p in products:
            key = (p.part_no.strip(), ) if p.part_no and p.part_no.strip() else (p.name.strip().lower(), )
            if key in seen:
                keep = seen[key]
                if p.pricing and not keep.pricing:
                    p.pricing.product_id = keep.id
                    keep.pricing = p.pricing
                    p.pricing = None
                elif p.pricing and keep.pricing:
                    db.delete(p.pricing)
                for model in [Sale, ProformaOrderItem, SaleItem, PurchaseRate]:
                    for obj in db.query(model).filter(model.product_id == p.id).all():
                        obj.product_id = keep.id
                for tbl in ["stock", "stock_entries"]:
                    try:
                        result = db.execute(text(f"DELETE FROM {tbl} WHERE product_id = :pid"), {"pid": p.id})
                        logger.info(f"Dedup: deleted {result.rowcount} rows from {tbl} for product {p.id}")
                    except Exception as ex:
                        logger.warning(f"Dedup: could not delete from {tbl} for product {p.id}: {ex}")
                db.delete(p)
                removed += 1
            else:
                seen[key] = p
        db.commit()
        return {"removed": removed, "remaining": len(seen), "message": f"Removed {removed} duplicate products"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Dedup failed: {str(e)}")
    finally:
        db.close()
