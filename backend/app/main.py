"""ChangeRadar FastAPI Backend Service.

College Project MVP for monitoring public webpages, detecting changes, and tracking deadlines.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db, init_db, SessionLocal, DATABASE_URL
from .routers import auth, websites, changes, deadlines, notifications
from .services import deadline_reminder_service

logger = logging.getLogger("changeradar.main")


async def deadline_reminder_background_loop():
    """Periodically scans for upcoming deadlines due in 48h, 24h, or 12h."""
    while True:
        try:
            await asyncio.sleep(60)
            db = SessionLocal()
            try:
                await deadline_reminder_service.process_deadline_reminders(db)
            finally:
                db.close()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning(f"Error in deadline reminder background loop: {exc}")
            await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context: initialize SQLite database and start background tasks."""
    init_db()
    reminder_task = asyncio.create_task(deadline_reminder_background_loop())
    yield
    reminder_task.cancel()
    try:
        await reminder_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="ChangeRadar API",
    description="Backend API for ChangeRadar: Webpage content change detection and deadline tracker",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS settings for local React / Vite development and preview servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers with both standard and /api prefixes for full client compatibility
app.include_router(auth.router, prefix="/auth")
app.include_router(auth.router, prefix="/api/auth")

app.include_router(websites.router, prefix="/websites")
app.include_router(websites.router, prefix="/api/websites")

app.include_router(changes.router, prefix="/changes")
app.include_router(changes.router, prefix="/api/changes")

app.include_router(deadlines.router, prefix="/deadlines")
app.include_router(deadlines.router, prefix="/api/deadlines")

app.include_router(notifications.router, prefix="/notifications")
app.include_router(notifications.router, prefix="/api/notifications")


@app.get("/", summary="API Root")
def root():
    return {
        "service": "ChangeRadar API",
        "status": "operational",
        "version": "0.1.0",
        "docs_url": "/docs",
        "endpoints": {
            "health": "/health",
            "websites": "/websites",
            "websites_api": "/api/websites",
            "changes": "/api/changes",
            "deadlines": "/api/deadlines",
            "deadlines_summary": "/api/deadlines/summary",
            "notifications": "/api/notifications"
        }
    }


@app.get("/health", summary="Health Check")
def health_check(db: Session = Depends(get_db)):
    """Check service health and SQLite database connectivity."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {str(exc)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "database_url": DATABASE_URL,
        "monitoring_engine": "httpx + beautifulsoup4 + difflib"
    }
