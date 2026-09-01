import os
import logging

logger = logging.getLogger("raksha-erp")

# ---- JWT ----
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    if os.environ.get("ENVIRONMENT") == "production":
        logger.critical("JWT_SECRET environment variable is not set. Refusing to start without a secure secret.")
        raise RuntimeError("JWT_SECRET environment variable is required")
    else:
        JWT_SECRET = "raksha-erp-dev-secret-do-not-use-in-production"
        logger.warning("JWT_SECRET not set — using insecure dev fallback. Set JWT_SECRET env var for production.")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# ---- Rates ----
DEFAULT_GST_RATE = 18.0
TCS_RATE = 0.001

# ---- WhatsApp Cloud API ----
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID", "")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.environ.get("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
WHATSAPP_API_VERSION = "v18.0"
WHATSAPP_API_URL = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"

# ---- CORS ----
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "https://raksha-erp-deploy.onrender.com").split(",") if o.strip()]
CORS_MAX_AGE = 600

# ---- Cloudinary ----
CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL", "")

# ---- Database ----
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./raksha_erp.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ---- Upload limits ----
MAX_UPLOAD_SIZE = int(os.environ.get("MAX_UPLOAD_SIZE", 10 * 1024 * 1024))  # 10MB default

# ---- Auth ----
LOGIN_LOCKOUT_THRESHOLD = 5
LOGIN_LOCKOUT_MINUTES = 15

# ---- File uploads ----
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}

# ---- Role Permissions ----
ROLE_PERMISSIONS = {
    "admin": {
        "dashboard": ["view"],
        "products": ["view", "create", "edit", "delete", "import", "export"],
        "orders": ["view", "create", "edit", "delete", "import", "export"],
        "proforma_orders": ["view", "create", "edit", "delete", "export"],
        "customers": ["view", "create", "edit", "delete", "import"],
        "transporters": ["view", "create", "edit", "delete", "import"],
        "sales": ["view", "create", "edit", "delete", "import", "export", "bulk_edit"],
        "expenses": ["view", "create", "edit", "delete", "import"],
        "reports": ["view", "export"],
        "settings": ["view", "edit"],
        "users": ["view", "create", "edit", "delete"],
    },
    "manager": {
        "dashboard": ["view"],
        "products": ["view", "create", "edit"],
        "orders": ["view", "create", "edit"],
        "proforma_orders": ["view", "create", "edit"],
        "customers": ["view", "create", "edit"],
        "transporters": ["view", "create", "edit"],
        "sales": ["view", "create", "edit"],
        "expenses": ["view", "create", "edit"],
        "reports": ["view"],
        "settings": ["view"],
        "users": [],
    },
    "viewer": {
        "dashboard": ["view"],
        "products": ["view"],
        "orders": ["view"],
        "proforma_orders": ["view"],
        "customers": ["view"],
        "transporters": ["view"],
        "sales": ["view"],
        "expenses": ["view"],
        "reports": ["view"],
        "settings": ["view"],
        "users": [],
    },
}
