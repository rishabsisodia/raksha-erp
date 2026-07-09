from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
import os

app = FastAPI(title="Raksha ERP")

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./raksha_erp.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if DATABASE_URL.startswith("postgresql://"):
    engine = create_engine(DATABASE_URL)
else:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, default="")
    size = Column(String, default="")
    load_rating = Column(String, default="")
    material = Column(String, default="FRP")
    color = Column(String, default="Grey")
    unit = Column(String, default="Nos")
    hsn_code = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    pricing = relationship("Pricing", back_populates="product", uselist=False, cascade="all,delete-orphan")
    stock = relationship("Stock", back_populates="product", uselist=False, cascade="all,delete-orphan")


class Pricing(Base):
    __tablename__ = "pricing"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True)
    raw_material_cost = Column(Float, default=0)
    labor_cost = Column(Float, default=0)
    overhead_cost = Column(Float, default=0)
    packing_cost = Column(Float, default=0)
    total_cost = Column(Float, default=0)
    profit_margin = Column(Float, default=20)
    mrp = Column(Float, default=0)
    dealer_price = Column(Float, default=0)
    distributor_price = Column(Float, default=0)
    gst_rate = Column(Float, default=18)
    product = relationship("Product", back_populates="pricing")


class Stock(Base):
    __tablename__ = "stock"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True)
    quantity = Column(Integer, default=0)
    min_stock = Column(Integer, default=10)
    product = relationship("Product", back_populates="stock")


class StockEntry(Base):
    __tablename__ = "stock_entries"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    entry_type = Column(String, default="IN")
    reference = Column(String, default="")
    notes = Column(String, default="")
    entry_date = Column(DateTime, default=datetime.utcnow)


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, default="")
    email = Column(String, default="")
    address = Column(String, default="")
    gst_number = Column(String, default="")
    state = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    invoice_no = Column(String, unique=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    unit_price = Column(Float)
    discount_percent = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    taxable_amount = Column(Float)
    cgst_rate = Column(Float, default=9)
    cgst_amount = Column(Float, default=0)
    sgst_rate = Column(Float, default=9)
    sgst_amount = Column(Float, default=0)
    freight_amount = Column(Float, default=0)
    total_amount = Column(Float)
    payment_status = Column(String, default="Pending")
    payment_method = Column(String, default="Cash")
    sale_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(String, default="")
    customer = relationship("Customer")
    product = relationship("Product")


class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String)
    description = Column(String, default="")
    amount = Column(Float)
    vendor = Column(String, default="")
    expense_date = Column(DateTime, default=datetime.utcnow)


class Settings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True)
    value = Column(String, default="")


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    seed_data()


def seed_data():
    db = SessionLocal()
    try:
        if db.query(Product).count() > 0:
            return

        import hashlib
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(username="admin", password_hash=hashlib.sha256("admin123".encode()).hexdigest(), role="admin")
            db.add(admin)
            db.commit()

        categories = ["Manhole Cover", "Gully Cover", "Frames", "Gratings", "Accessories"]
        square_sizes = [f"{s}x{s}" for s in range(10, 38, 2)]
        rect_sizes = ["12x18", "12x24", "18x24"]
        colors = ["Grey", "White"]
        load_ratings = ["5 Ton", "10 Ton", "12.5 Ton", "25 Ton", "40 Ton"]
        hsn_codes = {"Manhole Cover": "6914", "Gully Cover": "6914", "Frames": "6914", "Gratings": "6914", "Accessories": "6914"}

        pid = 1
        for cat in categories:
            sizes = square_sizes if cat in ["Manhole Cover", "Gully Cover", "Frames"] else square_sizes[:6] + rect_sizes
            for color in colors:
                for size in sizes:
                    for lr in load_ratings:
                        name = f"{cat} {size}mm {color} {lr}"
                        p = Product(id=pid, name=name, category=cat, size=size, load_rating=lr, material="FRP", color=color, hsn_code=hsn_codes.get(cat, "6914"))
                        db.add(p)
                        db.flush()
                        db.add(Pricing(product_id=p.id, profit_margin=20, gst_rate=18))
                        db.add(Stock(product_id=p.id, quantity=0, min_stock=10))
                        pid += 1

        db.commit()
        print(f"Seeded {pid - 1} products")
    finally:
        db.close()


class ProductIn(BaseModel):
    name: str
    category: str = ""
    size: str = ""
    load_rating: str = ""
    material: str = "FRP"
    color: str = "Grey"
    unit: str = "Nos"
    hsn_code: str = ""


class PricingIn(BaseModel):
    raw_material_cost: float = 0
    labor_cost: float = 0
    overhead_cost: float = 0
    packing_cost: float = 0
    profit_margin: float = 20
    gst_rate: float = 18


