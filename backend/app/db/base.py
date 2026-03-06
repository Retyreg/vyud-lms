from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Используем SQLite для быстрой разработки, PostgreSQL через ENV
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vyud_lms.db")

# check_same_thread нужен только для SQLite
connect_args = {"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
