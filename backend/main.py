from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
import os
import cloudinary
import cloudinary.uploader
import urllib.request

app = FastAPI(title="Raksha ERP")

CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "")
if CLOUDINARY_URL and "@" in CLOUDINARY_URL:
    parts = CLOUDINARY_URL.replace("cloudinary://", "").split("@")
    creds = parts[0].split(":")
    cloudinary.config(
        api_key=creds[0],
        api_secret=creds[1],
        cloud_name=parts[1],
        secure=True
    )

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
    part_no = Column(String, default="")
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


class Customer(Base):
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(String, unique=True, nullable=False)
    gstin = Column(String, default="")
    billing_address = Column(String, default="")
    shipping_address = Column(String, default="")
    state = Column(String, default="")
    district = Column(String, default="")
    city = Column(String, default="")
    pincode = Column(String, default="")
    contact_name = Column(String, default="")
    contact_number = Column(String, default="")
    contact_email = Column(String, default="")
    exec_code = Column(String, default="")
    exec_name = Column(String, default="")
    exec_number = Column(String, default="")
    exec_email = Column(String, default="")
    blacklisted = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Transporter(Base):
    __tablename__ = "transporters"
    id = Column(Integer, primary_key=True, index=True)
    transporter_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, default="")
    email = Column(String, default="")
    address = Column(Text, default="")
    state = Column(String, default="")
    district = Column(String, default="")
    city = Column(String, default="")
    pincode = Column(String, default="")
    gst_number = Column(String, default="")
    pan_number = Column(String, default="")
    gst_certificate = Column(String, default="")
    pan_card = Column(String, default="")
    contact_person = Column(String, default="")
    contact_number = Column(String, default="")
    blacklisted = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    invoice_no = Column(String)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    quantity = Column(Integer, nullable=True)
    unit_price = Column(Float, nullable=True)
    discount_percent = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    taxable_amount = Column(Float, nullable=True)
    cgst_rate = Column(Float, default=9)
    cgst_amount = Column(Float, default=0)
    sgst_rate = Column(Float, default=9)
    sgst_amount = Column(Float, default=0)
    freight_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    payment_status = Column(String, default="Pending")
    payment_method = Column(String, default="Cash")
    sale_date = Column(DateTime, nullable=True)
    notes = Column(String, default="")
    party_name = Column(String, default="")
    payment_terms = Column(String, default="")
    location = Column(String, default="")
    pincode = Column(String, default="")
    state = Column(String, default="")
    transporter_name = Column(String, default="")
    lr_no = Column(String, default="")
    weight_kgs = Column(Float, default=0)
    weight_pg_fiber = Column(Float, default=0)
    sales_person = Column(String, default="")
    pg_fiber_invoice_no = Column(String, default="")
    pg_fiber_invoice_value = Column(Float, default=0)
    gp = Column(Float, default=0)
    gp_percent = Column(Float, default=0)
    source_csv = Column(String, default="")
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


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)


class Token(Base):
    __tablename__ = "tokens"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    sl_no = Column(Integer, default=0)
    po_no = Column(String, default="")
    po_date = Column(String, default="")
    billing_site = Column(String, default="")
    shipping_site = Column(String, default="")
    no_of_boxes = Column(Integer, default=0)
    value_excl_gst_freight = Column(Float, default=0)
    invoice_no = Column(String, default="")
    invoice_date = Column(String, default="")
    invoice_amount_excl_gst = Column(Float, default=0)
    weight_kgs = Column(Float, default=0)
    freight_rate_per_kg = Column(Float, default=0)
    transport_charges = Column(Float, default=0)
    invoice_amount = Column(Float, default=0)
    eway_bill_no = Column(String, default="")
    lr_no = Column(String, default="")
    entry_date = Column(String, default="")
    credit_note_amount = Column(Float, default=0)
    credit_note_no = Column(String, default="")
    transporter = Column(String, default="")
    transporter_no = Column(String, default="")


@app.get("/api/db-info")
def db_info():
    db_url = os.environ.get("DATABASE_URL")
    has_key = "DATABASE_URL" in os.environ
    if db_url:
        masked = db_url[:20] + "...(masked)"
    else:
        masked = None
    return {
        "has_database_url_key": has_key,
        "db_url_preview": masked,
        "env_key_count": len(os.environ)
    }


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS part_no VARCHAR DEFAULT ''"))
            conn.commit()
        except Exception:
            pass
        try:
            conn.execute(text("ALTER TABLE sales DROP CONSTRAINT IF EXISTS sales_invoice_no_key"))
            conn.commit()
        except Exception:
            pass
        new_sale_cols = [
            "party_name", "payment_terms", "location", "pincode", "state",
            "transporter_name", "lr_no", "weight_kgs", "weight_pg_fiber",
            "sales_person", "pg_fiber_invoice_no", "pg_fiber_invoice_value",
            "gp", "gp_percent", "source_csv"
        ]
        for col in new_sale_cols:
            try:
                col_type = "FLOAT" if col in ("weight_kgs","weight_pg_fiber","pg_fiber_invoice_value","gp","gp_percent") else "VARCHAR DEFAULT ''"
                conn.execute(text(f"ALTER TABLE sales ADD COLUMN IF NOT EXISTS {col} {col_type}"))
            except Exception:
                pass
        conn.commit()
    backfill_part_numbers()
    seed_data()


