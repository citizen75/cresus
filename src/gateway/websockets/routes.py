"""FastAPI WebSocket routes for backtest and conversation updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import logging
import json
import asyncio
from dataclasses import asdict

from .manager import get_websocket_manager
from .conversation_manager import get_conversation_websocket_manager
from tools.conversation import ConversationManager

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

	logger.debug(f"WebSocket client connected: backtest_id={backtest_id}, strategy={strategy}")

	try:
		# Keep connection alive, flush pending messages periodically
		import asyncio
		while True:
			try:
				# Flush any pending messages (from backtest running in background thread)
				pending_count = len(manager._pending_messages)
				if pending_count > 0:
					logger.debug(f"Flushing {pending_count} pending messages for {backtest_id}")
				await manager.flush_pending_messages()

				# Wait for client message with timeout
				data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)

				# Handle client commands (optional)
				if data == "ping":
					await websocket.send_json({"type": "pong"})

			except asyncio.TimeoutError:
				# Timeout - loop again to check for pending messages
				continue

	except WebSocketDisconnect:
		manager.unregister_connection(backtest_id, websocket)
		logger.debug(f"WebSocket client disconnected: backtest_id={backtest_id}")

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


@router.websocket("/ws/conversations/{portfolio_name}")
async def websocket_conversation(
	websocket: WebSocket,
	portfolio_name: str,
	source: str = Query(default=None)
):
	"""WebSocket endpoint for conversation real-time updates.

	Args:
		websocket: WebSocket connection
		portfolio_name: Portfolio name (or '_global' for global chat)
		source: Filter by message source (alert, user, chatbot, notification)

	Clients receive:
	- initial: Full conversation history
	- message: New messages as they arrive
	"""
	manager = get_conversation_websocket_manager()

	await websocket.accept()
	manager.register(portfolio_name, websocket)

	logger.debug(f"WebSocket conversation connected: portfolio={portfolio_name}, source={source}")

	try:
		# Send initial conversation history filtered by portfolio and source
		conv_manager = ConversationManager(portfolio_name)
		history = conv_manager.get_history_dicts(
			source_filter=source,
			portfolio_filter=portfolio_name
		)

		await websocket.send_json({
			"type": "initial",
			"data": history,
			"count": len(history)
		})

		# Keep connection alive and check for new messages
		while True:
			try:
				# Check for file updates every 500ms
				await manager.check_for_updates(portfolio_name, source)
				await asyncio.sleep(0.5)

				# Handle client ping/pong
				try:
					data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
					if data == "ping":
						await websocket.send_json({"type": "pong"})
				except asyncio.TimeoutError:
					pass

			except asyncio.CancelledError:
				break

	except WebSocketDisconnect:
		manager.unregister(portfolio_name, websocket)
		logger.debug(f"WebSocket conversation disconnected: portfolio={portfolio_name}")

	except Exception as e:
		manager.unregister(portfolio_name, websocket)
		logger.error(f"WebSocket conversation error: {str(e)}")
