from fastapi import FastAPI
from src.books.routes import book_router
from contextlib import asynccontextmanager
from src.db.main import init_db
from src.auth.routes import auth_router
from src.reviews.routes import review_router
from .middleware import register_middleware
from .errors import register_all_errors
version = "v1"
app = FastAPI(
    title="Bookly",
    description="A RESTAPI for Book review web service",
    version=version,
)

register_all_errors(app)

register_middleware(app)


_protected_responses = {
    400: {"description": "Malformed request body"},
    401: {"description": "Authentication required or invalid token"},
    403: {"description": "Insufficient permissions or account not verified"},
    404: {"description": "Resource not found"},
}

app.include_router(
    book_router,
    prefix=f"/api/{version}/books",
    tags=["books"],
    responses=_protected_responses,
)
app.include_router(auth_router, prefix=f"/api/{version}/auth", tags=["auth"])
app.include_router(
    review_router,
    prefix=f"/api/{version}/reviews",
    tags=["reviews"],
    responses=_protected_responses,
)