PART_NO_CSV = [
    ("FRP01101-GRY", "FRP Manhole Cover 10 X 10  Grey"),
    ("FRP01103-GRY", "FRP Manhole Cover 12 X 12  Grey"),
    ("FRP01106-GRY", "FRP Manhole Cover 15 X 15 Grey"),
    ("FRP01109-GRY", "FRP Manhole Cover 18 X 18 Grey"),
    ("FRP01112-GRY", "FRP Manhole Cover 21 X 21 Grey"),
    ("FRP01115-GRY", "FRP Manhole Cover 24 X 24 Grey"),
    ("FRP01117-GRY", "FRP Manhole Cover 26 X 26 Grey"),
    ("FRP01119-GRY", "FRP Manhole Cover 28 X 28 Grey"),
    ("FRP01121-GRY", "FRP Manhole Cover 30 X 30 Grey"),
    ("FRP01127-GRY", "FRP Manhole Cover 36 X 36 Grey"),
    ("FRP04106-GRY", "FRP Manhole Cover 12 X 18  Grey"),
    ("FRP04112-GRY", "FRP Manhole Cover 12 X 24  Grey"),
    ("FRP10106-GRY", "FRP Manhole Cover 18 X 24 Grey"),
    ("FRP01101-WH", "FRP Manhole Cover 10 X 10 White"),
    ("FRP01103-WH", "FRP Manhole Cover 12 X 12  White"),
    ("FRP01106-WH", "FRP Manhole Cover 15 X 15 White"),
    ("FRP01109-WH", "FRP Manhole Cover 18 X 18 White"),
    ("FRP01112-WH", "FRP Manhole Cover 21 X 21 White"),
    ("FRP01115-WH", "FRP Manhole Cover 24 X 24 White"),
    ("FRP01117-WH", "FRP Manhole Cover 26 X 26 White"),
    ("FRP01119-WH", "FRP Manhole Cover 28 X 28 White"),
    ("FRP01121-WH", "FRP Manhole Cover 30 X 30 White"),
    ("FRP01127-WH", "FRP Manhole Cover 36 X 36 White"),
    ("FRP04106-WH", "FRP Manhole Cover 12 X 18  White"),
    ("FRP04112-WH", "FRP Manhole Cover 12 X 24  White"),
    ("FRP10106-WH", "FRP Manhole Cover 18 X 24  White"),
    ("FRP01112-GRYL", "FRP Manhole Cover 21 X 21 Grey With Lock"),
    ("FRP01115-GRYL", "FRP Manhole Cover 24 X 24 Grey With Lock"),
    ("FRP01117-GRYL", "FRP Manhole Cover 26 X 26 Grey With Lock"),
    ("FRP01119-GRYL", "FRP Manhole Cover 28 X 28 Grey With Lock"),
    ("FRP01121-GRYL", "FRP Manhole Cover 30 X 30 Grey With Lock"),
    ("FRP01127-GRYL", "FRP Manhole Cover 36 X 36 Grey With Lock"),
    ("FRP01112-WHL", "FRP Manhole Cover 21 X 21 White With Lock"),
    ("FRP01115-WHL", "FRP Manhole Cover 24 X 24 White With Lock"),
    ("FRP01117-WHL", "FRP Manhole Cover 26 X 26 White With Lock"),
    ("FRP01119-WHL", "FRP Manhole Cover 28 X 28 White With Lock"),
    ("FRP01121-WHL", "FRP Manhole Cover 30 X 30 White With Lock"),
    ("FRP01127-WHL", "FRP Manhole Cover 36 X 36 White With Lock"),
    ("RGC00001-GRY", "RAKSHA Gully Cover 10 X 10 Grey"),
    ("RGC00002-GRY", "RAKSHA Gully Cover 12 X 12 Grey"),
    ("RGC00003-GRY", "RAKSHA Gully Cover 15 X 15 Grey"),
    ("RGC00004-GRY", "RAKSHA Gully Cover 18 X 18 Grey"),
    ("RGC00005-GRY", "RAKSHA Gully Cover 24 X 24 Grey"),
    ("RGC00001-WH", "RAKSHA Gully Cover 10 X 10 White"),
    ("RGC00002-WH", "RAKSHA Gully Cover 12 X 12 White"),
    ("RGC00003-WH", "RAKSHA Gully Cover 15 X 15 White"),
    ("RGC00004-WH", "RAKSHA Gully Cover 18 X 18 White"),
    ("RGC00005-WH", "RAKSHA Gully Cover 24 X 24 White"),
]


