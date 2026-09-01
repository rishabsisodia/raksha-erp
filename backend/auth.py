import logging
import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .config import JWT_SECRET, JWT_ALGORITHM, ROLE_PERMISSIONS
from .database import SessionLocal
from .models import User, AuditLog

logger = logging.getLogger("raksha-erp")

security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        db.expunge(user)
        return user
    finally:
        db.close()


def require_permission(module, action):
    def dependency(user: User = Depends(get_current_user)):
        perms = ROLE_PERMISSIONS.get(user.role, {}).get(module, [])
        if action not in perms:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dependency


def audit_log(user, action, resource="", resource_id="", details="", request=None):
    try:
        db = SessionLocal()
        ip = ""
        if request:
            ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "")
        log = AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else "system",
            action=action, resource=resource, resource_id=str(resource_id),
            details=details, ip_address=ip
        )
        db.add(log)
        db.commit()
        db.close()
    except Exception as e:
        logger.warning(f"Audit log failed: {e}")
