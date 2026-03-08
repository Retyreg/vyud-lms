from dotenv import load_dotenv
import os

load_dotenv()

from pathlib import Path

# Явно указываем путь к .env файлу, чтобы он находился независимо от CWD
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Используем PostgreSQL (Supabase)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