class CustomerIn(BaseModel):
    name: str
    phone: str = ""
    email: str = ""
    address: str = ""
    gst_number: str = ""
    state: str = ""


class SaleIn(BaseModel):
    customer_id: int
    product_id: int
    quantity: int
    unit_price: float
    discount_percent: float = 0
    freight_amount: float = 0
    payment_status: str = "Pending"
    payment_method: str = "Cash"
    notes: str = ""


class ExpenseIn(BaseModel):
    category: str
    description: str = ""
    amount: float
    vendor: str = ""
    expense_date: Optional[str] = None


class StockIn(BaseModel):
    product_id: int
    quantity: int
    reference: str = ""
    notes: str = ""


# ---- PRODUCTS ----
@app.get("/api/products")
def list_products():
    db = SessionLocal()
    try:
        rows = db.query(Product).all()
        out = []
        for p in rows:
            stock_qty = p.stock.quantity if p.stock else 0
            mrp = p.pricing.mrp if p.pricing else 0
            out.append({
                "id": p.id, "name": p.name, "category": p.category,
                "size": p.size, "load_rating": p.load_rating,
                "material": p.material, "color": p.color, "unit": p.unit, "hsn_code": p.hsn_code,
                "stock": stock_qty, "mrp": mrp
            })
        return out
    finally:
        db.close()


@app.post("/api/products")
def create_product(inp: ProductIn):
    db = SessionLocal()
    try:
        p = Product(**inp.dict())
        db.add(p)
        db.commit()
        db.refresh(p)
        db.add(Pricing(product_id=p.id))
        db.add(Stock(product_id=p.id, quantity=0))
        db.commit()
        return {"id": p.id, "message": "Product created"}
    finally:
        db.close()


@app.put("/api/products/{pid}")
def update_product(pid: int, inp: ProductIn):
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


@app.delete("/api/products/{pid}")
def delete_product(pid: int):
    db = SessionLocal()
    try:
        p = db.query(Product).filter(Product.id == pid).first()
        if not p:
            raise HTTPException(404, "Not found")
        db.delete(p)
        db.commit()
        return {"message": "Deleted"}
    finally:
        db.close()


# ---- PRICING ----
@app.get("/api/products/{pid}/pricing")
def get_pricing(pid: int):
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


@app.put("/api/products/{pid}/pricing")
def update_pricing(pid: int, inp: PricingIn):
    db = SessionLocal()
    try:
        pr = db.query(Pricing).filter(Pricing.product_id == pid).first()
        if not pr:
            pr = Pricing(product_id=pid)
            db.add(pr)
        tc = inp.raw_material_cost + inp.labor_cost + inp.overhead_cost + inp.packing_cost
        mrp = tc * (1 + inp.profit_margin / 100)
        pr.raw_material_cost = inp.raw_material_cost
        pr.labor_cost = inp.labor_cost
        pr.overhead_cost = inp.overhead_cost
        pr.packing_cost = inp.packing_cost
        pr.profit_margin = inp.profit_margin
        pr.gst_rate = inp.gst_rate
        pr.total_cost = tc
        pr.mrp = mrp
        pr.dealer_price = mrp * 0.85
        pr.distributor_price = mrp * 0.75
        db.commit()
        return {"message": "Updated", "mrp": mrp}
    finally:
        db.close()


# ---- STOCK ----
@app.get("/api/stock")
def list_stock():
    db = SessionLocal()
    try:
        rows = db.query(Stock).all()
        out = []
        for s in rows:
            p = db.query(Product).filter(Product.id == s.product_id).first()
            if p:
                out.append({
                    "product_id": s.product_id,
                    "product_name": p.name,
                    "category": p.category,
                    "size": p.size,
                    "quantity": s.quantity,
                    "min_stock": s.min_stock,
                    "unit": p.unit,
                    "status": "low" if s.quantity <= s.min_stock else "ok"
                })
        return out
    finally:
        db.close()


@app.put("/api/stock/{pid}")
def update_stock_min(pid: int, body: dict):
    db = SessionLocal()
    try:
        s = db.query(Stock).filter(Stock.product_id == pid).first()
        if not s:
            raise HTTPException(404, "Not found")
        if "min_stock" in body:
            s.min_stock = int(body["min_stock"])
        db.commit()
        return {"message": "Updated"}
    finally:
        db.close()


@app.post("/api/stock/add")
def add_stock(inp: StockIn):
    db = SessionLocal()
    try:
        s = db.query(Stock).filter(Stock.product_id == inp.product_id).first()
        if not s:
            s = Stock(product_id=inp.product_id, quantity=0)
            db.add(s)
        s.quantity += inp.quantity
        db.add(StockEntry(
            product_id=inp.product_id, quantity=inp.quantity,
            entry_type="IN", reference=inp.reference, notes=inp.notes
        ))
        db.commit()
        return {"message": f"Added {inp.quantity} units"}
    finally:
        db.close()


