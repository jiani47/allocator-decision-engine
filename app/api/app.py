"""FastAPI application factory."""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import router

logger = logging.getLogger("equi.api")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="Equi API",
        description="Allocator Decision Engine REST API",
        version="1.0.0",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )

    application.include_router(router, prefix="/api")

    static_dir = Path(__file__).resolve().parent.parent.parent / "static"
    if static_dir.exists():
        application.mount(
            "/",
            StaticFiles(directory=str(static_dir), html=True),
            name="static",
        )

    return application


app = create_app()
