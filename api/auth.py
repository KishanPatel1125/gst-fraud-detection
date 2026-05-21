"""
GST Fraud Detection System
Authentication System
JWT tokens + Role-based access
"""

from datetime import datetime, timedelta
from typing import Optional
import importlib
try:
    jose = importlib.import_module("jose")
    JWTError = jose.JWTError
    jwt = jose.jwt
except Exception:  # pragma: no cover - fallback when jose is not available in the environment
    raise RuntimeError("python-jose is required for JWT handling. Install it with: pip install python-jose[cryptography]")
try:
    passlib_context = importlib.import_module("passlib.context")
    CryptContext = passlib_context.CryptContext
except Exception:  # pragma: no cover - fallback when passlib is not available in the environment
    class CryptContext:  # lightweight fallback to provide clearer error at runtime
        def __init__(self, *args, **kwargs):
            raise RuntimeError("passlib is required for password hashing. Install it with: pip install passlib[bcrypt]")
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import os

SECRET_KEY  = os.getenv("SECRET_KEY", "gst-fraud-secret-key-2024")
ALGORITHM   = "HS256"
EXPIRE_MINS = 60 * 8   # 8 hours

pwd_context   = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ── Default users (move to DB in production) ──
USERS_DB = {
    "admin": {
        "username":  "admin",
        "full_name": "Admin User",
        "email":     "admin@gstfraud.in",
        "role":      "admin",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # secret
        "disabled":  False,
    },
    "officer": {
        "username":  "officer",
        "full_name": "GST Officer",
        "email":     "officer@gst.gov.in",
        "role":      "officer",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled":  False,
    },
    "ca": {
        "username":  "ca",
        "full_name": "CA Auditor",
        "email":     "ca@firm.in",
        "role":      "ca",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled":  False,
    },
}

class Token(BaseModel):
    access_token: str
    token_type:   str
    user:         dict

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_user(username: str):
    return USERS_DB.get(username)

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=EXPIRE_MINS)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    exc = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail      = "Invalid or expired token",
        headers     = {"WWW-Authenticate": "Bearer"},
    )
    try:
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise exc
    except JWTError:
        raise exc
    user = get_user(username)
    if not user:
        raise exc
    return user

async def get_current_active_user(user=Depends(get_current_user)):
    if user.get("disabled"):
        raise HTTPException(status_code=400, detail="Account disabled")
    return user

def require_role(roles: list):
    async def checker(user=Depends(get_current_active_user)):
        if user["role"] not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required: {roles}"
            )
        return user
    return checker