"""FastAPI application entrypoint.

Run: uvicorn app.main:app --reload
OpenAPI docs: http://localhost:8000/docs
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.database import init_db

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description=(
        "AI-Enabled Scholarship & Fellowship Management System for Scheduled Tribes "
        "(Ministry of Tribal Affairs). SIH 2026 · PS 26239. "
        "Configurable eligibility rules, documents and selection criteria; AI assists "
        "but every automated decision is human-reviewable, overridable and audited."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}


app.include_router(api_router, prefix=settings.API_PREFIX)
