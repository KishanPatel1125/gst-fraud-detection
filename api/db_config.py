import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool

# DEBUG - print all env vars to Railway logs
print("=== ENV DEBUG ===")
print(f"DATABASE_URL = '{os.environ.get('DATABASE_URL', 'NOT FOUND')}'")
print(f"All keys: {[k for k in os.environ.keys()]}")
print("=================")

DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set!")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
    connect_args={"sslmode": "require"},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()