def generate_part_no(product):
    if product.part_no:
        return product.part_no
    import re
    name_lower = (product.name or "").lower()
    size = (product.size or "").lower().replace(" ", "")
    color = (product.color or "").lower()
    has_lock = "lock" in name_lower
    is_gully = "gully" in name_lower

    size_dim_map = {
        "250x250": ("10x10", "10X10"), "300x300": ("12x12", "12X12"),
        "380x380": ("15x15", "15X15"), "450x450": ("18x18", "18X18"),
        "535x535": ("21x21", "21X21"), "600x600": ("24x24", "24X24"),
        "660x660": ("26x26", "26X26"), "710x710": ("28x28", "28X28"),
        "760x760": ("30x30", "30X30"), "900x900": ("36x36", "36X36"),
        "1065x1065": ("42x42", "42X42"),
        "300x450": ("12x18", "12X18"), "300x600": ("12x24", "12X24"),
        "450x600": ("18x24", "18X24"),
    }
    nominal = size_dim_map.get(size)
    if not nominal:
        m = re.search(r'(\d+)\s*x\s*(\d+)', product.size or product.name or "")
        if m:
            nominal = (f"{m.group(1)}x{m.group(2)}", f"{m.group(1)}X{m.group(2)}")
        else:
            return ""

    nom_lower = nominal[0]
    nom_upper = nominal[1]
    color_code = "WH" if "white" in color else "GRY"
    if has_lock:
        color_code += "L"

    prefix = "RGC" if is_gully else "FRP"
    csv_desc = f"{prefix} {nom_upper} {('Grey' if 'grey' in color else 'White')}"
    if has_lock:
        csv_desc += " With Lock"

    for pn, desc in PART_NO_CSV:
        if desc.strip().lower() == csv_desc.strip().lower():
            return pn

    return ""


def backfill_part_numbers():
    db = SessionLocal()
    try:
        updated = 0
        for p in db.query(Product).filter((Product.part_no == "") | (Product.part_no.is_(None))).all():
            pn = generate_part_no(p)
            if pn:
                p.part_no = pn
                updated += 1
        if updated:
            db.commit()
            print(f"Backfilled part_no for {updated} products")
    finally:
        db.close()


