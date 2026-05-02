"""Broker sync endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncio

from services.sync.boursedirect import BourseDirectImporter

router = APIRouter(prefix="/sync", tags=["sync"])


class BourseDirectSyncRequest(BaseModel):
    """Request to sync Bourse Direct portfolio."""
    portfolio_name: str
    email: str
    password: str
    otp_url: Optional[str] = None


@router.post("/boursedirect")
async def sync_boursedirect(request: BourseDirectSyncRequest):
    """Sync portfolio from Bourse Direct broker."""
    try:
        importer = BourseDirectImporter(
            request.email,
            request.password,
            request.otp_url,
        )

        result = await importer.sync_portfolio(request.portfolio_name)

        if result.get("status") == "error":
            raise HTTPException(400, result.get("message", "Sync failed"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to sync portfolio: {str(e)}")


@router.get("/boursedirect/status")
async def get_sync_status(portfolio_name: str):
    """Get sync status for a portfolio."""
    # TODO: Implement sync status tracking
    return {
        "portfolio_name": portfolio_name,
        "last_sync": None,
        "status": "idle",
    }
