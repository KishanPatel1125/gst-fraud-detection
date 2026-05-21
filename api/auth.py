"""
GST Fraud Detection - Auth System
Simple JWT authentication
"""

from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import jwt
import os

SECRET_KEY  = os.getenv("SECRET_KEY", "gst-fraud-secret-key-2024")
ALGORITHM   = "HS256"
EXPIRE_MINS = 60 * 8

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ── Simple users — no bcrypt needed ──
USERS_DB = {
    "admin": {
        "username":  "admin",
        "full_name": "Admin User",
        "email":     "admin@gstfraud.in",
        "role":      "admin",
        "password":  "secret",
        "disabled":  False,
    },
    "officer": {
        "username":  "officer",
        "full_name": "GST Officer",
        "email":     "officer@gst.gov.in",
        "role":      "officer",
        "password":  "secret",
        "disabled":  False,
    },
    "ca": {
        "username":  "ca",
        "full_name": "CA Auditor",
        "email":     "ca@firm.in",
        "role":      "ca",
        "password":  "secret",
        "disabled":  False,
    },
}

class Token(BaseModel):
    access_token: str
    token_type:   str
    user:         dict

def get_user(username: str):
    return USERS_DB.get(username)

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if user["password"] != password:
        return False
    return user

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode.update({
        "exp": datetime.utcnow() + timedelta(minutes=EXPIRE_MINS)
    })
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
    except Exception:
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
            raise HTTPException(status_code=403, detail=f"Access denied")
        return user
    return checker