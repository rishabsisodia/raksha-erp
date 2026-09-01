import os
import re
import bcrypt
import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from .config import (
    JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS,
    ROLE_PERMISSIONS, ALLOWED_EXTENSIONS, DEFAULT_GST_RATE, TCS_RATE,
    WHATSAPP_API_VERSION, WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, WHATSAPP_BUSINESS_ACCOUNT_ID,
    WHATSAPP_API_URL, CLOUDINARY_URL, MAX_UPLOAD_SIZE
)
from .database import engine, SessionLocal, Base
from .models import User, Product, Settings, BillingSite
from .auth import get_current_user, require_permission, audit_log

from .routes.customers import router as customers_router
from .routes.transporters import router as transporters_router
from .routes.products import router as products_router
from .routes.expenses import router as expenses_router
from .routes.sales import router as sales_router
from .routes.orders import router as orders_router
from .routes.tracking import router as tracking_router
from .routes.whatsapp import router as whatsapp_router
from .routes.imports import router as imports_router
from .routes.exports import router as exports_router
from .routes.reports import router as reports_router
from .routes.auth_routes import router as auth_router

logger = logging.getLogger("raksha-erp")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Raksha ERP")

# --- Rate limiter (fix #3) ---
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
    status_code=429, content={"detail": "Too many requests. Please try again later."}
))
app.add_middleware(SlowAPIMiddleware)

# --- CORS from env var (fix #5) with preflight cache (fix #19) ---
_cors_origins = os.environ.get("CORS_ORIGINS", "https://raksha-erp-deploy.onrender.com").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)

# --- Security headers middleware (fix #12) + HTTPS enforcement (fix #13) ---
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "0"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; img-src 'self' data: blob: https:; connect-src 'self';"
    if not request.url.scheme == "https" and request.headers.get("x-forwarded-proto", "https") != "https":
        if os.environ.get("ENVIRONMENT") == "production":
            return JSONResponse(status_code=301, content={"detail": "HTTPS required"}, headers={"Strict-Transport-Security": "max-age=31536000; includeSubDomains"})
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# --- Upload size limit middleware (fix #20) ---
@app.middleware("http")
async def upload_size_limit_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_SIZE:
        if request.url.path.startswith("/api/") and request.method in ("POST", "PUT", "PATCH"):
            return JSONResponse(status_code=413, content={"detail": f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024*1024)}MB"})
    return await call_next(request)


# --- Startup helpers (backfill, seed) ---

PIECES_PER_BOX_MAP = {
    "10x10": 12, "12x12": 6, "15x15": 6, "18x18": 4,
    "21x21": 3, "24x24": 2, "26x26": 1, "28x28": 1,
    "30x30": 1, "36x36": 1, "42x42": 1,
    "12x18": 6, "12x24": 5, "18x24": 3,
    "250x250": 12, "300x300": 6, "380x380": 6, "450x450": 4,
    "530x530": 3, "600x600": 2, "660x660": 1, "700x700": 1, "710x710": 1,
    "750x750": 1, "900x900": 1, "1060x1060": 1, "1065x1065": 1,
    "300x450": 6, "300x600": 5, "450x600": 3,
}

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


def generate_part_no(product):
    if product.part_no:
        return product.part_no
    name_lower = (product.name or "").lower()
    size = (product.size or "").lower().replace(" ", "")
    color = (product.color or "").lower()
    has_lock = "lock" in name_lower
    has_hinges = "hinge" in name_lower
    is_gully = "gully" in name_lower
    is_10ton = "10 ton" in name_lower

    size_dim_map = {
        "250x250": ("10x10", "10x10"), "300x300": ("12x12", "12x12"),
        "380x380": ("15x15", "15x15"), "450x450": ("18x18", "18x18"),
        "535x535": ("21x21", "21x21"), "600x600": ("24x24", "24x24"),
        "660x660": ("26x26", "26x26"), "710x710": ("28x28", "28x28"),
        "760x760": ("30x30", "30x30"), "900x900": ("36x36", "36x36"),
        "1065x1065": ("42x42", "42x42"),
        "300x450": ("12x18", "12x18"), "300x600": ("12x24", "12x24"),
        "450x600": ("18x24", "18x24"),
    }
    nominal = size_dim_map.get(size)
    if not nominal:
        m = re.search(r'(\d+)\s*x\s*(\d+)', product.size or product.name or "")
        if m:
            nominal = (f"{m.group(1)}x{m.group(2)}", f"{m.group(1)}x{m.group(2)}")
        else:
            return ""

    nom_lower = nominal[0]
    color_name = "White" if "white" in color else "Grey"
    tonnage = "10 Ton" if is_10ton else "5 Ton"

    suffix = ""
    if has_hinges and has_lock:
        suffix = " (Double Hinges & Lock)"
    elif has_hinges:
        suffix = " (Double Hinges)"
    elif has_lock:
        suffix = " (with Lock)"

    prefix = "RGC" if is_gully else "FRP"
    if is_gully:
        csv_desc = f"Raksha FRP Gully Cover {nom_lower} - {color_name}{suffix}"
    else:
        csv_desc = f"Raksha FRP Manhole Cover {nom_lower} - {tonnage} {color_name}{suffix}"

    for pn, desc in PART_NO_CSV:
        if desc.strip().lower() == csv_desc.strip().lower():
            return pn

    num = re.search(r'(\d+)', nom_lower)
    num_str = num.group(1).zfill(5) if num else "00000"
    return f"{prefix}{num_str}-{'WH' if 'white' in color else 'GRY'}"


