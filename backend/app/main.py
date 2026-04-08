"""
VYUD LMS API — entry point.

All route handlers live in app/routers/. This module wires them together.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.base import Base, engine
# Ensure all model metadata is registered before create_all
import app.models.course   # noqa: F401
import app.models.knowledge  # noqa: F401
import app.models.org  # noqa: F401
import app.models.document  # noqa: F401
import app.models.streak  # noqa: F401
import app.models.user  # noqa: F401

from app.routers import health, courses, explain, nodes, orgs, streaks
from app.dependencies import get_db  # re-export for test backward compatibility

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if engine is not None:
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
    else:
        logger.warning("No database engine available — skipping table creation")
    yield


app = FastAPI(title="VYUD LMS API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Register routers ---
app.include_router(health.router)
app.include_router(courses.router)
app.include_router(explain.router)
app.include_router(nodes.router)
app.include_router(orgs.router)
app.include_router(streaks.router)
