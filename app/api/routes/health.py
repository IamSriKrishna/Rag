from fastapi import APIRouter
from sqlalchemy import text
from app.core.database import engine

router = APIRouter(tags=["Health"])


@router.get("/health/live")
def liveness():
    return {"status": "alive"}


@router.get("/health/ready")
def readiness():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception:
        return {"status": "degraded", "database": "unavailable"}