def get_new_product_name(part_no, old_name=""):
    pn = (part_no or "").upper().replace(" ", "")
    is_gully = pn.startswith("RGC")
    is_10ton = pn.startswith("FRP012")

    suffix = ""
    if pn.endswith("/H&L"):
        suffix = " (Double Hinges & Lock)"
    elif pn.endswith("H") and not pn.endswith("-WH"):
        suffix = " (Double Hinges)"
    elif pn.endswith("L") and "GRY" not in pn[-4:]:
        suffix = " (with Lock)"

    color = "White" if "-WH" in pn else "Grey"

    size_map = {
        "FRP01101": "10x10", "FRP01103": "12x12", "FRP01106": "15x15",
        "FRP01109": "18x18", "FRP01112": "21x21", "FRP01115": "24x24",
        "FRP01117": "26x26", "FRP01119": "28x28", "FRP01121": "30x30",
        "FRP01127": "36x36", "FRP04106": "12x18", "FRP04112": "12x24",
        "FRP10106": "18x24", "FRP01209": "18x18", "FRP01215": "24x24",
        "FRP01219": "28x28", "FRP01221": "30x30", "FRP01233": "42x42",
        "RGC00001": "10x10", "RGC00002": "12x12", "RGC00003": "15x15",
        "RGC00004": "18x18", "RGC00005": "24x24",
    }

    size = ""
    for prefix_key, sz in size_map.items():
        if pn.startswith(prefix_key):
            size = sz
            break

    if not size:
        m = re.search(r"(\d+)\s*[xX]\s*(\d+)", old_name or "")
        if m:
            size = f"{m.group(1)}x{m.group(2)}"

    if is_gully:
        return f"Raksha FRP Gully Cover {size} - {color}{suffix}"

    tonnage = "10 Ton" if is_10ton else "5 Ton"
    return f"Raksha FRP Manhole Cover {size} - {tonnage} {color}{suffix}"


def backfill_pieces_per_box():
    db = SessionLocal()
    try:
        products = db.query(Product).all()
        updated = 0
        for p in products:
            size_lower = (p.size or "").lower().replace(" ", "")
            ppb = PIECES_PER_BOX_MAP.get(size_lower)
            if ppb and p.pieces_per_box != ppb:
                p.pieces_per_box = ppb
                p.std_packaging = ppb
                updated += 1
            pn = (p.part_no or "").upper().replace(" ", "")
            if pn.startswith("FRP012"):
                if p.load_rating != "10 Ton":
                    p.load_rating = "10 Ton"
                    updated += 1
            elif pn.startswith("FRP01") or pn.startswith("FRP04") or pn.startswith("FRP10"):
                if p.load_rating != "5 Ton" or not p.load_rating:
                    p.load_rating = "5 Ton"
                    updated += 1
        if updated:
            db.commit()
            logger.info(f"Backfilled pieces_per_box and tonnage for {updated} products")
    finally:
        db.close()


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
            logger.info(f"Backfilled part_no for {updated} products")
    finally:
        db.close()


def backfill_product_names():
    db = SessionLocal()
    try:
        updated = 0
        for p in db.query(Product).all():
            new_name = get_new_product_name(p.part_no, p.name)
            if new_name and new_name != p.name:
                p.name = new_name
                updated += 1
        if updated:
            db.commit()
            logger.info(f"Backfilled product names for {updated} products")
    finally:
        db.close()


