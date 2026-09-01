from fastapi import APIRouter, Depends, HTTPException
from models import Customer, Sale, ProformaOrder, User
from schemas import CustomerIn
from auth import get_current_user, require_permission
from database import SessionLocal

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("")
def list_customers(user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        rows = db.query(Customer).all()
        return [{"id": c.id, "customer_id": c.customer_id, "name": c.name or "", "gstin": c.gstin,
                 "billing_address": c.billing_address, "shipping_address": c.shipping_address,
                 "state": c.state, "district": c.district, "city": c.city, "pincode": c.pincode,
                 "contact_name": c.contact_name, "contact_number": c.contact_number, "contact_email": c.contact_email,
                 "exec_code": c.exec_code, "exec_name": c.exec_name, "exec_number": c.exec_number, "exec_email": c.exec_email,
                 "blacklisted": c.blacklisted}
                for c in rows]
    finally:
        db.close()


@router.post("")
def create_customer(inp: CustomerIn, user: User = Depends(require_permission("customers", "create"))):
    db = SessionLocal()
    try:
        c = Customer(**inp.dict())
        db.add(c)
        db.commit()
        db.refresh(c)
        return {"id": c.id, "message": "Customer created"}
    finally:
        db.close()


@router.put("/{cid}")
def update_customer(cid: int, inp: CustomerIn, user: User = Depends(require_permission("customers", "edit"))):
    db = SessionLocal()
    try:
        c = db.query(Customer).filter(Customer.id == cid).first()
        if not c:
            raise HTTPException(404, "Not found")
        for k, v in inp.dict().items():
            setattr(c, k, v)
        db.commit()
        return {"message": "Updated"}
    finally:
        db.close()


@router.delete("/{cid}")
def delete_customer(cid: int, user: User = Depends(require_permission("customers", "delete"))):
    db = SessionLocal()
    try:
        c = db.query(Customer).filter(Customer.id == cid).first()
        if not c:
            raise HTTPException(404, "Not found")
        db.query(Sale).filter(Sale.customer_id == c.id).update({"customer_id": None})
        db.delete(c)
        db.commit()
        return {"message": "Deleted"}
    finally:
        db.close()


@router.delete("/by-id/{customer_id}")
def delete_customer_by_customer_id(customer_id: str, user: User = Depends(require_permission("customers", "delete"))):
    db = SessionLocal()
    try:
        c = db.query(Customer).filter(Customer.customer_id == customer_id).first()
        if not c:
            raise HTTPException(404, "Not found")
        db.query(Sale).filter(Sale.customer_id == c.id).update({"customer_id": None})
        db.delete(c)
        db.commit()
        return {"message": f"Deleted {customer_id}"}
    finally:
        db.close()


@router.post("/dedup")
def dedup_customers(user: User = Depends(require_permission("customers", "edit"))):
    db = SessionLocal()
    try:
        customers = db.query(Customer).order_by(Customer.id).all()
        seen = {}
        removed = 0
        for c in customers:
            key = (c.name.strip().lower(),) if c.name and c.name.strip() else (c.customer_id.strip(),)
            if key in seen:
                keep = seen[key]
                for sale in db.query(Sale).filter(Sale.customer_id == c.id).all():
                    sale.customer_id = keep.id
                for po in db.query(ProformaOrder).filter(ProformaOrder.customer_id == c.id).all():
                    po.customer_id = keep.id
                db.delete(c)
                removed += 1
            else:
                seen[key] = c
        db.commit()
        return {"removed": removed, "remaining": len(seen), "message": f"Removed {removed} duplicate customers"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Dedup failed: {str(e)}")
    finally:
        db.close()
