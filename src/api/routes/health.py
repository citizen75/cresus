"""Health check and config endpoints."""

from fastapi import APIRouter
import yaml
from pathlib import Path

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "cresus-api"}


@router.get("/config")
async def get_config():
    """Get API server configuration for frontend.

    Returns the host and port from ~/.cresus/config/cresus.yml
    """
    try:
        config_path = Path.home() / ".cresus" / "config" / "cresus.yml"
        if not config_path.exists():
            return {
                "api": {
                    "host": "localhost",
                    "port": 8000
                }
            }

        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        api_config = config.get("api", {})
        return {
            "api": {
                "host": api_config.get("host", "localhost"),
                "port": api_config.get("port", 8000)
            }
        }
    except Exception as e:
        # Fallback to defaults if config can't be read
        return {
            "api": {
                "host": "localhost",
                "port": 8000,
                "error": str(e)
            }
        }
