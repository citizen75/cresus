"""FastAPI application factory."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from apscheduler.schedulers.background import BackgroundScheduler
from gateway.cron import CronScheduler


def setup_scheduler(app: FastAPI) -> None:
    """Set up background scheduler for data fetching."""
    scheduler = BackgroundScheduler()

    def fetch_portfolio_data():
        """Fetch fundamental data for all portfolio tickers."""
        try:
            from tools.portfolio.manager import PortfolioManager
            pm = PortfolioManager()
            result = pm.fetch_all_ticker_data(days=365)
            logger.info(f"Scheduled data fetch: {result['tickers_processed']}/{result['tickers_total']} tickers updated")
        except Exception as e:
            logger.error(f"Error in scheduled data fetch: {e}")

    # Schedule data fetch every 30 minutes on weekdays from 9am to 11pm
    # Cron format: (minute, hour, day_of_week, month, day)
    # 9-23 means 9am to 11pm (hour 23)
    # 0-4 means Monday to Friday
    scheduler.add_job(
        fetch_portfolio_data,
        "cron",
        minute="*/30",  # Every 30 minutes
        hour="9-23",    # 9am to 11pm
        day_of_week="0-4",  # Monday to Friday
        id="fetch_portfolio_data",
        name="Fetch portfolio fundamental data",
        max_instances=1,  # Prevent concurrent executions
    )

    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started: Data fetch job scheduled (weekdays 9-23, every 30 min)")

    # Store scheduler in app state for shutdown
    app.state.scheduler = scheduler

    # Add shutdown event
    @app.on_event("shutdown")
    def shutdown_scheduler():
        scheduler.shutdown()
        logger.info("Scheduler shutdown")


def setup_cron_scheduler(app: FastAPI) -> None:
    """Set up cron job scheduler for dynamic job management."""
    try:
        from utils.env import get_config_root
        cron_config_path = get_config_root() / "cron.yml"

        cron_scheduler = CronScheduler(cron_config_path)
        cron_scheduler.start()

        # Store in app state for API access
        app.state.cron_scheduler = cron_scheduler
        logger.info(f"Cron scheduler started with {len(cron_scheduler.get_jobs())} jobs")

        # Add shutdown event
        @app.on_event("shutdown")
        def shutdown_cron_scheduler():
            cron_scheduler.stop()
            logger.info("Cron scheduler shutdown")

    except Exception as e:
        logger.error(f"Failed to set up cron scheduler: {e}", exc_info=True)


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
    from api.routes.conversations import router as conversations_router
    from api.routes.scheduler import router as scheduler_router
    from api.routes.screener import router as screener_router
    from api.routes.alerts import router as alerts_router
    from api.routes.tasks import router as tasks_router
    from api.routes.bots import router as bots_router
    from gateway.websockets.routes import router as websocket_router

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(portfolios_router, prefix="/api/v1")
    app.include_router(sync_router, prefix="/api/v1")
    app.include_router(watchlist_router, prefix="/api/v1")
    app.include_router(data_router, prefix="/api/v1")
    app.include_router(strategies_router, prefix="/api/v1")
    app.include_router(backtests_router, prefix="/api/v1")
    app.include_router(conversations_router, prefix="/api/v1")
    app.include_router(scheduler_router, prefix="/api/v1")
    app.include_router(screener_router, prefix="/api/v1")
    app.include_router(alerts_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(bots_router, prefix="/api/v1")
    app.include_router(websocket_router, prefix="/api/v1")

    # Setup background scheduler for data fetching
    setup_scheduler(app)

    # Setup cron scheduler for dynamic job management
    setup_cron_scheduler(app)

    return app


# Create app instance for uvicorn
app = create_app()
