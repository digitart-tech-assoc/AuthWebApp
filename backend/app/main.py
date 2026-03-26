"""役割: FastAPI起動点"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.manifest import router as manifest_router
from app.api.v1.roles import router as roles_router
from app.api.v1.sync import router as sync_router
from app.api.v1.users import router as users_router
from app.api.v1.join import router as join_router
from app.api.v1.contact import router as contact_router
from app.api.v1.student import router as student_router
from app.db.repository import init_db


app = FastAPI(title="AuthWebApp Backend", version="0.1.0")

_origins = [origin.strip() for origin in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",") if origin.strip()]
app.add_middleware(
	CORSMiddleware,
	allow_origins=_origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
	init_db()


@app.get("/health")
async def health() -> dict:
	return {"status": "ok"}


app.include_router(manifest_router)
app.include_router(roles_router)
app.include_router(sync_router)
app.include_router(users_router)
app.include_router(join_router)
app.include_router(contact_router)
app.include_router(student_router)
