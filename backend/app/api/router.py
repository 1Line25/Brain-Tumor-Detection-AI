from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import audit_logs, auth, patients, predictions, users


api_router = APIRouter()

# Gom toàn bộ router con vào một router chung.
# main.py sau này chỉ cần:
# app.include_router(api_router, prefix=settings.api_v1_prefix)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(patients.router)
api_router.include_router(predictions.router)
api_router.include_router(audit_logs.router)
