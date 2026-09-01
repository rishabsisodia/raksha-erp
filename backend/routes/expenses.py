from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from models import Expense
from schemas import ExpenseIn
from auth import get_current_user, require_permission
from database import SessionLocal
from models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/expenses", tags=["expenses"])


@router.get("")
def list_expenses(user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        rows = db.query(Expense).order_by(Expense.expense_date.desc()).all()
        return [{"id": e.id, "category": e.category, "description": e.description,
                 "amount": e.amount, "vendor": e.vendor,
                 "expense_date": e.expense_date.isoformat() if e.expense_date else None}
                for e in rows]
    finally:
        db.close()


@router.get("/{eid}")
def get_expense(eid: int, user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        e = db.query(Expense).filter(Expense.id == eid).first()
        if not e:
            raise HTTPException(404, "Expense not found")
        return {"id": e.id, "category": e.category, "description": e.description,
                "amount": e.amount, "vendor": e.vendor,
                "expense_date": e.expense_date.isoformat() if e.expense_date else None}
    finally:
        db.close()


@router.post("")
def create_expense(inp: ExpenseIn, user: User = Depends(require_permission("expenses", "create"))):
    db = SessionLocal()
    try:
        try:
            dt = datetime.strptime(inp.expense_date, "%Y-%m-%d") if inp.expense_date else datetime.now()
        except ValueError:
            raise HTTPException(400, f"Invalid date format: {inp.expense_date}. Use YYYY-MM-DD")
        e = Expense(category=inp.category, description=inp.description,
                    amount=inp.amount, vendor=inp.vendor, expense_date=dt)
        db.add(e)
        db.commit()
        return {"message": "Expense added"}
    finally:
        db.close()


@router.delete("/{eid}")
def delete_expense(eid: int, user: User = Depends(require_permission("expenses", "delete"))):
    db = SessionLocal()
    try:
        e = db.query(Expense).filter(Expense.id == eid).first()
        if not e:
            raise HTTPException(404, "Not found")
        db.delete(e)
        db.commit()
        return {"message": "Deleted"}
    finally:
        db.close()


@router.put("/{eid}")
def update_expense(eid: int, inp: ExpenseIn, user: User = Depends(require_permission("expenses", "edit"))):
    db = SessionLocal()
    try:
        e = db.query(Expense).filter(Expense.id == eid).first()
        if not e:
            raise HTTPException(404, "Not found")
        e.category = inp.category
        e.description = inp.description
        e.amount = inp.amount
        e.vendor = inp.vendor
        if inp.expense_date:
            try:
                e.expense_date = datetime.strptime(inp.expense_date, "%Y-%m-%d")
            except Exception:
                logger.warning("Invalid expense_date '%s' for expense %s", inp.expense_date, eid)
        db.commit()
        return {"message": "Expense updated"}
    finally:
        db.close()
