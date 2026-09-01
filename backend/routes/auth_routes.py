from fastapi import APIRouter, Depends, HTTPException, Request
from ..models import User, TokenBlacklist, LoginAttempt
from ..schemas import LoginIn, RefreshIn, LogoutIn, UserCreateIn, UserUpdateIn, ChangePasswordIn
from ..auth import get_current_user, require_permission, audit_log
from ..database import SessionLocal
from ..config import (
    JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS, LOGIN_LOCKOUT_THRESHOLD,
    LOGIN_LOCKOUT_MINUTES, ROLE_PERMISSIONS,
)
import bcrypt
import jwt
import time
import os
import logging
from datetime import datetime, timezone, timedelta
import uuid

logger = logging.getLogger("raksha-erp")

router = APIRouter(tags=["auth"])

# limiter will be attached in main.py


@router.post("/api/auth/login")
def login(request: Request, body: LoginIn):
    username = body.username
    password = body.password
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "")
    db = SessionLocal()
    try:
        # Check lockout
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
        recent_failures = db.query(LoginAttempt).filter(
            LoginAttempt.username == username,
            LoginAttempt.success == 0,
            LoginAttempt.created_at > cutoff
        ).count()
        if recent_failures >= LOGIN_LOCKOUT_THRESHOLD:
            logger.warning(f"Login locked out for {username} from {ip} ({recent_failures} failures)")
            raise HTTPException(status_code=429, detail=f"Account locked. Try again in {LOGIN_LOCKOUT_MINUTES} minutes.")

        user = db.query(User).filter(User.username == username).first()
        if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            db.add(LoginAttempt(username=username, ip_address=ip, success=0))
            db.commit()
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account disabled")
        # Clear failed attempts on success
        db.query(LoginAttempt).filter(LoginAttempt.username == username, LoginAttempt.success == 0).delete()
        db.add(LoginAttempt(username=username, ip_address=ip, success=1))
        user.last_login = datetime.now(timezone.utc)
        db.commit()
        access_token = jwt.encode(
            {"user_id": user.id, "role": user.role, "type": "access",
             "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)},
            JWT_SECRET, algorithm=JWT_ALGORITHM
        )
        refresh_token = jwt.encode(
            {"user_id": user.id, "type": "refresh",
             "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)},
            JWT_SECRET, algorithm=JWT_ALGORITHM
        )
        audit_log(user, "login", details=f"User {username} logged in", request=request)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {"id": user.id, "username": user.username, "full_name": user.full_name, "role": user.role}
        }
    finally:
        db.close()


@router.post("/api/auth/refresh")
def refresh_token(request: Request, body: RefreshIn):
    token = body.refresh_token
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("user_id")
        jti = payload.get("jti")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    db = SessionLocal()
    try:
        # Check if token is blacklisted (fix #21 - token revocation)
        if jti:
            bl = db.query(TokenBlacklist).filter(TokenBlacklist.token == token).first()
            if bl:
                raise HTTPException(status_code=401, detail="Token has been revoked")
        user = db.query(User).filter(User.id == user_id, User.is_active == 1).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        # Blacklist old refresh token (rotation)
        if jti:
            try:
                old_exp = datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc)
                db.add(TokenBlacklist(token=token, user_id=user_id, expires_at=old_exp))
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to blacklist old refresh token: {e}")
        new_jti = str(uuid.uuid4())
        access_token = jwt.encode(
            {"user_id": user.id, "role": user.role, "type": "access",
             "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)},
            JWT_SECRET, algorithm=JWT_ALGORITHM
        )
        new_refresh_token = jwt.encode(
            {"user_id": user.id, "type": "refresh", "jti": new_jti,
             "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)},
            JWT_SECRET, algorithm=JWT_ALGORITHM
        )
        return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}
    finally:
        db.close()


@router.get("/api/auth/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id, "username": user.username, "full_name": user.full_name,
        "email": user.email, "role": user.role, "is_active": user.is_active,
        "last_login": str(user.last_login) if user.last_login else None,
        "permissions": ROLE_PERMISSIONS.get(user.role, {}),
    }


@router.post("/api/auth/logout")
def logout(inp: LogoutIn, user: User = Depends(get_current_user), request: Request = None):
    if inp.refresh_token:
        try:
            payload = jwt.decode(inp.refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM], options={"verify_exp": False})
            db = SessionLocal()
            try:
                expires_at = datetime.fromtimestamp(payload.get("exp", 0), tz=timezone.utc)
                db.add(TokenBlacklist(token=inp.refresh_token, user_id=user.id, expires_at=expires_at))
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Logout blacklist failed: {e}")
    audit_log(user, "logout", details=f"User {user.username} logged out", request=request)
    return {"message": "Logged out"}