@app.get("/api/stock/history")
def stock_history():
    db = SessionLocal()
    try:
        rows = db.query(StockEntry).order_by(StockEntry.entry_date.desc()).limit(50).all()
        out = []
        for e in rows:
            p = db.query(Product).filter(Product.id == e.product_id).first()
            out.append({
                "id": e.id,
                "product_name": p.name if p else "?",
                "quantity": e.quantity,
                "entry_type": e.entry_type,
                "reference": e.reference,
                "notes": e.notes,
                "entry_date": e.entry_date.isoformat() if e.entry_date else None
            })
        return out
    finally:
        db.close()


# ---- CUSTOMERS ----
@app.get("/api/customers")
def list_customers():
    db = SessionLocal()
    try:
        rows = db.query(Customer).all()
        return [{"id": c.id, "name": c.name, "phone": c.phone, "email": c.email,
                 "address": c.address, "gst_number": c.gst_number, "state": c.state}
                for c in rows]
    finally:
        db.close()


@app.post("/api/customers")
def create_customer(inp: CustomerIn):
    db = SessionLocal()
    try:
        c = Customer(**inp.dict())
        db.add(c)
        db.commit()
        db.refresh(c)
        return {"id": c.id, "message": "Customer created"}
    finally:
        db.close()


@app.put("/api/customers/{cid}")
def update_customer(cid: int, inp: CustomerIn):
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


@app.delete("/api/customers/{cid}")
def delete_customer(cid: int):
    db = SessionLocal()
    try:
        c = db.query(Customer).filter(Customer.id == cid).first()
        if not c:
            raise HTTPException(404, "Not found")
        db.delete(c)
        db.commit()
        return {"message": "Deleted"}
    finally:
        db.close()


# ---- SALES ----
@app.get("/api/sales")
def list_sales():
    db = SessionLocal()
    try:
        rows = db.query(Sale).order_by(Sale.sale_date.desc()).all()
        out = []
        for s in rows:
            cust = db.query(Customer).filter(Customer.id == s.customer_id).first()
            prod = db.query(Product).filter(Product.id == s.product_id).first()
            out.append({
                "id": s.id, "invoice_no": s.invoice_no,
                "customer_name": cust.name if cust else "?",
                "product_name": prod.name if prod else "?",
                "quantity": s.quantity, "unit_price": s.unit_price,
                "taxable_amount": s.taxable_amount,
                "cgst_amount": s.cgst_amount, "sgst_amount": s.sgst_amount,
                "freight_amount": s.freight_amount,
                "total_amount": s.total_amount,
                "payment_status": s.payment_status,
                "payment_method": s.payment_method,
                "sale_date": s.sale_date.isoformat() if s.sale_date else None,
                "notes": s.notes
            })
        return out
    finally:
        db.close()


@app.post("/api/sales")
def create_sale(inp: SaleIn):
    db = SessionLocal()
    try:
        prod = db.query(Product).filter(Product.id == inp.product_id).first()
        if not prod:
            raise HTTPException(404, "Product not found")
        pr = db.query(Pricing).filter(Pricing.product_id == inp.product_id).first()
        gst_rate = pr.gst_rate if pr else 18

        taxable = inp.quantity * inp.unit_price
        disc_amt = taxable * inp.discount_percent / 100
        taxable -= disc_amt
        cgst = taxable * gst_rate / 200
        sgst = taxable * gst_rate / 200
        total = taxable + cgst + sgst + inp.freight_amount

        max_id = db.query(Sale).count()
        invoice_no = f"RFRP-{max_id + 1:05d}"

        s = Sale(
            invoice_no=invoice_no, customer_id=inp.customer_id,
            product_id=inp.product_id, quantity=inp.quantity,
            unit_price=inp.unit_price, discount_percent=inp.discount_percent,
            discount_amount=disc_amt, taxable_amount=taxable,
            cgst_rate=gst_rate / 2, cgst_amount=cgst,
            sgst_rate=gst_rate / 2, sgst_amount=sgst,
            freight_amount=inp.freight_amount, total_amount=total,
            payment_status=inp.payment_status, payment_method=inp.payment_method,
            notes=inp.notes
        )
        db.add(s)

        stock = db.query(Stock).filter(Stock.product_id == inp.product_id).first()
        if stock:
            stock.quantity -= inp.quantity

        db.commit()
        return {"invoice_no": invoice_no, "total": total}
    finally:
        db.close()


