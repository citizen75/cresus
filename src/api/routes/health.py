"""Health check and config endpoints."""

from fastapi import APIRouter
from pathlib import Path
import os

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "cresus-api"}


@router.get("/config")
async def get_config():
    """Get API server configuration for frontend.

    Returns the host and port from ~/.cresus/.env
    """
    try:
        env_path = Path.home() / ".cresus" / ".env"

        # Default values
        api_host = "localhost"
        api_port = 8000

        if env_path.exists():
            # Parse .env file
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue

                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()

                        if key == "API_HOST":
                            api_host = value
                        elif key == "API_PORT":
                            try:
                                api_port = int(value)
                            except ValueError:
                                api_port = 8000

        return {
            "api": {
                "host": api_host,
                "port": api_port
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