@router.get("/api/users")
def list_users(user: User = Depends(require_permission("users", "view"))):
    db = SessionLocal()
    try:
        users = db.query(User).all()
        return [{"id": u.id, "username": u.username, "full_name": u.full_name,
                 "email": u.email, "role": u.role, "is_active": u.is_active,
                 "last_login": str(u.last_login) if u.last_login else None,
                 "created_at": str(u.created_at) if u.created_at else None} for u in users]
    finally:
        db.close()


@router.get("/api/users/{uid}")
def get_user(uid: int, user: User = Depends(require_permission("users", "view"))):
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.id == uid).first()
        if not u:
            raise HTTPException(404, "User not found")
        return {"id": u.id, "username": u.username, "full_name": u.full_name,
                "email": u.email, "role": u.role, "is_active": u.is_active,
                "last_login": str(u.last_login) if u.last_login else None,
                "created_at": str(u.created_at) if u.created_at else None}
    finally:
        db.close()


@router.post("/api/users")
def create_user(body: UserCreateIn, user: User = Depends(require_permission("users", "create")), request: Request = None):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == body.username).first():
            raise HTTPException(status_code=400, detail="Username already exists")
        pw = body.password
        pw_hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
        new_user = User(
            username=body.username, password_hash=pw_hash,
            full_name=body.full_name, email=body.email,
            role=body.role, is_active=1,
        )
        db.add(new_user)
        db.commit()
        audit_log(user, "create_user", resource="users", resource_id=new_user.id,
                  details=f"Created user {body.username} with role {body.role}", request=request)
        return {"message": "User created", "id": new_user.id}
    finally:
        db.close()


@router.put("/api/users/{uid}")
def update_user(uid: int, body: UserUpdateIn, user: User = Depends(require_permission("users", "edit")), request: Request = None):
    db = SessionLocal()
    try:
        target = db.query(User).filter(User.id == uid).first()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        if target.username == "admin" and body.role and body.role != "admin":
            raise HTTPException(status_code=400, detail="Cannot change admin role")
        if body.full_name is not None:
            target.full_name = body.full_name
        if body.email is not None:
            target.email = body.email
        if body.role is not None:
            target.role = body.role
        if body.is_active is not None:
            target.is_active = body.is_active
        if body.password:
            target.password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
        target.updated_at = datetime.now(timezone.utc)
        db.commit()
        audit_log(user, "update_user", resource="users", resource_id=uid,
                  details=f"Updated user {target.username}", request=request)
        return {"message": "User updated"}
    finally:
        db.close()


@router.delete("/api/users/{uid}")
def delete_user(uid: int, user: User = Depends(require_permission("users", "delete")), request: Request = None):
    db = SessionLocal()
    try:
        target = db.query(User).filter(User.id == uid).first()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        # Prevent deleting the last admin (role-based, not username-based)
        if target.role == "admin":
            admin_count = db.query(User).filter(User.role == "admin", User.is_active == 1).count()
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot delete the last active admin user")
        deleted_username = target.username
        db.delete(target)
        db.commit()
        audit_log(user, "delete_user", resource="users", resource_id=uid,
                  details=f"Deleted user {deleted_username}", request=request)
        return {"message": "User deleted"}
    finally:
        db.close()


@router.put("/api/users/{uid}/password")
def change_password(uid: int, body: ChangePasswordIn, user: User = Depends(get_current_user)):
    if user.id != uid and user.role != "admin":
        raise HTTPException(status_code=403, detail="Can only change own password")
    db = SessionLocal()
    try:
        target = db.query(User).filter(User.id == uid).first()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        if user.role != "admin":
            if not bcrypt.checkpw(body.current_password.encode(), target.password_hash.encode()):
                raise HTTPException(status_code=400, detail="Current password incorrect")
        elif user.id == uid:
            if not body.current_password:
                raise HTTPException(status_code=400, detail="Current password required")
            if not bcrypt.checkpw(body.current_password.encode(), target.password_hash.encode()):
                raise HTTPException(status_code=400, detail="Current password incorrect")
        pw = body.new_password
        target.password_hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
        db.commit()
        return {"message": "Password changed"}
    finally:
        db.close()