@app.delete("/api/sales/{sid}")
def delete_sale(sid: int):
    db = SessionLocal()
    try:
        s = db.query(Sale).filter(Sale.id == sid).first()
        if not s:
            raise HTTPException(404, "Not found")
        stock = db.query(Stock).filter(Stock.product_id == s.product_id).first()
        if stock:
            stock.quantity += s.quantity
        db.delete(s)
        db.commit()
        return {"message": "Deleted"}
    finally:
        db.close()


# ---- EXPENSES ----
@app.get("/api/expenses")
def list_expenses():
    db = SessionLocal()
    try:
        rows = db.query(Expense).order_by(Expense.expense_date.desc()).all()
        return [{"id": e.id, "category": e.category, "description": e.description,
                 "amount": e.amount, "vendor": e.vendor,
                 "expense_date": e.expense_date.isoformat() if e.expense_date else None}
                for e in rows]
    finally:
        db.close()


@app.post("/api/expenses")
def create_expense(inp: ExpenseIn):
    db = SessionLocal()
    try:
        dt = datetime.strptime(inp.expense_date, "%Y-%m-%d") if inp.expense_date else datetime.utcnow()
        e = Expense(category=inp.category, description=inp.description,
                    amount=inp.amount, vendor=inp.vendor, expense_date=dt)
        db.add(e)
        db.commit()
        return {"message": "Expense added"}
    finally:
        db.close()


@app.delete("/api/expenses/{eid}")
def delete_expense(eid: int):
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


# ---- REPORTS ----
@app.get("/api/reports/profit-loss")
def profit_loss(start_date: str = None, end_date: str = None):
    db = SessionLocal()
    try:
        sales = db.query(Sale).all()
        expenses = db.query(Expense).all()

        revenue = sum(s.total_amount for s in sales)
        units = sum(s.quantity for s in sales)
        gst = sum(s.cgst_amount + s.sgst_amount for s in sales)

        avg_cost = db.query(Pricing.total_cost).filter(Pricing.total_cost > 0).all()
        avg = sum(a[0] for a in avg_cost) / len(avg_cost) if avg_cost else 0
        cogs = units * avg

        exp_by_cat = {}
        for e in expenses:
            exp_by_cat[e.category] = exp_by_cat.get(e.category, 0) + e.amount
        total_opex = sum(exp_by_cat.values())

        gp = revenue - cogs
        ebitda = gp - total_opex
        tax = ebitda * 0.25 if ebitda > 0 else 0
        pat = ebitda - tax

        return {
            "revenue": revenue, "gst": gst, "units": units,
            "cogs": cogs, "gross_profit": gp,
            "gross_margin": (gp / revenue * 100) if revenue else 0,
            "expenses": exp_by_cat, "total_opex": total_opex,
            "ebitda": ebitda, "ebitda_margin": (ebitda / revenue * 100) if revenue else 0,
            "tax_rate": 25, "tax": tax, "pat": pat
        }
    finally:
        db.close()


# ---- DASHBOARD ----
@app.get("/api/dashboard")
def dashboard():
    db = SessionLocal()
    try:
        return {
            "total_products": db.query(Product).count(),
            "total_customers": db.query(Customer).count(),
            "total_sales": db.query(Sale).count(),
            "revenue": sum(s.total_amount for s in db.query(Sale).all()),
            "low_stock": db.query(Stock).filter(Stock.quantity <= Stock.min_stock).count(),
            "pending": sum(s.total_amount for s in db.query(Sale).filter(Sale.payment_status == "Pending").all()),
            "recent_sales": [
                {"id": s.id, "invoice": s.invoice_no,
                 "customer": (db.query(Customer).filter(Customer.id == s.customer_id).first() or type("", (), {"name": "?"})()).name,
                 "amount": s.total_amount, "status": s.payment_status,
                 "date": s.sale_date.strftime("%d %b") if s.sale_date else ""}
                for s in db.query(Sale).order_by(Sale.sale_date.desc()).limit(5).all()
            ]
        }
    finally:
        db.close()


# ---- SETTINGS ----
@app.get("/api/settings")
def get_settings():
    db = SessionLocal()
    try:
        rows = db.query(Settings).all()
        return {s.key: s.value for s in rows}
    finally:
        db.close()


@app.put("/api/settings")
def update_settings(body: dict):
    db = SessionLocal()
    try:
        for k, v in body.items():
            row = db.query(Settings).filter(Settings.key == k).first()
            if row:
                row.value = str(v)
            else:
                db.add(Settings(key=k, value=str(v)))
        db.commit()
        return {"message": "Settings updated"}
    finally:
        db.close()


# ---- FRONTEND ----
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/")
def index():
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"message": "Raksha ERP API is running. Frontend not found."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
