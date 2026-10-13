"""ChangeRadar FastAPI Backend Service
College Project MVP for monitoring public webpages, detecting changes, and tracking deadlines.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import websites, changes, deadlines, notifications

app = FastAPI(
    title="ChangeRadar API",
    description="Backend API for ChangeRadar: Webpage content change detection and deadline tracker",
    version="0.1.0"
)

# Enable CORS for frontend Vite dev server (default port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(websites.router)
app.include_router(changes.router)
app.include_router(deadlines.router)
app.include_router(notifications.router)

@app.get("/")
def root():
    return {
        "service": "ChangeRadar API",
        "status": "operational",
        "version": "0.1.0",
        "docs_url": "/docs",
        "endpoints": [
            "/health",
            "/api/websites",
            "/api/changes",
            "/api/deadlines",
            "/api/deadlines/summary",
            "/api/notifications"
        ]
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": "sqlite:///./changeradar.db",
        "monitoring_engine": "httpx + beautifulsoup4 + difflib"
    }
