import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.db.base import Base, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if engine is not None:
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created/verified successfully")
        except Exception as e:
            logger.error("Failed to create database tables: %s", e)
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

app.include_router(api_router)
