"""ChangeRadar FastAPI Backend Service.

College Project MVP for monitoring public webpages, detecting changes, and tracking deadlines.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import get_db, init_db, DATABASE_URL
from .routers import websites, changes, deadlines, notifications


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context: initialize SQLite database on startup."""
    init_db()
    yield


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
