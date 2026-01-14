from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cache.redis_client import init_redis, close_redis
from app.core.config import get_list_env
from app.database.database import db
from app.routers import admin_router, user_router

app = FastAPI(
    title="Secure Bank API",
    description="A secure banking system with Admin 2FA and Customer Management",
    version="1.0.0",
)

cors_origins = get_list_env("CORS_ALLOW_ORIGINS", default=[])
cors_allow_credentials = bool(cors_origins) and "*" not in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)
app.include_router(user_router)


@app.on_event("startup")
async def startup():
    await db.connect()
    await init_redis()


@app.on_event("shutdown")
async def shutdown():
    await close_redis()
    await db.disconnect()
