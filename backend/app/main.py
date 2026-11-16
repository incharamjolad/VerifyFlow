from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.database import mongo
from app.routes import auth, documents, reviews, audit, admin

app = FastAPI(
    title="VerifyFlow API",
    description="Intelligent Document Verification and Digital Audit Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list if settings.cors_list else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount application routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(reviews.router)
app.include_router(audit.router)
app.include_router(admin.router)


@app.get("/health", tags=["Health"])
def health():
    """Liveness probe: verifies API process is alive."""
    return {"status": "ok"}


@app.get("/ready", tags=["Health"])
def ready(response: Response):
    """Readiness probe: verifies MongoDB Atlas connection is healthy."""
    if mongo.ping():
        return {"status": "ready", "database": "up"}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "not_ready", "database": "down"}
