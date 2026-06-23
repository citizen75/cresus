"""Bot management API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from functools import lru_cache
from typing import Optional, Dict, Any
import pandas as pd

from tools.bot import BotManager
from tools.portfolio.manager import PortfolioManager
from tools.watchlist.watchlist_manager import WatchlistManager


class CreateBotRequest(BaseModel):
    name: str
    strategy: str


@lru_cache(maxsize=1)
def _get_bot_manager() -> BotManager:
    return BotManager()


@lru_cache(maxsize=1)
def _get_portfolio_manager() -> PortfolioManager:
    return PortfolioManager()


router = APIRouter(prefix="/bots", tags=["bots"])


@router.get("")
async def list_bots(state: Optional[str] = None):
    """List all bots, optionally filtered by state (active|inactive)."""
    bm = _get_bot_manager()
    bots = bm.list_bots(state)
    return {
        "status": "success",
        "bots": bots,
        "total": len(bots),
    }


@router.get("/summary")
async def get_bots_summary():
    """Get bot counts grouped by state."""
    bm = _get_bot_manager()
    return bm.get_bots_summary()


@router.post("")
async def create_bot(req: CreateBotRequest):
    """Create a new bot from a strategy name or path."""
    bm = _get_bot_manager()
    try:
        config = bm.create_bot(req.name, req.strategy)
        return {"status": "success", "bot": config}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{name}")
async def get_bot(name: str):
    """Get comprehensive bot information (config, portfolio, watchlist)."""
    bm = _get_bot_manager()
    info = bm.get_bot_info(name)
    if info is None:
        raise HTTPException(404, f"Bot '{name}' not found")
    return info


@router.delete("/{name}")
async def delete_bot(name: str):
    """Delete a bot and all its data."""
    bm = _get_bot_manager()
    if not bm.delete_bot(name):
        raise HTTPException(404, f"Bot '{name}' not found")
    return {"status": "success", "message": f"Bot '{name}' deleted"}


@router.post("/{name}/activate")
async def activate_bot(name: str):
    """Activate a bot for live trading."""
    bm = _get_bot_manager()
    if not bm.activate_bot(name):
        raise HTTPException(404, f"Bot '{name}' not found")
    return {"status": "success", "message": f"Bot '{name}' activated"}


@router.post("/{name}/deactivate")
async def deactivate_bot(name: str):
    """Deactivate a bot (pause trading)."""
    bm = _get_bot_manager()
    if not bm.deactivate_bot(name):
        raise HTTPException(404, f"Bot '{name}' not found")
    return {"status": "success", "message": f"Bot '{name}' deactivated"}


@router.post("/{name}/run")
async def run_bot(name: str, params: Optional[Dict[str, Any]] = None):
    """Run a bot trading cycle (default step: pre_market)."""
    from bot.finance import BotFinance

    bm = _get_bot_manager()
    bot_config = bm.get_bot(name)
    if bot_config is None:
        raise HTTPException(404, f"Bot '{name}' not found")

    run_params = dict(params or {})
    run_params.setdefault("step", "pre_market")

    bot_dir = bm.get_bot_dir(name)
    bot = BotFinance(name, bot_dir)
    bot.activate()
    result = bot.run(params=run_params)

    if result.get("status") != "success":
        raise HTTPException(500, result.get("message", "Bot execution failed"))

    return result


@router.get("/{name}/watchlist")
async def get_bot_watchlist(name: str, limit: Optional[int] = None):
    """Get the bot's watchlist (stored in its bot_dir)."""
    bm = _get_bot_manager()
    bot_dir = bm.get_bot_dir(name)
    if not bot_dir.exists():
        raise HTTPException(404, f"Bot '{name}' not found")

    wm = WatchlistManager(name, bot_dir=str(bot_dir))
    df = wm.load()

    if df is None or df.empty:
        return {"name": name, "watchlist": [], "total": 0}

    if limit and limit > 0:
        df = df.head(limit)

    records = df.to_dict("records")
    for record in records:
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None

    return {"name": name, "watchlist": records, "total": len(records)}


@router.get("/{name}/orders")
async def get_bot_orders(name: str):
    """Get all orders for a bot (pending, executed, rejected, expired), stored in its bot_dir."""
    bm = _get_bot_manager()
    bot_dir = bm.get_bot_dir(name)
    if not bot_dir.exists():
        raise HTTPException(404, f"Bot '{name}' not found")

    pm = _get_portfolio_manager()
    return pm.get_portfolio_orders(name, bot_dir=str(bot_dir))


@router.get("/{name}/positions")
async def get_bot_positions(name: str):
    """Get the bot's open positions, resolved from its own bot_dir journal."""
    bm = _get_bot_manager()
    bot_config = bm.get_bot(name)
    if bot_config is None:
        raise HTTPException(404, f"Bot '{name}' not found")

    bot_dir = bm.get_bot_dir(name)
    strategy_name = bot_config.get("strategy", name)
    pm = PortfolioManager(context={"bot_dir": str(bot_dir)})
    result = pm.get_portfolio_positions(name)
    if not result:
        return {"name": name, "strategy": strategy_name, "positions": [], "total_value": 0}

    return {
        "name": name,
        "strategy": strategy_name,
        "positions": result.get("positions", []),
        "total_value": result.get("total_value", 0),
    }
