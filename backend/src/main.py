"""
MedVerify FastAPI Server Application and AWS Lambda Handler (§12).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from mangum import Mangum
except ImportError:
    Mangum = None

from src.routers import (
    check_router,
    investigate_router,
    sessions_router,
    reports_router,
    uploads_router,
    batches_router,
    admin_router,
)
from src.config import settings
from src.utils.logger import logger

app = FastAPI(
    title="MedVerify API",
    description="Regulatory verification, AI counterfeit investigation, and community safety reporting for medicines.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(check_router, prefix="/check", tags=["Quick Check"])
app.include_router(investigate_router, prefix="/investigate", tags=["Investigation"])
app.include_router(sessions_router, prefix="/sessions", tags=["Sessions & Feedback"])
app.include_router(reports_router, prefix="/reports", tags=["Community Reports"])
app.include_router(uploads_router, prefix="/uploads", tags=["Uploads"])
app.include_router(batches_router, tags=["Batches & Manufacturers"])
app.include_router(admin_router, prefix="/admin", tags=["Admin & Analytics"])


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for container and API Gateway monitoring."""
    return {
        "status": "healthy",
        "service": "MedVerify Backend",
        "version": "2.0.0",
        "region": settings.AWS_REGION,
    }


# Mangum adapter for AWS Lambda / API Gateway serverless deployment
handler = Mangum(app) if Mangum else None
