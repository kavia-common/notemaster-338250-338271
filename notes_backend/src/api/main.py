import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers.notes import router as notes_router
from src.api.routers.tags import router as tags_router

openapi_tags = [
    {"name": "system", "description": "Service health and meta endpoints."},
    {"name": "notes", "description": "Notes CRUD, listing, and search."},
    {"name": "tags", "description": "Tag management."},
]

app = FastAPI(
    title="NoteMaster API",
    description="Backend API for a notes application (notes CRUD, search, and tags).",
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# Basic structured logging configuration
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
allowed_headers = os.getenv("ALLOWED_HEADERS", "*").split(",")
allowed_methods = os.getenv("ALLOWED_METHODS", "*").split(",")
cors_max_age = int(os.getenv("CORS_MAX_AGE", "3600"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins if o.strip()] if allowed_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=[m.strip() for m in allowed_methods if m.strip()] if allowed_methods != ["*"] else ["*"],
    allow_headers=[h.strip() for h in allowed_headers if h.strip()] if allowed_headers != ["*"] else ["*"],
    max_age=cors_max_age,
)


@app.get(
    "/",
    tags=["system"],
    summary="Health check",
    operation_id="health_check",
)
def health_check():
    """Health check endpoint.

    Returns:
        dict: A small JSON payload indicating service is up.
    """
    return {"message": "Healthy"}


app.include_router(notes_router)
app.include_router(tags_router)