def seed_data():
    db = SessionLocal()
    try:
        import hashlib
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(username="admin", password_hash=hashlib.sha256("admin123".encode()).hexdigest(), role="admin")
            db.add(admin)
            db.commit()

        if db.query(Product).count() > 0:
            return

        products = [
            # Manhole Cover - Grey
            {"part_no": "FRP01101-GRY", "name": "FRP Manhole Cover 10 X 10 Grey", "category": "Manhole Cover", "size": "10x10", "color": "Grey", "rate": 190, "mrp": 686},
            {"part_no": "FRP01103-GRY", "name": "FRP Manhole Cover 12 X 12 Grey", "category": "Manhole Cover", "size": "12x12", "color": "Grey", "rate": 242, "mrp": 830},
            {"part_no": "FRP01106-GRY", "name": "FRP Manhole Cover 15 X 15 Grey", "category": "Manhole Cover", "size": "15x15", "color": "Grey", "rate": 310, "mrp": 1046},
            {"part_no": "FRP01109-GRY", "name": "FRP Manhole Cover 18 X 18 Grey", "category": "Manhole Cover", "size": "18x18", "color": "Grey", "rate": 455, "mrp": 1536},
            {"part_no": "FRP01112-GRY", "name": "FRP Manhole Cover 21 X 21 Grey", "category": "Manhole Cover", "size": "21x21", "color": "Grey", "rate": 640, "mrp": 2130},
            {"part_no": "FRP01115-GRY", "name": "FRP Manhole Cover 24 X 24 Grey", "category": "Manhole Cover", "size": "24x24", "color": "Grey", "rate": 765, "mrp": 2560},
            {"part_no": "FRP01117-GRY", "name": "FRP Manhole Cover 26 X 26 Grey", "category": "Manhole Cover", "size": "26x26", "color": "Grey", "rate": 1130, "mrp": 3266},
            {"part_no": "FRP01119-GRY", "name": "FRP Manhole Cover 28 X 28 Grey", "category": "Manhole Cover", "size": "28x28", "color": "Grey", "rate": 1500, "mrp": 4934},
            {"part_no": "FRP01121-GRY", "name": "FRP Manhole Cover 30 X 30 Grey", "category": "Manhole Cover", "size": "30x30", "color": "Grey", "rate": 1750, "mrp": 5854},
            {"part_no": "FRP01127-GRY", "name": "FRP Manhole Cover 36 X 36 Grey", "category": "Manhole Cover", "size": "36x36", "color": "Grey", "rate": 3200, "mrp": 11454},
            {"part_no": "FRP04106-GRY", "name": "FRP Manhole Cover 12 X 18 Grey", "category": "Manhole Cover", "size": "12x18", "color": "Grey", "rate": 350, "mrp": 1154},
            {"part_no": "FRP04112-GRY", "name": "FRP Manhole Cover 12 X 24 Grey", "category": "Manhole Cover", "size": "12x24", "color": "Grey", "rate": 500, "mrp": 1624},
            {"part_no": "FRP10106-GRY", "name": "FRP Manhole Cover 18 X 24 Grey", "category": "Manhole Cover", "size": "18x24", "color": "Grey", "rate": 620, "mrp": 2020},
            # Manhole Cover - White
            {"part_no": "FRP01101-WH", "name": "FRP Manhole Cover 10 X 10 White", "category": "Manhole Cover", "size": "10x10", "color": "White", "rate": 190, "mrp": 686},
            {"part_no": "FRP01103-WH", "name": "FRP Manhole Cover 12 X 12 White", "category": "Manhole Cover", "size": "12x12", "color": "White", "rate": 242, "mrp": 830},
            {"part_no": "FRP01106-WH", "name": "FRP Manhole Cover 15 X 15 White", "category": "Manhole Cover", "size": "15x15", "color": "White", "rate": 310, "mrp": 1046},
            {"part_no": "FRP01109-WH", "name": "FRP Manhole Cover 18 X 18 White", "category": "Manhole Cover", "size": "18x18", "color": "White", "rate": 455, "mrp": 1536},
            {"part_no": "FRP01112-WH", "name": "FRP Manhole Cover 21 X 21 White", "category": "Manhole Cover", "size": "21x21", "color": "White", "rate": 640, "mrp": 2130},
            {"part_no": "FRP01115-WH", "name": "FRP Manhole Cover 24 X 24 White", "category": "Manhole Cover", "size": "24x24", "color": "White", "rate": 765, "mrp": 2560},
            {"part_no": "FRP01117-WH", "name": "FRP Manhole Cover 26 X 26 White", "category": "Manhole Cover", "size": "26x26", "color": "White", "rate": 1130, "mrp": 3266},
            {"part_no": "FRP01119-WH", "name": "FRP Manhole Cover 28 X 28 White", "category": "Manhole Cover", "size": "28x28", "color": "White", "rate": 1500, "mrp": 4934},
            {"part_no": "FRP01121-WH", "name": "FRP Manhole Cover 30 X 30 White", "category": "Manhole Cover", "size": "30x30", "color": "White", "rate": 1750, "mrp": 5854},
            {"part_no": "FRP01127-WH", "name": "FRP Manhole Cover 36 X 36 White", "category": "Manhole Cover", "size": "36x36", "color": "White", "rate": 3200, "mrp": 11454},
            {"part_no": "FRP04106-WH", "name": "FRP Manhole Cover 12 X 18 White", "category": "Manhole Cover", "size": "12x18", "color": "White", "rate": 350, "mrp": 1154},
            {"part_no": "FRP04112-WH", "name": "FRP Manhole Cover 12 X 24 White", "category": "Manhole Cover", "size": "12x24", "color": "White", "rate": 500, "mrp": 1624},
            {"part_no": "FRP10106-WH", "name": "FRP Manhole Cover 18 X 24 White", "category": "Manhole Cover", "size": "18x24", "color": "White", "rate": 620, "mrp": 2020},
            # Manhole Cover - Grey With Lock
            {"part_no": "FRP01112-GRYL", "name": "FRP Manhole Cover 21 X 21 Grey With Lock", "category": "Manhole Cover", "size": "21x21", "color": "Grey", "rate": 710, "mrp": 2130},
            {"part_no": "FRP01115-GRYL", "name": "FRP Manhole Cover 24 X 24 Grey With Lock", "category": "Manhole Cover", "size": "24x24", "color": "Grey", "rate": 835, "mrp": 2560},
            {"part_no": "FRP01117-GRYL", "name": "FRP Manhole Cover 26 X 26 Grey With Lock", "category": "Manhole Cover", "size": "26x26", "color": "Grey", "rate": 1270, "mrp": 3266},
            {"part_no": "FRP01119-GRYL", "name": "FRP Manhole Cover 28 X 28 Grey With Lock", "category": "Manhole Cover", "size": "28x28", "color": "Grey", "rate": 1640, "mrp": 4934},
            {"part_no": "FRP01121-GRYL", "name": "FRP Manhole Cover 30 X 30 Grey With Lock", "category": "Manhole Cover", "size": "30x30", "color": "Grey", "rate": 1890, "mrp": 5854},
            {"part_no": "FRP01127-GRYL", "name": "FRP Manhole Cover 36 X 36 Grey With Lock", "category": "Manhole Cover", "size": "36x36", "color": "Grey", "rate": 3340, "mrp": 11454},
            # Manhole Cover - White With Lock
            {"part_no": "FRP01112-WHL", "name": "FRP Manhole Cover 21 X 21 White With Lock", "category": "Manhole Cover", "size": "21x21", "color": "White", "rate": 710, "mrp": 2130},
            {"part_no": "FRP01115-WHL", "name": "FRP Manhole Cover 24 X 24 White With Lock", "category": "Manhole Cover", "size": "24x24", "color": "White", "rate": 835, "mrp": 2560},
            {"part_no": "FRP01117-WHL", "name": "FRP Manhole Cover 26 X 26 White With Lock", "category": "Manhole Cover", "size": "26x26", "color": "White", "rate": 1270, "mrp": 3266},
            {"part_no": "FRP01119-WHL", "name": "FRP Manhole Cover 28 X 28 White With Lock", "category": "Manhole Cover", "size": "28x28", "color": "White", "rate": 1640, "mrp": 4934},
            {"part_no": "FRP01121-WHL", "name": "FRP Manhole Cover 30 X 30 White With Lock", "category": "Manhole Cover", "size": "30x30", "color": "White", "rate": 1890, "mrp": 5854},
            {"part_no": "FRP01127-WHL", "name": "FRP Manhole Cover 36 X 36 White With Lock", "category": "Manhole Cover", "size": "36x36", "color": "White", "rate": 3340, "mrp": 11454},
            # Gully Cover - Grey
            {"part_no": "RGC00001-GRY", "name": "RAKSHA Gully Cover 10 X 10 Grey", "category": "Gully Cover", "size": "10x10", "color": "Grey", "rate": 240, "mrp": 806},
            {"part_no": "RGC00002-GRY", "name": "RAKSHA Gully Cover 12 X 12 Grey", "category": "Gully Cover", "size": "12x12", "color": "Grey", "rate": 325, "mrp": 984},
            {"part_no": "RGC00003-GRY", "name": "RAKSHA Gully Cover 15 X 15 Grey", "category": "Gully Cover", "size": "15x15", "color": "Grey", "rate": 440, "mrp": 1380},
            {"part_no": "RGC00004-GRY", "name": "RAKSHA Gully Cover 18 X 18 Grey", "category": "Gully Cover", "size": "18x18", "color": "Grey", "rate": 570, "mrp": 2012},
            {"part_no": "RGC00005-GRY", "name": "RAKSHA Gully Cover 24 X 24 Grey", "category": "Gully Cover", "size": "24x24", "color": "Grey", "rate": 1160, "mrp": 3910},
            # Gully Cover - White
            {"part_no": "RGC00001-WH", "name": "RAKSHA Gully Cover 10 X 10 White", "category": "Gully Cover", "size": "10x10", "color": "White", "rate": 240, "mrp": 806},
            {"part_no": "RGC00002-WH", "name": "RAKSHA Gully Cover 12 X 12 White", "category": "Gully Cover", "size": "12x12", "color": "White", "rate": 325, "mrp": 984},
            {"part_no": "RGC00003-WH", "name": "RAKSHA Gully Cover 15 X 15 White", "category": "Gully Cover", "size": "15x15", "color": "White", "rate": 440, "mrp": 1380},
            {"part_no": "RGC00004-WH", "name": "RAKSHA Gully Cover 18 X 18 White", "category": "Gully Cover", "size": "18x18", "color": "White", "rate": 570, "mrp": 2012},
            {"part_no": "RGC00005-WH", "name": "RAKSHA Gully Cover 24 X 24 White", "category": "Gully Cover", "size": "24x24", "color": "White", "rate": 1160, "mrp": 3910},
        ]

        pid = 1
        for prod in products:
            p = Product(id=pid, part_no=prod["part_no"], name=prod["name"], category=prod["category"], size=prod["size"], load_rating="5 Ton", material="FRP", color=prod["color"], hsn_code="39259090")
            db.add(p)
            db.flush()
            db.add(Pricing(product_id=p.id, raw_material_cost=prod["rate"], total_cost=prod["rate"], profit_margin=20, gst_rate=18, mrp=prod["mrp"]))
            pid += 1

        db.commit()
        print(f"Seeded {pid - 1} products")
    finally:
        db.close()


