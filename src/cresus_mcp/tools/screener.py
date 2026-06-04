"""Screener tools implementation."""

import httpx
import json
from typing import Optional, List, Dict, Any
from loguru import logger


async def list_screeners(client: httpx.AsyncClient) -> Dict[str, Any]:
    """List all screeners."""
    try:
        response = await client.get("/screener/screeners")
        return response.json()
    except Exception as e:
        logger.error(f"Error listing screeners: {e}")
        return {"error": str(e), "screeners": []}


async def get_screener(client: httpx.AsyncClient, name: str) -> Dict[str, Any]:
    """Get screener details."""
    try:
        response = await client.get(f"/screener/screeners/{name}")
        return response.json()
    except Exception as e:
        logger.error(f"Error getting screener {name}: {e}")
        return {"error": str(e)}


async def create_screener(
    client: httpx.AsyncClient,
    name: str,
    source: Optional[str] = None,
    formula: Optional[str] = None,
    indicators: Optional[List[str]] = None,
    description: str = "",
) -> Dict[str, Any]:
    """Create a new screener."""
    try:
        payload = {
            "name": name,
            "source": source,
            "formula": formula,
            "indicators": indicators or [],
            "description": description,
        }
        response = await client.post(
            "/screener/screeners",
            json=payload,
        )
        return response.json()
    except Exception as e:
        logger.error(f"Error creating screener {name}: {e}")
        return {"error": str(e)}


async def update_screener(
    client: httpx.AsyncClient,
    name: str,
    source: Optional[str] = None,
    formula: Optional[str] = None,
    indicators: Optional[List[str]] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Update screener."""
    try:
        payload = {}
        if source:
            payload["source"] = source
        if formula:
            payload["formula"] = formula
        if indicators:
            payload["indicators"] = indicators
        if description:
            payload["description"] = description

        response = await client.put(
            f"/screener/screeners/{name}",
            json=payload,
        )
        return response.json()
    except Exception as e:
        logger.error(f"Error updating screener {name}: {e}")
        return {"error": str(e)}


async def run_screener(
    client: httpx.AsyncClient,
    name: str,
    limit: int = 0,
) -> Dict[str, Any]:
    """Execute a screener."""
    try:
        response = await client.post(
            f"/screener/screeners/{name}/run",
            json={"limit": limit},
        )
        return response.json()
    except Exception as e:
        logger.error(f"Error running screener {name}: {e}")
        return {"error": str(e)}


async def get_screener_results(
    client: httpx.AsyncClient,
    name: str,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Get screener results."""
    try:
        response = await client.get(
            f"/screener/screeners/{name}/results",
            params={"limit": limit, "offset": offset},
        )
        return response.json()
    except Exception as e:
        logger.error(f"Error getting screener results {name}: {e}")
        return {"error": str(e)}


async def validate_formula(
    client: httpx.AsyncClient,
    formula: str,
    source: Optional[str] = None,
    tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Validate screener formula."""
    try:
        payload = {
            "formula": formula,
            "source": source,
            "tickers": tickers,
        }
        response = await client.post(
            "/screener/builder",
            json=payload,
        )
        return response.json()
    except Exception as e:
        logger.error(f"Error validating formula: {e}")
        return {"error": str(e)}


async def delete_screener(
    client: httpx.AsyncClient,
    name: str,
) -> Dict[str, Any]:
    """Delete a screener."""
    try:
        response = await client.delete(f"/screener/screeners/{name}")
        return response.json()
    except Exception as e:
        logger.error(f"Error deleting screener {name}: {e}")
        return {"error": str(e)}
