import re
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator


def _validate_password(v):
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
        raise ValueError("Password must contain at least one special character")
    return v


# ---- Entity Schemas ----

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
    raw_material_cost: float = Field(0, ge=0)
    mrp: float = Field(0, ge=0)
    labor_cost: float = Field(0, ge=0)
    overhead_cost: float = Field(0, ge=0)
    packing_cost: float = Field(0, ge=0)
    profit_margin: float = Field(20, ge=0)
    gst_rate: float = Field(18, ge=0)


class CustomerIn(BaseModel):
    customer_id: str
    name: str = ""
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
    tracking_url_pattern: str = ""
    blacklisted: int = 0


class SaleItemIn(BaseModel):
    product_id: int
    quantity: int = Field(0, ge=0)
    unit_price: float = Field(0, ge=0)
    discount_percent: float = Field(0, ge=0, le=100)


class SaleIn(BaseModel):
    customer_id: int
    product_id: int = 0
    quantity: int = Field(0, ge=0)
    unit_price: float = Field(0, ge=0)
    discount_percent: float = Field(0, ge=0, le=100)
    freight_amount: float = Field(0, ge=0)
    invoice_value: float = Field(0, ge=0)
    payment_status: str = "Pending"
    payment_method: str = "Cash"
    notes: str = ""
    transporter_name: str = ""
    lr_no: str = ""
    items: List[SaleItemIn] = []


class ExpenseIn(BaseModel):
    category: str
    description: str = ""
    amount: float = Field(0, ge=0)
    vendor: str = ""
    expense_date: Optional[str] = None


class OrderIn(BaseModel):
    sl_no: int = 0
    po_no: str = ""
    po_date: str = ""
    customer_name: str = ""
    billing_site: str = ""
    shipping_site: str = ""
    no_of_boxes: int = Field(0, ge=0)
    value_excl_gst_freight: float = Field(0, ge=0)
    invoice_no: str = ""
    invoice_date: str = ""
    invoice_amount_excl_gst: float = Field(0, ge=0)
    weight_kgs: float = Field(0, ge=0)
    freight_rate_per_kg: float = Field(0, ge=0)
    transport_charges: float = Field(0, ge=0)
    invoice_amount: float = Field(0, ge=0)
    eway_bill_no: str = ""
    lr_no: str = ""
    entry_date: str = ""
    credit_note_amount: float = Field(0, ge=0)
    credit_note_no: str = ""
    transporter: str = ""
    transporter_no: str = ""


class ProformaOrderItemIn(BaseModel):
    product_id: int
    part_no: str = ""
    description: str = ""
    size: str = ""
    category: str = ""
    qty_boxes: int = Field(1, ge=0)
    std_packaging: int = Field(1, ge=0)
    pieces_per_box: int = Field(1, ge=0)
    final_qty: int = Field(0, ge=0)
    mrp: float = Field(0, ge=0)
    d1: float = Field(0, ge=0, le=100)
    d2: float = Field(0, ge=0, le=100)
    d3: float = Field(0, ge=0, le=100)
    d4: float = Field(0, ge=0, le=100)
    d5: float = Field(0, ge=0, le=100)
    cd: float = Field(0, ge=0, le=100)
    discount_percent: float = Field(0, ge=0, le=100)
    net_rate: float = Field(0, ge=0)
    lock_hinge: int = Field(0, ge=0)
    basic_amount: float = Field(0, ge=0)


class ProformaOrderIn(BaseModel):
    customer_id: int
    billing_site: str = ""
    shipping_site: str = ""
    freight_amount: float = Field(0, ge=0)
    payment_status: str = "Pending"
    payment_method: str = "Cash"
    transport_mode: str = ""
    delivery_days: int = Field(30, ge=0)
    notes: str = ""
    terms: str = ""
    order_type: str = "PI"
    discount_scheme_applied: int = 0
    items: List[ProformaOrderItemIn] = []


# ---- Auth Schemas ----

class LoginIn(BaseModel):
    username: str
    password: str

class RefreshIn(BaseModel):
    refresh_token: str

class LogoutIn(BaseModel):
    refresh_token: Optional[str] = None

class UserCreateIn(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: str = ""
    email: str = ""
    role: Literal["admin", "manager", "viewer"] = "viewer"

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        return _validate_password(v)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v and not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", v):
            raise ValueError("Invalid email format")
        return v

class UserUpdateIn(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[int] = None
    password: Optional[str] = None

class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        return _validate_password(v)


# ---- Purchase Rate Schemas ----

class PurchaseRateIn(BaseModel):
    product_id: int
    rate: float = Field(0, ge=0)
    supplier: str = ""
    effective_date: Optional[str] = None

class PurchaseRateUpdateIn(BaseModel):
    rate: float = Field(0, ge=0)
    supplier: str = ""
    effective_date: Optional[str] = None

class BulkPurchaseRateIn(BaseModel):
    rates: List[PurchaseRateIn]


# ---- Misc Schemas ----

class TransportUpdateIn(BaseModel):
    transport_cost: float = Field(0, ge=0)

class OrderStatusIn(BaseModel):
    status: str

class WhatsAppSendIn(BaseModel):
    phone: str = Field(..., pattern=r"^\d{10,15}$")
    message: str = ""

class WhatsAppSendPIIn(BaseModel):
    phone: str = Field(..., pattern=r"^\d{10,15}$")

class WhatsAppSendPOIn(BaseModel):
    phone: str = Field(..., pattern=r"^\d{10,15}$")

class WhatsAppTestIn(BaseModel):
    phone: str = Field(..., pattern=r"^\d{10,15}$")

class SaleInvoiceIn(BaseModel):
    invoice_no: str = ""
    invoice_value: float = Field(0, ge=0)

class BulkPaymentIn(BaseModel):
    ids: List[int]
    status: str

class BulkLRIn(BaseModel):
    ids: List[int]
    lr_no: str = ""

class LRTrackingIn(BaseModel):
    lr_no: str = ""
    tracking_url: str = ""

class SettingsUpdateIn(BaseModel):
    settings: dict