class ProductIn(BaseModel):
    part_no: str = ""
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
    mrp: float = 0
    labor_cost: float = 0
    overhead_cost: float = 0
    packing_cost: float = 0
    profit_margin: float = 20
    gst_rate: float = 18


class CustomerIn(BaseModel):
    customer_id: str
    gstin: str = ""
    billing_address: str = ""
    shipping_address: str = ""
    state: str = ""
    district: str = ""
    city: str = ""
    pincode: str = ""
    contact_name: str = ""
    contact_number: str = ""
    contact_email: str = ""
    exec_code: str = ""
    exec_name: str = ""
    exec_number: str = ""
    exec_email: str = ""
    blacklisted: int = 0


class TransporterIn(BaseModel):
    transporter_id: str
    name: str
    phone: str
    email: str
    address: str
    state: str
    district: str
    city: str
    pincode: str
    gst_number: str
    pan_number: str
    gst_certificate: str = ""
    pan_card: str = ""
    contact_person: str
    contact_number: str
    blacklisted: int = 0


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


class OrderIn(BaseModel):
    sl_no: int = 0
    po_no: str = ""
    po_date: str = ""
    billing_site: str = ""
    shipping_site: str = ""
    no_of_boxes: int = 0
    value_excl_gst_freight: float = 0
    invoice_no: str = ""
    invoice_date: str = ""
    invoice_amount_excl_gst: float = 0
    weight_kgs: float = 0
    freight_rate_per_kg: float = 0
    transport_charges: float = 0
    invoice_amount: float = 0
    eway_bill_no: str = ""
    lr_no: str = ""
    entry_date: str = ""
    credit_note_amount: float = 0
    credit_note_no: str = ""
    transporter: str = ""
    transporter_no: str = ""