def seed_data():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        admin_password = os.environ.get("ADMIN_PASSWORD")
        if not admin:
            if not admin_password:
                if os.environ.get("ENVIRONMENT") == "production":
                    logger.critical("ADMIN_PASSWORD env var not set and no admin user exists. Cannot seed admin account.")
                    raise RuntimeError("ADMIN_PASSWORD environment variable is required on first run")
                else:
                    admin_password = "RS@2026"
                    logger.warning("ADMIN_PASSWORD not set — using dev default. Set ADMIN_PASSWORD for production.")
            pw_hash = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt()).decode()
            admin = User(username="admin", password_hash=pw_hash, full_name="Administrator", email="admin@raksha.com", role="admin", is_active=1)
            db.add(admin)
            db.commit()
            logger.info("Admin user seeded from ADMIN_PASSWORD env var")
        elif not admin.password_hash.startswith("$2"):
            if not admin_password:
                if os.environ.get("ENVIRONMENT") == "production":
                    logger.warning("Admin password hash is not bcrypt format, but ADMIN_PASSWORD not set. Skipping rehash.")
                else:
                    admin_password = "RS@2026"
            if admin_password:
                admin.password_hash = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt()).decode()
                admin.role = "admin"
                admin.full_name = admin.full_name or "Administrator"
                db.commit()
                logger.info("Admin password rehashed from ADMIN_PASSWORD env var")

        if db.query(Product).count() > 0:
            return

        products = [
            {"part_no": "FRP01101-GRY", "name": "Raksha FRP Manhole Cover 10x10 - 5 Ton Grey", "category": "Manhole Cover", "size": "10x10", "color": "Grey", "rate": 190, "mrp": 686, "ppb": 12, "tonnage": "5 Ton"},
            {"part_no": "FRP01103-GRY", "name": "Raksha FRP Manhole Cover 12x12 - 5 Ton Grey", "category": "Manhole Cover", "size": "12x12", "color": "Grey", "rate": 242, "mrp": 830, "ppb": 6, "tonnage": "5 Ton"},
            {"part_no": "FRP01106-GRY", "name": "Raksha FRP Manhole Cover 15x15 - 5 Ton Grey", "category": "Manhole Cover", "size": "15x15", "color": "Grey", "rate": 310, "mrp": 1046, "ppb": 6, "tonnage": "5 Ton"},
            {"part_no": "FRP01109-GRY", "name": "Raksha FRP Manhole Cover 18x18 - 5 Ton Grey", "category": "Manhole Cover", "size": "18x18", "color": "Grey", "rate": 455, "mrp": 1536, "ppb": 4, "tonnage": "5 Ton"},
            {"part_no": "FRP01112-GRY", "name": "Raksha FRP Manhole Cover 21x21 - 5 Ton Grey", "category": "Manhole Cover", "size": "21x21", "color": "Grey", "rate": 640, "mrp": 2130, "ppb": 3, "tonnage": "5 Ton"},
            {"part_no": "FRP01115-GRY", "name": "Raksha FRP Manhole Cover 24x24 - 5 Ton Grey", "category": "Manhole Cover", "size": "24x24", "color": "Grey", "rate": 765, "mrp": 2560, "ppb": 2, "tonnage": "5 Ton"},
            {"part_no": "FRP01117-GRY", "name": "Raksha FRP Manhole Cover 26x26 - 5 Ton Grey", "category": "Manhole Cover", "size": "26x26", "color": "Grey", "rate": 1130, "mrp": 3266, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP01119-GRY", "name": "Raksha FRP Manhole Cover 28x28 - 5 Ton Grey", "category": "Manhole Cover", "size": "28x28", "color": "Grey", "rate": 1500, "mrp": 4934, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP01121-GRY", "name": "Raksha FRP Manhole Cover 30x30 - 5 Ton Grey", "category": "Manhole Cover", "size": "30x30", "color": "Grey", "rate": 1750, "mrp": 5854, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP01127-GRY", "name": "Raksha FRP Manhole Cover 36x36 - 5 Ton Grey", "category": "Manhole Cover", "size": "36x36", "color": "Grey", "rate": 3200, "mrp": 11454, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP04106-GRY", "name": "Raksha FRP Manhole Cover 12x18 - 5 Ton Grey", "category": "Manhole Cover", "size": "12x18", "color": "Grey", "rate": 350, "mrp": 1154, "ppb": 6, "tonnage": "5 Ton"},
            {"part_no": "FRP04112-GRY", "name": "Raksha FRP Manhole Cover 12x24 - 5 Ton Grey", "category": "Manhole Cover", "size": "12x24", "color": "Grey", "rate": 500, "mrp": 1624, "ppb": 5, "tonnage": "5 Ton"},
            {"part_no": "FRP10106-GRY", "name": "Raksha FRP Manhole Cover 18x24 - 5 Ton Grey", "category": "Manhole Cover", "size": "18x24", "color": "Grey", "rate": 620, "mrp": 2020, "ppb": 3, "tonnage": "5 Ton"},
            {"part_no": "FRP01101-WH", "name": "Raksha FRP Manhole Cover 10x10 - 5 Ton White", "category": "Manhole Cover", "size": "10x10", "color": "White", "rate": 190, "mrp": 686, "ppb": 12, "tonnage": "5 Ton"},
            {"part_no": "FRP01103-WH", "name": "Raksha FRP Manhole Cover 12x12 - 5 Ton White", "category": "Manhole Cover", "size": "12x12", "color": "White", "rate": 242, "mrp": 830, "ppb": 6, "tonnage": "5 Ton"},
            {"part_no": "FRP01106-WH", "name": "Raksha FRP Manhole Cover 15x15 - 5 Ton White", "category": "Manhole Cover", "size": "15x15", "color": "White", "rate": 310, "mrp": 1046, "ppb": 6, "tonnage": "5 Ton"},
            {"part_no": "FRP01109-WH", "name": "Raksha FRP Manhole Cover 18x18 - 5 Ton White", "category": "Manhole Cover", "size": "18x18", "color": "White", "rate": 455, "mrp": 1536, "ppb": 4, "tonnage": "5 Ton"},
            {"part_no": "FRP01112-WH", "name": "Raksha FRP Manhole Cover 21x21 - 5 Ton White", "category": "Manhole Cover", "size": "21x21", "color": "White", "rate": 640, "mrp": 2130, "ppb": 3, "tonnage": "5 Ton"},
            {"part_no": "FRP01115-WH", "name": "Raksha FRP Manhole Cover 24x24 - 5 Ton White", "category": "Manhole Cover", "size": "24x24", "color": "White", "rate": 765, "mrp": 2560, "ppb": 2, "tonnage": "5 Ton"},
            {"part_no": "FRP01117-WH", "name": "Raksha FRP Manhole Cover 26x26 - 5 Ton White", "category": "Manhole Cover", "size": "26x26", "color": "White", "rate": 1130, "mrp": 3266, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP01119-WH", "name": "Raksha FRP Manhole Cover 28x28 - 5 Ton White", "category": "Manhole Cover", "size": "28x28", "color": "White", "rate": 1500, "mrp": 4934, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP01121-WH", "name": "Raksha FRP Manhole Cover 30x30 - 5 Ton White", "category": "Manhole Cover", "size": "30x30", "color": "White", "rate": 1750, "mrp": 5854, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP01127-WH", "name": "Raksha FRP Manhole Cover 36x36 - 5 Ton White", "category": "Manhole Cover", "size": "36x36", "color": "White", "rate": 3200, "mrp": 11454, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP04106-WH", "name": "Raksha FRP Manhole Cover 12x18 - 5 Ton White", "category": "Manhole Cover", "size": "12x18", "color": "White", "rate": 350, "mrp": 1154, "ppb": 6, "tonnage": "5 Ton"},
            {"part_no": "FRP04112-WH", "name": "Raksha FRP Manhole Cover 12x24 - 5 Ton White", "category": "Manhole Cover", "size": "12x24", "color": "White", "rate": 500, "mrp": 1624, "ppb": 5, "tonnage": "5 Ton"},
            {"part_no": "FRP10106-WH", "name": "Raksha FRP Manhole Cover 18x24 - 5 Ton White", "category": "Manhole Cover", "size": "18x24", "color": "White", "rate": 620, "mrp": 2020, "ppb": 3, "tonnage": "5 Ton"},
            {"part_no": "FRP01112-GRYL", "name": "Raksha FRP Manhole Cover 21x21 - 5 Ton Grey (with Lock)", "category": "Manhole Cover", "size": "21x21", "color": "Grey", "rate": 710, "mrp": 2130, "ppb": 3, "tonnage": "5 Ton"},
            {"part_no": "FRP01115-GRYL", "name": "Raksha FRP Manhole Cover 24x24 - 5 Ton Grey (with Lock)", "category": "Manhole Cover", "size": "24x24", "color": "Grey", "rate": 835, "mrp": 2560, "ppb": 2, "tonnage": "5 Ton"},
            {"part_no": "FRP01117-GRYL", "name": "Raksha FRP Manhole Cover 26x26 - 5 Ton Grey (with Lock)", "category": "Manhole Cover", "size": "26x26", "color": "Grey", "rate": 1270, "mrp": 3266, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP01119-GRYL", "name": "Raksha FRP Manhole Cover 28x28 - 5 Ton Grey (with Lock)", "category": "Manhole Cover", "size": "28x28", "color": "Grey", "rate": 1640, "mrp": 4934, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP01121-GRYL", "name": "Raksha FRP Manhole Cover 30x30 - 5 Ton Grey (with Lock)", "category": "Manhole Cover", "size": "30x30", "color": "Grey", "rate": 1890, "mrp": 5854, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP01127-GRYL", "name": "Raksha FRP Manhole Cover 36x36 - 5 Ton Grey (with Lock)", "category": "Manhole Cover", "size": "36x36", "color": "Grey", "rate": 3340, "mrp": 11454, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP01112-WHL", "name": "Raksha FRP Manhole Cover 21x21 - 5 Ton White (with Lock)", "category": "Manhole Cover", "size": "21x21", "color": "White", "rate": 710, "mrp": 2130, "ppb": 3, "tonnage": "5 Ton"},
            {"part_no": "FRP01115-WHL", "name": "Raksha FRP Manhole Cover 24x24 - 5 Ton White (with Lock)", "category": "Manhole Cover", "size": "24x24", "color": "White", "rate": 835, "mrp": 2560, "ppb": 2, "tonnage": "5 Ton"},
            {"part_no": "FRP01117-WHL", "name": "Raksha FRP Manhole Cover 26x26 - 5 Ton White (with Lock)", "category": "Manhole Cover", "size": "26x26", "color": "White", "rate": 1270, "mrp": 3266, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP01119-WHL", "name": "Raksha FRP Manhole Cover 28x28 - 5 Ton White (with Lock)", "category": "Manhole Cover", "size": "28x28", "color": "White", "rate": 1640, "mrp": 4934, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP01121-WHL", "name": "Raksha FRP Manhole Cover 30x30 - 5 Ton White (with Lock)", "category": "Manhole Cover", "size": "30x30", "color": "White", "rate": 1890, "mrp": 5854, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP01127-WHL", "name": "Raksha FRP Manhole Cover 36x36 - 5 Ton White (with Lock)", "category": "Manhole Cover", "size": "36x36", "color": "White", "rate": 3340, "mrp": 11454, "ppb": 1, "tonnage": "5 Ton"},
            {"part_no": "FRP01115-GRYH", "name": "Raksha FRP Manhole Cover 24x24 - 5 Ton Grey (Double Hinges)", "category": "Manhole Cover", "size": "24x24", "color": "Grey", "rate": 835, "mrp": 2560, "ppb": 2, "tonnage": "5 Ton"},
            {"part_no": "FRP01115-WHH", "name": "Raksha FRP Manhole Cover 24x24 - 5 Ton White (Double Hinges)", "category": "Manhole Cover", "size": "24x24", "color": "White", "rate": 835, "mrp": 2560, "ppb": 2, "tonnage": "5 Ton"},
            {"part_no": "FRP01115-GRY/H&L", "name": "Raksha FRP Manhole Cover 24x24 - 5 Ton Grey (Double Hinges & Lock)", "category": "Manhole Cover", "size": "24x24", "color": "Grey", "rate": 910, "mrp": 2560, "ppb": 2, "tonnage": "5 Ton"},
            {"part_no": "FRP01115-WH/H&L", "name": "Raksha FRP Manhole Cover 24x24 - 5 Ton White (Double Hinges & Lock)", "category": "Manhole Cover", "size": "24x24", "color": "White", "rate": 910, "mrp": 2560, "ppb": 2, "tonnage": "5 Ton"},
            {"part_no": "FRP01209-GRY", "name": "Raksha FRP Manhole Cover 18x18 - 10 Ton Grey", "category": "Manhole Cover", "size": "18x18", "color": "Grey", "rate": 680, "mrp": 2130, "ppb": 4, "tonnage": "10 Ton"},
            {"part_no": "FRP01215-GRY", "name": "Raksha FRP Manhole Cover 24x24 - 10 Ton Grey", "category": "Manhole Cover", "size": "24x24", "color": "Grey", "rate": 1150, "mrp": 3666, "ppb": 2, "tonnage": "10 Ton"},
            {"part_no": "FRP01219-GRY", "name": "Raksha FRP Manhole Cover 28x28 - 10 Ton Grey", "category": "Manhole Cover", "size": "28x28", "color": "Grey", "rate": 2200, "mrp": 6528, "ppb": 1, "tonnage": "10 Ton"},
            {"part_no": "FRP01221-GRY", "name": "Raksha FRP Manhole Cover 30x30 - 10 Ton Grey", "category": "Manhole Cover", "size": "30x30", "color": "Grey", "rate": 2600, "mrp": 7720, "ppb": 1, "tonnage": "10 Ton"},
            {"part_no": "FRP01233-GRY", "name": "Raksha FRP Manhole Cover 42x42 - 10 Ton Grey", "category": "Manhole Cover", "size": "42x42", "color": "Grey", "rate": 5000, "mrp": 14832, "ppb": 1, "tonnage": "10 Ton"},
            {"part_no": "FRP01209-WH", "name": "Raksha FRP Manhole Cover 18x18 - 10 Ton White", "category": "Manhole Cover", "size": "18x18", "color": "White", "rate": 680, "mrp": 2130, "ppb": 4, "tonnage": "10 Ton"},
            {"part_no": "FRP01215-WH", "name": "Raksha FRP Manhole Cover 24x24 - 10 Ton White", "category": "Manhole Cover", "size": "24x24", "color": "White", "rate": 1150, "mrp": 3666, "ppb": 2, "tonnage": "10 Ton"},
            {"part_no": "FRP01219-WH", "name": "Raksha FRP Manhole Cover 28x28 - 10 Ton White", "category": "Manhole Cover", "size": "28x28", "color": "White", "rate": 2200, "mrp": 6528, "ppb": 1, "tonnage": "10 Ton"},
            {"part_no": "FRP01221-WH", "name": "Raksha FRP Manhole Cover 30x30 - 10 Ton White", "category": "Manhole Cover", "size": "30x30", "color": "White", "rate": 2600, "mrp": 7720, "ppb": 1, "tonnage": "10 Ton"},
            {"part_no": "FRP01233-WH", "name": "Raksha FRP Manhole Cover 42x42 - 10 Ton White", "category": "Manhole Cover", "size": "42x42", "color": "White", "rate": 5000, "mrp": 14832, "ppb": 1, "tonnage": "10 Ton"},
            {"part_no": "RGC00001-GRY", "name": "Raksha FRP Gully Cover 10x10 - Grey", "category": "Gully Cover", "size": "10x10", "color": "Grey", "rate": 190, "mrp": 686, "ppb": 12, "tonnage": ""},
            {"part_no": "RGC00002-GRY", "name": "Raksha FRP Gully Cover 12x12 - Grey", "category": "Gully Cover", "size": "12x12", "color": "Grey", "rate": 242, "mrp": 830, "ppb": 6, "tonnage": ""},
            {"part_no": "RGC00003-GRY", "name": "Raksha FRP Gully Cover 15x15 - Grey", "category": "Gully Cover", "size": "15x15", "color": "Grey", "rate": 310, "mrp": 1046, "ppb": 6, "tonnage": ""},
            {"part_no": "RGC00004-GRY", "name": "Raksha FRP Gully Cover 18x18 - Grey", "category": "Gully Cover", "size": "18x18", "color": "Grey", "rate": 455, "mrp": 1536, "ppb": 4, "tonnage": ""},
            {"part_no": "RGC00005-GRY", "name": "Raksha FRP Gully Cover 24x24 - Grey", "category": "Gully Cover", "size": "24x24", "color": "Grey", "rate": 765, "mrp": 2560, "ppb": 2, "tonnage": ""},
            {"part_no": "RGC00001-WH", "name": "Raksha FRP Gully Cover 10x10 - White", "category": "Gully Cover", "size": "10x10", "color": "White", "rate": 190, "mrp": 686, "ppb": 12, "tonnage": ""},
            {"part_no": "RGC00002-WH", "name": "Raksha FRP Gully Cover 12x12 - White", "category": "Gully Cover", "size": "12x12", "color": "White", "rate": 242, "mrp": 830, "ppb": 6, "tonnage": ""},
            {"part_no": "RGC00003-WH", "name": "Raksha FRP Gully Cover 15x15 - White", "category": "Gully Cover", "size": "15x15", "color": "White", "rate": 310, "mrp": 1046, "ppb": 6, "tonnage": ""},
            {"part_no": "RGC00004-WH", "name": "Raksha FRP Gully Cover 18x18 - White", "category": "Gully Cover", "size": "18x18", "color": "White", "rate": 455, "mrp": 1536, "ppb": 4, "tonnage": ""},
            {"part_no": "RGC00005-WH", "name": "Raksha FRP Gully Cover 24x24 - White", "category": "Gully Cover", "size": "24x24", "color": "White", "rate": 765, "mrp": 2560, "ppb": 2, "tonnage": ""},
        ]
        for pdata in products:
            from .models import Pricing
            p = Product(
                part_no=pdata["part_no"], name=pdata["name"], category=pdata["category"],
                size=pdata["size"], load_rating=pdata.get("tonnage", ""), material="FRP",
                color=pdata["color"], unit="Nos", pieces_per_box=pdata.get("ppb", 1),
                std_packaging=pdata.get("ppb", 1)
            )
            db.add(p)
            db.flush()
            pricing = Pricing(product_id=p.id, mrp=pdata.get("mrp", 0), gst_rate=18, profit_margin=20)
            db.add(pricing)
        db.commit()
        logger.info(f"Seeded {len(products)} products with pricing")
    finally:
        db.close()


def seed_billing_sites():
    db = SessionLocal()
    try:
        if db.query(BillingSite).count() > 0:
            return
        sites = [
            {"name": "Diamond Pipes & Tubes Private Limited - Unit 1", "address": "No - 209/394, Hosur Main Road, Chandapur, Bangalore - 560081", "phone": "9341329825", "email": "spi@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "29AAECS9353F1Z0", "state_code": "29", "pan": "AAECS9353F"},
            {"name": "Diamond Pipes & Tubes Private Limited - Unit 2", "address": "No.195/2, 74/74/1, 115/67/1, 81/81/1, Chikkanahalli Road, Bommanahalli, Bengaluru - 560068", "phone": "9341985236", "email": "pi@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "29AAACD5818Q1Z2", "state_code": "29", "pan": "AAACD5818Q"},
            {"name": "Diamond Pipes & Tubes Private Limited - Unit 3", "address": "S.No.70 / 2B,Daman Industrial Estate, Kadaiya, Daman - 396210", "phone": "8306340710", "email": "bds@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "26AAACD5818Q1Z8", "state_code": "26", "pan": "AAACD5818Q"},
            {"name": "Shand Pipe Industry Private Limited - Unit 1", "address": "Industrial Area, Hosur Road, Bommasandra, Bangalore - 560099", "phone": "7815833361", "email": "dpt@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "29ABJPS4076L1ZV", "state_code": "29", "pan": "ABJPS4076L"},
            {"name": "Shand Pipe Industry Private Limited - Unit 2", "address": "Sy. No. 168, Madivala Village, Kasba Hobli, Anekal Taluk, Bengaluru - 562106", "phone": "7815833361", "email": "dpt@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "29ABJPS4076L1ZV", "state_code": "29", "pan": "ABJPS4076L"},
            {"name": "Raksha Pipes Private Limited - Ernakulam", "address": "36/337A, Chettu Kudiyil House, Pullepady Kathrikadavu Road, Kochi, Ernakulam - 682017", "phone": "9562011100", "email": "rishabmkt@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "32AACCV0019M1ZK", "state_code": "32", "pan": "AACCV0019M"},
            {"name": "Raksha Pipes Private Limited - Coimbatore", "address": "D.No. 509/1A,Maniakarampalayam Road,Nallampalayam,Coimbatore,Tamil Nadu - 641006", "phone": "9345157327", "email": "raksha_tcy@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "33AACCV0019M1ZI", "state_code": "33", "pan": "AACCV0019M"},
            {"name": "Raksha Pipes Private Limited - Vijayawada", "address": "# 25/96, 4th Cross, Ramraj Nagar, Kabela Centre, Vijayawada, Andhra Pradesh - 520012", "phone": "7032959106", "email": "prajay@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "37AACCV0019M1ZA", "state_code": "37", "pan": "AACCV0019M"},
            {"name": "Raksha Pipes Private Limited - JC Road", "address": "No-11, New No - 11/1, 1st B Cross, Fireworks Colony, J C Road, Bangalore - 560002", "phone": "9342209496", "email": "galaxyblr@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "29AACCV0019M1Z7", "state_code": "29", "pan": "AACCV0019M"},
            {"name": "Raksha Pipes Private Limited - Belgaum", "address": "C.T.S No-4927/29, Sambhaji Galli Mahadwar Road, Belgaum - 590002", "phone": "9343943148", "email": "galaxy_bel@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "29AACCV0019M1Z7", "state_code": "29", "pan": "AACCV0019M"},
            {"name": "Raksha Pipes Private Limited - Pune", "address": "Gate No.1150, Opp.Hotel Abhiruchi, Near Modak International School, Pune-Saswad Road, 10th Mile, Pune - 412308", "phone": "9325411100", "email": "bhavana@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "27AACCV0019M1Z7", "state_code": "27", "pan": "AACCV0019M"},
            {"name": "Raksha Pipes Private Limited - Indore", "address": "520, Shekhar Central, A B Road, Manorama Ganj, Indore, Madhya Pradesh", "phone": "9770851100", "email": "desana_ind@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "23AACCV0019M1ZJ", "state_code": "23", "pan": "AACCV0019M"},
            {"name": "Raksha Pipes Private Limited - Jaipur", "address": "M - 1, Opp. V K I, Road No. - 03, Near Sharada Sec.School, Kalyan Nagar, Jaipur - 302039", "phone": "9529937091", "email": "emerald@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "08AACCV0019M1ZJ", "state_code": "08", "pan": "AACCV0019M"},
            {"name": "Raksha Pipes Private Limited - Ludhiana", "address": "Block No - 30, No - 3450, Street No- 3, Heera Nagar, P.O.Moti Nagar, Ludhiana - 141010", "phone": "9356292307", "email": "desana_ldh@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "03AACCV0019M1ZJ", "state_code": "03", "pan": "AACCV0019M"},
            {"name": "Raksha Pipes Private Limited - Kolkata", "address": "NH2 Chakundi Dankuni, Post Dankuni, Dankuni, Hooghly - 712310", "phone": "9339711100", "email": "raksha_kol@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "19AACCV0019M1ZJ", "state_code": "19", "pan": "AACCV0019M"},
            {"name": "Raksha Pipes Private Limited - Patna", "address": "ANA Ware House, TRS Campus, New Byepass Road, Patna, Bihar - 800002", "phone": "7991607272", "email": "raksha_patna@shandgroup.com", "website": "www.rakshapipes.com", "gstin": "10AACCV0019M1ZJ", "state_code": "10", "pan": "AACCV0019M"},
        ]
        for s in sites:
            db.add(BillingSite(**s))
        db.commit()
        logger.info(f"Seeded {len(sites)} billing sites")
    finally:
        db.close()


# --- Startup event ---
@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        def safe_ddl(sql):
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()
        safe_ddl("CREATE TABLE IF NOT EXISTS proforma_orders (id SERIAL PRIMARY KEY, pi_no VARCHAR UNIQUE, pi_date TIMESTAMP, customer_id INTEGER REFERENCES customers(id), billing_site VARCHAR DEFAULT '', shipping_site VARCHAR DEFAULT '', no_of_boxes INTEGER DEFAULT 0, total_qty INTEGER DEFAULT 0, value_excl_gst FLOAT DEFAULT 0, gst_amount FLOAT DEFAULT 0, total_amount FLOAT DEFAULT 0, freight_amount FLOAT DEFAULT 0, payment_status VARCHAR DEFAULT 'Pending', payment_method VARCHAR DEFAULT 'Cash', transport_mode VARCHAR DEFAULT '', delivery_days INTEGER DEFAULT 30, notes VARCHAR DEFAULT '', terms TEXT DEFAULT '', order_type VARCHAR DEFAULT 'PI', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        safe_ddl("CREATE TABLE IF NOT EXISTS proforma_order_items (id SERIAL PRIMARY KEY, proforma_order_id INTEGER REFERENCES proforma_orders(id), sl_no INTEGER, product_id INTEGER REFERENCES products(id), part_no VARCHAR DEFAULT '', description VARCHAR DEFAULT '', size VARCHAR DEFAULT '', category VARCHAR DEFAULT '', qty_boxes INTEGER DEFAULT 1, std_packaging INTEGER DEFAULT 1, pieces_per_box INTEGER DEFAULT 1, final_qty INTEGER DEFAULT 0, mrp FLOAT DEFAULT 0, d1 FLOAT DEFAULT 0, d2 FLOAT DEFAULT 0, d3 FLOAT DEFAULT 0, d4 FLOAT DEFAULT 0, d5 FLOAT DEFAULT 0, cd FLOAT DEFAULT 0, discount_percent FLOAT DEFAULT 0, net_rate FLOAT DEFAULT 0, lock_hinge INTEGER DEFAULT 0, basic_amount FLOAT DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        safe_ddl("ALTER TABLE products ADD COLUMN IF NOT EXISTS part_no VARCHAR DEFAULT ''")
        safe_ddl("ALTER TABLE products ADD COLUMN IF NOT EXISTS pieces_per_box INTEGER DEFAULT 1")
        safe_ddl("ALTER TABLE products ADD COLUMN IF NOT EXISTS std_packaging INTEGER DEFAULT 1")
        safe_ddl("ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_name VARCHAR DEFAULT ''")
        safe_ddl("ALTER TABLE sales DROP CONSTRAINT IF EXISTS sales_invoice_no_key")
        safe_ddl("ALTER TABLE transporters ADD COLUMN IF NOT EXISTS tracking_url_pattern VARCHAR DEFAULT ''")
        safe_ddl("ALTER TABLE sales ADD COLUMN IF NOT EXISTS lr_tracking_status VARCHAR DEFAULT ''")
        safe_ddl("ALTER TABLE sales ADD COLUMN IF NOT EXISTS lr_tracking_url VARCHAR DEFAULT ''")
        safe_ddl("ALTER TABLE sales ADD COLUMN IF NOT EXISTS lr_last_checked TIMESTAMP")
        new_sale_cols = [
            "party_name", "payment_terms", "location", "pincode", "state",
            "transporter_name", "lr_no", "weight_kgs", "weight_pg_fiber",
            "sales_person", "pg_fiber_invoice_no", "pg_fiber_invoice_value",
            "gp", "gp_percent", "source_csv"
        ]
        for col in new_sale_cols:
            col_type = "FLOAT" if col in ("weight_kgs","weight_pg_fiber","pg_fiber_invoice_value","gp","gp_percent") else "VARCHAR DEFAULT ''"
            safe_ddl(f"ALTER TABLE sales ADD COLUMN IF NOT EXISTS {col} {col_type}")
        safe_ddl("UPDATE sales SET invoice_value = '0' WHERE invoice_value IS NULL OR invoice_value = '' OR invoice_value = 'None' OR invoice_value = '\\u2013'")
        safe_ddl("ALTER TABLE sales ALTER COLUMN invoice_value TYPE FLOAT USING invoice_value::float")
        safe_ddl("ALTER TABLE sales ADD COLUMN IF NOT EXISTS invoice_value FLOAT DEFAULT 0")
        safe_ddl("UPDATE sales SET invoice_value = total_amount WHERE invoice_value = 0 AND total_amount > 0")
        safe_ddl("UPDATE sales SET total_amount = invoice_value WHERE invoice_value > 0 AND (total_amount = 0 OR total_amount = freight_amount)")
        safe_ddl("UPDATE sales SET total_amount = invoice_value WHERE invoice_value > freight_amount AND freight_amount > 0 AND total_amount = freight_amount")
        customer_cols = [
            ("customer_id", "VARCHAR DEFAULT ''"),
            ("gstin", "VARCHAR DEFAULT ''"),
            ("billing_address", "VARCHAR DEFAULT ''"),
            ("shipping_address", "VARCHAR DEFAULT ''"),
            ("state", "VARCHAR DEFAULT ''"),
            ("district", "VARCHAR DEFAULT ''"),
            ("city", "VARCHAR DEFAULT ''"),
            ("pincode", "VARCHAR DEFAULT ''"),
            ("contact_name", "VARCHAR DEFAULT ''"),
            ("contact_number", "VARCHAR DEFAULT ''"),
            ("contact_email", "VARCHAR DEFAULT ''"),
            ("exec_code", "VARCHAR DEFAULT ''"),
            ("exec_name", "VARCHAR DEFAULT ''"),
            ("exec_number", "VARCHAR DEFAULT ''"),
            ("exec_email", "VARCHAR DEFAULT ''"),
            ("blacklisted", "INTEGER DEFAULT 0"),
            ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ]
        for col_name, col_type in customer_cols:
            safe_ddl(f"ALTER TABLE customers ADD COLUMN IF NOT EXISTS {col_name} {col_type}")
        safe_ddl("UPDATE customers SET customer_id = 'C' || id WHERE customer_id IS NULL OR customer_id = ''")
        safe_ddl("ALTER TABLE customers ADD CONSTRAINT customers_customer_id_unique UNIQUE (customer_id)")
        safe_ddl("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR DEFAULT ''")
        safe_ddl("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR DEFAULT ''")
        safe_ddl("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active INTEGER DEFAULT 1")
        safe_ddl("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP")
        safe_ddl("ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        safe_ddl("UPDATE users SET role = 'admin' WHERE username = 'admin' AND (role = 'user' OR role IS NULL OR role = '')")
        safe_ddl("ALTER TABLE proforma_orders ADD COLUMN IF NOT EXISTS po_no VARCHAR DEFAULT ''")
        safe_ddl("ALTER TABLE proforma_orders ADD COLUMN IF NOT EXISTS po_date TIMESTAMP")
        safe_ddl("ALTER TABLE proforma_orders ADD COLUMN IF NOT EXISTS purchase_total FLOAT DEFAULT 0")
        safe_ddl("ALTER TABLE proforma_orders ADD COLUMN IF NOT EXISTS transport_cost FLOAT DEFAULT 0")
        safe_ddl("ALTER TABLE proforma_orders ADD COLUMN IF NOT EXISTS gross_profit FLOAT DEFAULT 0")
        safe_ddl("ALTER TABLE proforma_orders ADD COLUMN IF NOT EXISTS net_profit FLOAT DEFAULT 0")
        safe_ddl("ALTER TABLE proforma_orders ADD COLUMN IF NOT EXISTS transporter_id INTEGER REFERENCES transporters(id)")
        safe_ddl("ALTER TABLE proforma_orders ADD COLUMN IF NOT EXISTS whatsapp_status VARCHAR DEFAULT 'pending'")
        safe_ddl("ALTER TABLE proforma_orders ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'draft'")
        safe_ddl("ALTER TABLE proforma_orders ADD COLUMN IF NOT EXISTS discount_scheme_applied INTEGER DEFAULT 0")
        safe_ddl("ALTER TABLE proforma_orders ADD COLUMN IF NOT EXISTS discount_percent FLOAT DEFAULT 0")
        safe_ddl("ALTER TABLE proforma_orders ADD COLUMN IF NOT EXISTS discount_amount FLOAT DEFAULT 0")
        safe_ddl("""CREATE TABLE IF NOT EXISTS sale_items (
            id SERIAL PRIMARY KEY,
            sale_id INTEGER REFERENCES sales(id),
            sl_no INTEGER DEFAULT 1,
            product_id INTEGER REFERENCES products(id),
            quantity INTEGER DEFAULT 0,
            unit_price FLOAT DEFAULT 0,
            discount_percent FLOAT DEFAULT 0,
            discount_amount FLOAT DEFAULT 0,
            taxable_amount FLOAT DEFAULT 0,
            gst_rate FLOAT DEFAULT 18,
            cgst_amount FLOAT DEFAULT 0,
            sgst_amount FLOAT DEFAULT 0,
            total_amount FLOAT DEFAULT 0,
            basic_amount FLOAT DEFAULT 0
        )""")
        safe_ddl("""CREATE TABLE IF NOT EXISTS login_attempts (
            id SERIAL PRIMARY KEY,
            username VARCHAR NOT NULL,
            ip_address VARCHAR DEFAULT '',
            success INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
    backfill_part_numbers()
    backfill_pieces_per_box()
    backfill_product_names()
    seed_data()
    seed_billing_sites()


# --- Include routers ---
app.include_router(customers_router)
app.include_router(transporters_router)
app.include_router(products_router)
app.include_router(expenses_router)
app.include_router(sales_router)
app.include_router(orders_router)
app.include_router(tracking_router)
app.include_router(whatsapp_router)
app.include_router(imports_router)
app.include_router(exports_router)
app.include_router(reports_router)
app.include_router(auth_router)


# --- Health check ---
@app.get("/health")
def health_check():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(status_code=503, content={"status": "unhealthy", "database": "disconnected"})


# --- Frontend static files ---
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
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
