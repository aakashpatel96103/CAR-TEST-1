import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./rental.db")

options = {"connect_args": {"check_same_thread": False}}
if ":memory:" in DATABASE_URL:
    options["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
