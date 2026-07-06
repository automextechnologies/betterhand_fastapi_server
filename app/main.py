import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.infrastructure.database.mongodb import connect_to_mongo, close_mongo_connection
from app.api.routers.auth import router as auth_router
from app.api.routers.ward import router as ward_router
from app.api.routers.donation import router as donation_router

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    await connect_to_mongo()
    yield
    # Shutdown actions
    await close_mongo_connection()

app = FastAPI(
    title="Betterhand API Backend",
    description="FastAPI migration of the Betterhand backend with Clean Architecture and MongoDB",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware configuration
# Using allow_origin_regex to match local React/React Native, staging, and preview origins
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex="https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# API Route Registrations
app.include_router(auth_router, prefix="/api/accounts", tags=["Accounts"])
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(ward_router, prefix="/api/ward", tags=["Ward"])
app.include_router(donation_router, prefix="/api/donation", tags=["Donation"])


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Betterhand API",
        "version": "1.0.0"
    }
