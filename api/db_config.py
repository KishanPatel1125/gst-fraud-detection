"""
GST Fraud Detection System
Database Configuration
Connects to Supabase PostgreSQL
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

# ── Validate ──
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set! "
        "Add it to Railway Variables."
    )

# ── Fix postgres:// → postgresql:// ──
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ── Auto-fix direct URL → pooler URL (fixes Railway IPv6) ──
if "db.resocelpibhiyqrxhzvo.supabase.co:5432" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace(
        "db.resocelpibhiyqrxhzvo.supabase.co:5432",
        "aws-0-ap-south-1.pooler.supabase.com:6543"
    )

# ── Create engine ──
engine = create_engine(
    DATABASE_URL,
    poolclass    = NullPool,
    echo         = False,
    connect_args = {
        "sslmode":        "require",
        "connect_timeout": 10,
    },
)

SessionLocal = sessionmaker(
    autocommit = False,
    autoflush  = False,
    bind       = engine,
)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    try:
        with engine.connect() as conn:
            result  = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"  ✅ Connected to PostgreSQL!")
            print(f"  Version: {version[:50]}")
            return True
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_connection()