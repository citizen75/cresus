"""FastAPI application factory."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    """Create and configure FastAPI app."""
    app = FastAPI(
        title="Cresus Portfolio API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware - allow all origins for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from api.routes.health import router as health_router
    from api.routes.portfolios import router as portfolios_router
    from api.routes.sync import router as sync_router
    from api.routes.watchlist import router as watchlist_router
    from api.routes.data import router as data_router
    from api.routes.strategies import router as strategies_router
    from api.routes.backtests import router as backtests_router
    from gateway.websockets.routes import router as websocket_router

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(portfolios_router, prefix="/api/v1")
    app.include_router(sync_router, prefix="/api/v1")
    app.include_router(watchlist_router, prefix="/api/v1")
    app.include_router(data_router, prefix="/api/v1")
    app.include_router(strategies_router, prefix="/api/v1")
    app.include_router(backtests_router, prefix="/api/v1")
    app.include_router(websocket_router, prefix="/api/v1")

    return app


# Create app instance for uvicorn
app = create_app()