# ---- PRODUCTS ----
SIZE_ORDER = {
    "10x10": 1, "250x250": 1,
    "12x12": 2, "300x300": 2,
    "15x15": 3, "380x380": 3,
    "18x18": 4, "450x450": 4,
    "21x21": 5, "535x535": 5,
    "24x24": 6, "600x600": 6,
    "26x26": 7, "660x660": 7,
    "28x28": 8, "710x710": 8,
    "30x30": 9, "760x760": 9,
    "36x36": 10, "900x900": 10,
    "42x42": 11, "1065x1065": 11,
    "12x18": 12, "300x450": 12,
    "12x24": 13, "300x600": 13,
    "18x24": 14, "450x600": 14,
}
COLOR_ORDER = {"Grey": 0, "White": 1}
CATEGORY_ORDER = {"Manhole Cover": 0, "Gully Cover": 1}

CSV_ORDER = {pn: i for i, (pn, _) in enumerate(PART_NO_CSV)}

@app.get("/api/products")
def list_products():
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


@app.post("/api/products")
def create_product(inp: ProductIn):
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
        pr.raw_material_cost = inp.raw_material_cost
        pr.mrp = inp.mrp
        pr.gst_rate = inp.gst_rate
        db.commit()
        return {"message": "Updated", "mrp": inp.mrp}
    finally:
        db.close()


# ---- ORDERS ----
@app.get("/api/orders")
def list_orders():
    db = SessionLocal()
    try:
        rows = db.query(Order).order_by(Order.id).all()
        return [{"id": o.id, "sl_no": o.sl_no, "po_no": o.po_no, "po_date": o.po_date,
                 "billing_site": o.billing_site, "shipping_site": o.shipping_site,
                 "no_of_boxes": o.no_of_boxes, "value_excl_gst_freight": o.value_excl_gst_freight,
                 "invoice_no": o.invoice_no, "invoice_date": o.invoice_date,
                 "invoice_amount_excl_gst": o.invoice_amount_excl_gst,
                 "weight_kgs": o.weight_kgs, "freight_rate_per_kg": o.freight_rate_per_kg,
                 "transport_charges": o.transport_charges, "invoice_amount": o.invoice_amount,
                 "eway_bill_no": o.eway_bill_no, "lr_no": o.lr_no, "entry_date": o.entry_date,
                 "credit_note_amount": o.credit_note_amount, "credit_note_no": o.credit_note_no,
                 "transporter": o.transporter, "transporter_no": o.transporter_no}
                for o in rows]
    finally:
        db.close()


@app.post("/api/orders")
def create_order(inp: OrderIn):
    db = SessionLocal()
    try:
        max_sl = db.query(Order.sl_no).order_by(Order.sl_no.desc()).first()
        next_sl = (max_sl[0] + 1) if max_sl and max_sl[0] else 1
        data = inp.dict()
        data["sl_no"] = next_sl
        o = Order(**data)
        db.add(o)
        db.commit()
        db.refresh(o)
        return {"id": o.id, "sl_no": next_sl, "message": "Order created"}
    finally:
        db.close()


@app.put("/api/orders/{oid}")
def update_order(oid: int, inp: OrderIn):
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


@app.delete("/api/orders/{oid}")
def delete_order(oid: int):
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


