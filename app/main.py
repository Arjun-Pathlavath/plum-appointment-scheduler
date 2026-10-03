"""FastAPI Application Entrypoint for Plum AI-Powered Appointment Scheduler."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import APP_NAME, APP_VERSION
from app.api.routes import router

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="""
# Plum Benefits - AI-Powered Appointment Scheduler Assistant

A production-grade backend service that transforms unstructured natural language and scanned document/image requests into structured clinical appointment data.

### Pipeline Architecture:
1. **Step 1 - OCR / Text Extraction**: Image preprocessing, noise reduction, and typo normalization.
2. **Step 2 - Entity Extraction**: Extracting `date_phrase`, `time_phrase`, and `department`.
3. **Step 3 - Normalization (Asia/Kolkata)**: Mapping temporal phrases to ISO-8601 in India Standard Time (`Asia/Kolkata`) and taxonomy standardization.
4. **Guardrails**: Automated ambiguity detection and exit condition handler (`needs_clarification`).
5. **Step 4 - Final Appointment Synthesis**: Merged structured output with status confirmation.
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)

# Mount static directory for interactive demo UI
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_playground():
        return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for deployment monitoring."""
    return {
        "status": "healthy",
        "service": APP_NAME,
        "version": APP_VERSION,
        "timezone": "Asia/Kolkata"
    }


if __name__ == "__main__":
    import uvicorn
    from app.config import HOST, PORT
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
