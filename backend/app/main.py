"""StyleSense AI — FastAPI Application Entrypoint.

Registers API routers for all core engines:
- StyleDNA Engine (/api/styledna)
- Rule Engine (/api/rules)
- Recommendation Engine (/api/recommendations)
- Feedback Engine (/api/events, /api/feedback)
- Catalogue / Products (/api/products, /api/catalog)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api.styledna import router as styledna_router
from app.api.rules import router as rules_router
from app.api.recommendations import router as recommendations_router
from app.api.feedback import router as feedback_router
from app.api.products import router as products_router

@asynccontextmanager
async def lifespan(app: FastAPI):

    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="StyleSense AI Engine APIs — StyleDNA, Rule, Recommendation, Feedback, and Catalogue.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(styledna_router, prefix=settings.API_V1_PREFIX)
app.include_router(rules_router, prefix=settings.API_V1_PREFIX)
app.include_router(recommendations_router, prefix=settings.API_V1_PREFIX)
app.include_router(feedback_router, prefix=settings.API_V1_PREFIX)
app.include_router(products_router, prefix=settings.API_V1_PREFIX)

@app.get("/api/health", tags=["Health"])
def health_check():
    """Service health and engine status check."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "engines": {
            "styledna": "active",
            "rules": "active",
            "recommendation": "active",
            "feedback": "active",
            "catalogue": "active",
        },
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
