from datetime import datetime, date, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base


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
    pieces_per_box = Column(Integer, default=1)
    std_packaging = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
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
    name = Column(String, default="")
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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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
    tracking_url_pattern = Column(String, default="")
    blacklisted = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    invoice_no = Column(String)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True, index=True)
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
    invoice_value = Column(Float, default=0)
    source_csv = Column(String, default="")
    lr_tracking_status = Column(String, default="")
    lr_tracking_url = Column(String, default="")
    lr_last_checked = Column(DateTime, nullable=True)
    customer = relationship("Customer")
    product = relationship("Product")
    items = relationship("SaleItem", cascade="all,delete-orphan", back_populates="sale")


class SaleItem(Base):
    __tablename__ = "sale_items"
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), index=True)
    sl_no = Column(Integer, default=1)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    quantity = Column(Integer, default=0)
    unit_price = Column(Float, default=0)
    discount_percent = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    taxable_amount = Column(Float, default=0)
    gst_rate = Column(Float, default=18)
    cgst_amount = Column(Float, default=0)
    sgst_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    basic_amount = Column(Float, default=0)
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")


class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String)
    description = Column(String, default="")
    amount = Column(Float)
    vendor = Column(String, default="")
    expense_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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
    full_name = Column(String, default="")
    email = Column(String, default="")
    role = Column(String, default="viewer")
    is_active = Column(Integer, default=1)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    sl_no = Column(Integer, default=0)
    po_no = Column(String, default="")
    po_date = Column(String, default="")
    customer_name = Column(String, default="")
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


class ProformaOrder(Base):
    __tablename__ = "proforma_orders"
    id = Column(Integer, primary_key=True, index=True)
    pi_no = Column(String, unique=True)
    pi_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    billing_site = Column(String, default="")
    shipping_site = Column(String, default="")
    no_of_boxes = Column(Integer, default=0)
    total_qty = Column(Integer, default=0)
    value_excl_gst = Column(Float, default=0)
    gst_amount = Column(Float, default=0)
    total_amount = Column(Float, default=0)
    freight_amount = Column(Float, default=0)
    payment_status = Column(String, default="Pending")
    payment_method = Column(String, default="Cash")
    transport_mode = Column(String, default="")
    delivery_days = Column(Integer, default=30)
    notes = Column(String, default="")
    terms = Column(Text, default="")
    order_type = Column(String, default="PI")
    po_no = Column(String, default="")
    po_date = Column(DateTime, nullable=True)
    purchase_total = Column(Float, default=0)
    transport_cost = Column(Float, default=0)
    gross_profit = Column(Float, default=0)
    net_profit = Column(Float, default=0)
    transporter_id = Column(Integer, ForeignKey("transporters.id"), nullable=True, index=True)
    whatsapp_status = Column(String, default="pending")
    status = Column(String, default="draft")
    discount_scheme_applied = Column(Integer, default=0)
    discount_percent = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    customer = relationship("Customer")
    items = relationship("ProformaOrderItem", back_populates="proforma_order", cascade="all,delete-orphan")


class ProformaOrderItem(Base):
    __tablename__ = "proforma_order_items"
    id = Column(Integer, primary_key=True, index=True)
    proforma_order_id = Column(Integer, ForeignKey("proforma_orders.id"), index=True)
    sl_no = Column(Integer)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    part_no = Column(String, default="")
    description = Column(String, default="")
    size = Column(String, default="")
    category = Column(String, default="")
    qty_boxes = Column(Integer, default=1)
    std_packaging = Column(Integer, default=1)
    pieces_per_box = Column(Integer, default=1)
    final_qty = Column(Integer, default=0)
    mrp = Column(Float, default=0)
    d1 = Column(Float, default=0)
    d2 = Column(Float, default=0)
    d3 = Column(Float, default=0)
    d4 = Column(Float, default=0)
    d5 = Column(Float, default=0)
    cd = Column(Float, default=0)
    discount_percent = Column(Float, default=0)
    net_rate = Column(Float, default=0)
    lock_hinge = Column(Integer, default=0)
    basic_amount = Column(Float, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    proforma_order = relationship("ProformaOrder", back_populates="items")
    product = relationship("Product")


class BillingSite(Base):
    __tablename__ = "billing_sites"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, default="")
    phone = Column(String, default="")
    email = Column(String, default="")
    website = Column(String, default="")
    gstin = Column(String, default="")
    state_code = Column(String, default="")
    pan = Column(String, default="")


class PurchaseRate(Base):
    __tablename__ = "purchase_rates"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), index=True)
    rate = Column(Float, default=0)
    supplier = Column(String, default="")
    effective_date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    product = relationship("Product")


class TransporterQuote(Base):
    __tablename__ = "transporter_quotes"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("proforma_orders.id"), index=True)
    transporter_id = Column(Integer, ForeignKey("transporters.id"), index=True)
    rate_per_kg = Column(Float, default=0)
    total_cost = Column(Float, default=0)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    proforma_order = relationship("ProformaOrder")
    transporter = relationship("Transporter")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String, default="")
    action = Column(String, nullable=False)
    resource = Column(String, default="")
    resource_id = Column(String, default="")
    details = Column(Text, default="")
    ip_address = Column(String, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(Text, nullable=False)
    user_id = Column(Integer, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, index=True)
    ip_address = Column(String, default="")
    success = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
