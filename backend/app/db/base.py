import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger(__name__)

# Явно указываем путь к .env файлу, чтобы он находился независимо от CWD
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

Base = declarative_base()

# Используем PostgreSQL (Supabase)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# SQLAlchemy 2.x dropped the legacy "postgres://" dialect alias.
# Supabase, Heroku and Render still emit "postgres://" in DATABASE_URL,
# so we normalise it here before it reaches create_engine().
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

if SQLALCHEMY_DATABASE_URL:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    logger.warning("DATABASE_URL is not set — database functionality will be unavailable")
    engine = None
    SessionLocal = None