# ---- CUSTOMERS ----
@app.get("/api/customers")
def list_customers():
    db = SessionLocal()
    try:
        rows = db.query(Customer).all()
        return [{"id": c.id, "customer_id": c.customer_id, "gstin": c.gstin,
                 "billing_address": c.billing_address, "shipping_address": c.shipping_address,
                 "state": c.state, "district": c.district, "city": c.city, "pincode": c.pincode,
                 "contact_name": c.contact_name, "contact_number": c.contact_number, "contact_email": c.contact_email,
                 "exec_code": c.exec_code, "exec_name": c.exec_name, "exec_number": c.exec_number, "exec_email": c.exec_email,
                 "blacklisted": c.blacklisted}
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


# ---- TRANSPORTERS ----
@app.get("/api/transporters")
def list_transporters():
    db = SessionLocal()
    try:
        rows = db.query(Transporter).all()
        return [{"id": t.id, "transporter_id": t.transporter_id, "name": t.name,
                 "phone": t.phone, "email": t.email, "address": t.address,
                 "state": t.state, "district": t.district, "city": t.city, "pincode": t.pincode,
                 "gst_number": t.gst_number, "pan_number": t.pan_number,
                 "gst_certificate": t.gst_certificate, "pan_card": t.pan_card,
                 "contact_person": t.contact_person, "contact_number": t.contact_number,
                 "blacklisted": t.blacklisted}
                for t in rows]
    finally:
        db.close()


@app.post("/api/transporters")
def create_transporter(inp: TransporterIn):
    db = SessionLocal()
    try:
        t = Transporter(**inp.dict())
        db.add(t)
        db.commit()
        db.refresh(t)
        return {"id": t.id, "message": "Transporter created"}
    finally:
        db.close()


@app.put("/api/transporters/{tid}")
def update_transporter(tid: int, inp: TransporterIn):
    db = SessionLocal()
    try:
        t = db.query(Transporter).filter(Transporter.id == tid).first()
        if not t:
            raise HTTPException(404, "Not found")
        for k, v in inp.dict().items():
            setattr(t, k, v)
        db.commit()
        return {"message": "Updated"}
    finally:
        db.close()


@app.get("/api/fix-urls")
def fix_urls():
    db = SessionLocal()
    try:
        rows = db.query(Transporter).all()
        fixed = 0
        for t in rows:
            changed = False
            for field in ["gst_certificate", "pan_card"]:
                url = getattr(t, field, "")
                if url and "/image/upload/" in url and url.endswith(".pdf"):
                    setattr(t, field, url.replace("/image/upload/", "/raw/upload/"))
                    changed = True
            if changed:
                fixed += 1
        db.commit()
        return {"fixed": fixed}
    finally:
        db.close()


@app.get("/api/view-file")
async def view_file(url: str = Query(...)):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
            if data[:4] == b'%PDF':
                content_type = 'application/pdf'
            elif data[:2] == b'\xff\xd8':
                content_type = 'image/jpeg'
            elif data[:8] == b'\x89PNG\r\n\x1a\n':
                content_type = 'image/png'
            else:
                content_type = resp.headers.get("Content-Type", "application/octet-stream")
            return Response(content=data, media_type=content_type, headers={
                "Content-Disposition": "inline",
            })
    except Exception as e:
        raise HTTPException(500, f"Failed to load file: {str(e)}")


@app.delete("/api/transporters/{tid}")
def delete_transporter(tid: int):
    db = SessionLocal()
    try:
        t = db.query(Transporter).filter(Transporter.id == tid).first()
        if not t:
            raise HTTPException(404, "Not found")
        db.delete(t)
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
                "customer_name": cust.contact_name if cust else "?",
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
            "pending": sum(s.total_amount for s in db.query(Sale).filter(Sale.payment_status == "Pending").all()),
            "recent_sales": [
                {"id": s.id, "invoice": s.invoice_no,
                 "customer": (db.query(Customer).filter(Customer.id == s.customer_id).first() or type("", (), {"contact_name": "?"})()).contact_name,
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


# ---- CSV IMPORT ----
def parse_csv_amount(val):
    if not val or val.strip() in ('-', '–', ''):
        return 0
    return float(str(val).replace('₹', '').replace(',', '').replace(' ', '').strip() or 0)


def parse_csv_date(val):
    if not val or val.strip() in ('-', '–', ''):
        return None
    from dateutil import parser as dateparser
    try:
        return dateparser.parse(val.strip(), dayfirst=False).strftime('%Y-%m-%d')
    except Exception:
        return val.strip() if val else None


@app.post("/api/import/orders")
async def import_orders_csv(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode('utf-8-sig')
    import csv, io
    reader = csv.DictReader(io.StringIO(text))
    db = SessionLocal()
    imported = 0
    skipped = 0
    try:
        for row in reader:
            sl_raw = row.get('Sl No.', '').strip()
            if not sl_raw:
                skipped += 1
                continue
            try:
                sl_no = int(sl_raw)
            except ValueError:
                skipped += 1
                continue
            existing = db.query(Order).filter(Order.sl_no == sl_no).first()
            data = {
                "sl_no": sl_no,
                "po_no": "",
                "po_date": parse_csv_date(row.get('PO Date', '')),
                "billing_site": row.get('Billing Site', '').strip(),
                "shipping_site": row.get('Shipping Site', '').strip(),
                "no_of_boxes": int(parse_csv_amount(row.get('No. Of Boxes', '0'))),
                "value_excl_gst_freight": parse_csv_amount(row.get('Value (excl. GST & Freight)', '0')),
                "invoice_no": row.get('Invoice No.', '').strip().replace('-', '') if row.get('Invoice No.', '').strip() not in ('-', '–', '') else '',
                "invoice_date": parse_csv_date(row.get('Invoice Date', '')),
                "invoice_amount_excl_gst": parse_csv_amount(row.get('Invoice Amount (ex. GST)', '0')),
                "weight_kgs": parse_csv_amount(row.get('Weight (Kg)', '0')),
                "freight_rate_per_kg": parse_csv_amount(row.get('Freight (Rate / Kg)', '0')),
                "transport_charges": parse_csv_amount(row.get('Transport Charges', '0')),
                "invoice_amount": parse_csv_amount(row.get('Invoice Amount', '0')),
                "eway_bill_no": row.get('E-way Bill No', '').strip() if row.get('E-way Bill No', '').strip() not in ('-', '–', '') else '',
                "lr_no": row.get('LR Copy', '').strip() if row.get('LR Copy', '').strip() not in ('-', '–', '') else '',
                "entry_date": parse_csv_date(row.get('ERP Entry Date', '')),
                "credit_note_amount": parse_csv_amount(row.get('Credit Note Amount (If any)', '0')),
                "credit_note_no": row.get('Credit Note No.', '').strip() if row.get('Credit Note No.', '').strip() not in ('-', '–', '') else '',
                "transporter": row.get('Transporter', '').strip(),
                "transporter_no": "",
            }
            if existing:
                for k, v in data.items():
                    if k != "sl_no":
                        setattr(existing, k, v)
            else:
                o = Order(**data)
                db.add(o)
            imported += 1
        db.commit()
        return {"imported": imported, "skipped": skipped, "message": f"Imported {imported} orders, skipped {skipped}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Import failed: {str(e)}")
    finally:
        db.close()


@app.post("/api/import/sales")
async def import_sales_csv(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode('utf-8-sig')
    import csv, io
    reader = csv.DictReader(io.StringIO(text))
    db = SessionLocal()
    imported = 0
    skipped = 0
    try:
        for row in reader:
            sl_raw = row.get('Sl No.', '').strip()
            if not sl_raw:
                skipped += 1
                continue
            try:
                sl_no = int(sl_raw)
            except ValueError:
                skipped += 1
                continue
            invoice_no = row.get('Raksha Invoice NO', '').strip()
            if invoice_no in ('-', '–', ''):
                invoice_no = f"INDORE-{sl_no:04d}"
            sale_date = parse_csv_date(row.get('Date ', '') or row.get('Date', ''))
            sale_date_dt = None
            if sale_date:
                try:
                    from datetime import datetime as dt
                    sale_date_dt = dt.strptime(sale_date, '%Y-%m-%d')
                except Exception:
                    pass
            freight = parse_csv_amount(row.get('Freight', '0'))
            gp = parse_csv_amount(row.get('GP', '0'))
            gp_pct_raw = row.get('GP%', '0').replace('%', '').strip()
            gp_pct = float(gp_pct_raw) if gp_pct_raw else 0
            s = Sale(
                invoice_no=invoice_no,
                sale_date=sale_date_dt,
                payment_terms=row.get('Payment Terms', '').strip(),
                party_name=row.get('Party Name ', '') or row.get('Party Name', '').strip(),
                location=row.get('Location', '').strip(),
                pincode=row.get('Pincode', '').strip(),
                state=row.get('State', '').strip(),
                transporter_name=row.get('Transporter Name', '').strip(),
                lr_no=row.get('LR No', '').strip(),
                freight_amount=freight,
                weight_kgs=parse_csv_amount(row.get('Weight', '0')),
                weight_pg_fiber=parse_csv_amount(row.get('Weight on PG Fiber Bill', '0')),
                sales_person=row.get('Sales Ex Person / Person In-Charge', '').strip(),
                pg_fiber_invoice_no=(row.get('P.G.Fiber Invoice No', '') or row.get('P.G.Fiber Invoice No ', '') or '').strip(),
                pg_fiber_invoice_value=parse_csv_amount(row.get('P.G.Fiber Invoice Value', '') or row.get('P.G.Fiber Invoice Value ', '0')),
                gp=gp,
                gp_percent=gp_pct,
                total_amount=freight,
                source_csv="From Indore",
            )
            db.add(s)
            imported += 1
        db.commit()
        return {"imported": imported, "skipped": skipped, "message": f"Imported {imported} sales, skipped {skipped}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Import failed: {str(e)}")
    finally:
        db.close()


# ---- FILE UPLOAD (Cloudinary) ----
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Only .jpg, .png, .pdf files allowed")
    try:
        content = await file.read()
        rtype = "raw" if ext == ".pdf" else "image"
        result = cloudinary.uploader.upload(
            content,
            folder="raksha_erp",
            resource_type=rtype
        )
        url = result["secure_url"]
        if rtype == "raw" and "/image/" in url:
            url = url.replace("/image/upload/", "/raw/upload/")
        return {"filename": result["public_id"], "url": url, "original": file.filename}
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {str(e)}")


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
