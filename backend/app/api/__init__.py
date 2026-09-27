"""API router aggregation."""
from fastapi import APIRouter

from app.api import (
    auth, schemes, applications, scrutiny, selection,
    fellowship, grievance, dashboard, audit, govmock, notifications,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(schemes.router, prefix="/schemes", tags=["schemes"])
api_router.include_router(applications.router, tags=["applications"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(scrutiny.router, prefix="/scrutiny", tags=["scrutiny"])
api_router.include_router(selection.router, tags=["selection"])
api_router.include_router(fellowship.router, prefix="/fellowships", tags=["fellowship"])
api_router.include_router(grievance.router, prefix="/grievances", tags=["grievance"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(govmock.router, prefix="/mock", tags=["gov-mocks"])
