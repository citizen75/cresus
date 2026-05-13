"""FastAPI WebSocket routes for backtest updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import logging

from .manager import get_websocket_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/backtest/{backtest_id}")
async def websocket_backtest(
	websocket: WebSocket,
	backtest_id: str,
	strategy: str = Query(default="")
):
	"""WebSocket endpoint for backtest real-time updates.

	Args:
		websocket: WebSocket connection
		backtest_id: Backtest identifier
		strategy: Strategy name (optional)

	Clients connect and receive:
	- daily_results: Daily backtest progress
	- backtest_complete: Final results
	- error: Backtest errors
	"""
	manager = get_websocket_manager()

	await websocket.accept()
	manager.register_connection(backtest_id, websocket)

	logger.info(f"WebSocket client connected: backtest_id={backtest_id}, strategy={strategy}")

	try:
		# Keep connection alive and listen for client messages
		while True:
			# Receive ping/pong or close message from client
			data = await websocket.receive_text()

			# Handle client commands (optional)
			if data == "ping":
				await websocket.send_text("pong")

	except WebSocketDisconnect:
		manager.unregister_connection(backtest_id, websocket)
		logger.info(f"WebSocket client disconnected: backtest_id={backtest_id}")

	except Exception as e:
		manager.unregister_connection(backtest_id, websocket)
		logger.error(f"WebSocket error: {str(e)}")


@router.get("/ws/backtests/active")
async def get_active_backtests():
	"""Get list of active backtests with connected WebSocket clients.

	Returns:
		List of backtest IDs
	"""
	manager = get_websocket_manager()
	active = manager.get_active_backtests()

	return {
		"status": "success",
		"active_backtests": active,
		"count": len(active)
	}


@router.get("/ws/backtests/{backtest_id}/connections")
async def get_backtest_connections(backtest_id: str):
	"""Get number of active WebSocket connections for a backtest.

	Args:
		backtest_id: Backtest identifier

	Returns:
		Connection count
	"""
	manager = get_websocket_manager()
	count = manager.get_connection_count(backtest_id)

	return {
		"status": "success",
		"backtest_id": backtest_id,
		"connection_count": count
	}
