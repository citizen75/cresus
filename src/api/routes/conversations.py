"""Conversation API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime, timedelta
from tools.conversation import ConversationManager

router = APIRouter(prefix="/conversations", tags=["conversations"])


# Request/Response Models
class ConversationMessage(BaseModel):
    source: Literal["user", "chatbot", "alert", "notification"]
    content: str


class BulkAddMessagesRequest(BaseModel):
    messages: List[ConversationMessage]


class MessageResponse(BaseModel):
    source: str
    content: str
    datetime: str


class ConversationHistoryResponse(BaseModel):
    portfolio_name: str
    history: List[MessageResponse]
    count: int
    limit: Optional[int] = None
    offset: Optional[int] = None
    total: Optional[int] = None


class MessageCountResponse(BaseModel):
    portfolio_name: str
    count: int
    by_source: Optional[dict] = None


class ConversationStatsResponse(BaseModel):
    portfolio_name: str
    total_messages: int
    messages_by_source: dict
    last_message: Optional[MessageResponse] = None
    first_message: Optional[MessageResponse] = None


class StatusResponse(BaseModel):
    status: str
    portfolio_name: str
    details: Optional[dict] = None


# Get conversation history with pagination
@router.get("/{portfolio_name}")
async def get_conversation_history(
    portfolio_name: str,
    limit: Optional[int] = Query(None, ge=1, le=1000),
    offset: Optional[int] = Query(0, ge=0),
    source: Optional[str] = None,
    search: Optional[str] = None,
):
    """Get conversation history for a portfolio with pagination and filtering.

    Args:
        portfolio_name: Portfolio name
        limit: Max messages to return (1-1000)
        offset: Starting position
        source: Filter by message source (user|chatbot|alert|notification)
        search: Search in message content
    """
    try:
        manager = ConversationManager(portfolio_name)

        # Get all history
        if source:
            history = manager.get_history(source_filter=source)
        else:
            history = manager.get_history()

        # Apply search filter
        if search:
            history = [
                msg for msg in history
                if search.lower() in msg.content.lower()
            ]

        total = len(history)

        # Apply pagination
        if limit:
            history = history[offset : offset + limit]
        else:
            history = history[offset:]

        history_dicts = [msg.to_dict() for msg in history]

        return ConversationHistoryResponse(
            portfolio_name=portfolio_name,
            history=history_dicts,
            count=len(history_dicts),
            limit=limit,
            offset=offset,
            total=total,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Get specific message count
@router.get("/{portfolio_name}/count")
async def get_message_count(
    portfolio_name: str,
    source: Optional[str] = None,
):
    """Get count of messages in portfolio conversation.

    Args:
        portfolio_name: Portfolio name
        source: Filter by message source
    """
    try:
        manager = ConversationManager(portfolio_name)

        if source:
            count = manager.get_message_count(source_filter=source)
            return MessageCountResponse(
                portfolio_name=portfolio_name,
                count=count,
            )

        # Get counts by source
        all_messages = manager.get_history()
        total = len(all_messages)
        by_source = {}
        for src in ["user", "chatbot", "alert", "notification"]:
            by_source[src] = manager.get_message_count(source_filter=src)

        return MessageCountResponse(
            portfolio_name=portfolio_name,
            count=total,
            by_source=by_source,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Get conversation statistics
@router.get("/{portfolio_name}/stats")
async def get_conversation_stats(portfolio_name: str):
    """Get conversation statistics for a portfolio.

    Returns:
        - total_messages: Total number of messages
        - messages_by_source: Count by source type
        - last_message: Most recent message
        - first_message: Oldest message
    """
    try:
        manager = ConversationManager(portfolio_name)
        all_messages = manager.get_history()

        if not all_messages:
            return ConversationStatsResponse(
                portfolio_name=portfolio_name,
                total_messages=0,
                messages_by_source={
                    "user": 0,
                    "chatbot": 0,
                    "alert": 0,
                    "notification": 0,
                },
            )

        # Count by source
        by_source = {}
        for src in ["user", "chatbot", "alert", "notification"]:
            by_source[src] = manager.get_message_count(source_filter=src)

        # Get first and last
        first_msg = all_messages[0].to_dict() if all_messages else None
        last_msg = all_messages[-1].to_dict() if all_messages else None

        return ConversationStatsResponse(
            portfolio_name=portfolio_name,
            total_messages=len(all_messages),
            messages_by_source=by_source,
            first_message=first_msg,
            last_message=last_msg,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Add single message
@router.post("/{portfolio_name}/message")
async def add_message(portfolio_name: str, message: ConversationMessage):
    """Add a single message to portfolio conversation history."""
    try:
        manager = ConversationManager(portfolio_name)
        manager.add_message(
            source=message.source,
            content=message.content,
        )

        # Return updated history
        history = manager.get_history_dicts()
        return ConversationHistoryResponse(
            portfolio_name=portfolio_name,
            history=history,
            count=len(history),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Add multiple messages
@router.post("/{portfolio_name}/messages/bulk")
async def add_messages_bulk(
    portfolio_name: str,
    request: BulkAddMessagesRequest,
):
    """Add multiple messages to portfolio conversation history.

    Useful for batch imports or synchronization.
    """
    try:
        manager = ConversationManager(portfolio_name)

        for msg in request.messages:
            manager.add_message(
                source=msg.source,
                content=msg.content,
            )

        # Return updated history
        history = manager.get_history_dicts()
        return ConversationHistoryResponse(
            portfolio_name=portfolio_name,
            history=history,
            count=len(history),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Get last message
@router.get("/{portfolio_name}/last")
async def get_last_message(
    portfolio_name: str,
    source: Optional[str] = None,
):
    """Get the most recent message, optionally filtered by source."""
    try:
        manager = ConversationManager(portfolio_name)
        last_msg = manager.get_last_message(
            source_filter=source if source else None
        )

        if not last_msg:
            return {"portfolio_name": portfolio_name, "message": None}

        return {
            "portfolio_name": portfolio_name,
            "message": last_msg.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Filter messages by source
@router.get("/{portfolio_name}/by-source/{source}")
async def get_messages_by_source(
    portfolio_name: str,
    source: Literal["user", "chatbot", "alert", "notification"],
    limit: Optional[int] = Query(None, ge=1, le=1000),
):
    """Get all messages from a specific source.

    Args:
        portfolio_name: Portfolio name
        source: Message source to filter by
        limit: Maximum messages to return
    """
    try:
        manager = ConversationManager(portfolio_name)
        history = manager.get_history(source_filter=source, limit=limit)
        history_dicts = [msg.to_dict() for msg in history]

        return ConversationHistoryResponse(
            portfolio_name=portfolio_name,
            history=history_dicts,
            count=len(history_dicts),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Clear all messages
@router.delete("/{portfolio_name}")
async def clear_conversation_history(portfolio_name: str):
    """Clear all conversation history for a portfolio.

    WARNING: This permanently deletes all messages for this portfolio.
    """
    try:
        manager = ConversationManager(portfolio_name)
        manager.clear_history()

        return StatusResponse(
            status="cleared",
            portfolio_name=portfolio_name,
            details={"message": "All conversation history has been deleted"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Clear messages by source
@router.delete("/{portfolio_name}/by-source/{source}")
async def clear_messages_by_source(
    portfolio_name: str,
    source: Literal["user", "chatbot", "alert", "notification"],
):
    """Clear all messages from a specific source.

    Args:
        portfolio_name: Portfolio name
        source: Message source to clear
    """
    try:
        manager = ConversationManager(portfolio_name)
        all_messages = manager.get_history()

        # Filter out messages from this source
        remaining = [msg for msg in all_messages if msg.source != source]

        # Clear and re-add remaining
        manager.clear_history()
        for msg in remaining:
            manager.add_message(
                source=msg.source,
                content=msg.content,
                timestamp=msg.timestamp,
            )

        cleared_count = len(all_messages) - len(remaining)

        return StatusResponse(
            status="cleared",
            portfolio_name=portfolio_name,
            details={
                "source": source,
                "cleared_count": cleared_count,
                "remaining_count": len(remaining),
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Search messages
@router.get("/{portfolio_name}/search")
async def search_messages(
    portfolio_name: str,
    q: str = Query(..., min_length=1),
    source: Optional[str] = None,
):
    """Search messages by content.

    Args:
        portfolio_name: Portfolio name
        q: Search query (case-insensitive)
        source: Optional source filter
    """
    try:
        manager = ConversationManager(portfolio_name)

        # Get all messages
        if source:
            all_messages = manager.get_history(source_filter=source)
        else:
            all_messages = manager.get_history()

        # Filter by search query
        results = [
            msg for msg in all_messages
            if q.lower() in msg.content.lower()
        ]

        results_dicts = [msg.to_dict() for msg in results]

        return ConversationHistoryResponse(
            portfolio_name=portfolio_name,
            history=results_dicts,
            count=len(results_dicts),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Delete specific message by timestamp
@router.delete("/{portfolio_name}/message")
async def delete_message(
    portfolio_name: str,
    timestamp: str = Query(..., description="Message timestamp to delete"),
):
    """Delete a specific message by timestamp."""
    try:
        from datetime import datetime
        manager = ConversationManager(portfolio_name)
        all_messages = manager.get_history()

        # Find and remove the message with matching timestamp
        target_time = datetime.fromisoformat(timestamp)
        remaining = [
            msg for msg in all_messages
            if msg.timestamp != target_time
        ]

        if len(remaining) == len(all_messages):
            raise HTTPException(status_code=404, detail="Message not found")

        # Clear and re-add remaining messages
        manager.clear_history()
        for msg in remaining:
            manager.add_message(
                source=msg.source,
                content=msg.content,
                timestamp=msg.timestamp,
            )

        # Return updated history
        history = manager.get_history_dicts()
        return ConversationHistoryResponse(
            portfolio_name=portfolio_name,
            history=history,
            count=len(history),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Export conversation
@router.get("/{portfolio_name}/export")
async def export_conversation(
    portfolio_name: str,
    format: Literal["json", "csv"] = "json",
):
    """Export conversation history in specified format.

    Args:
        portfolio_name: Portfolio name
        format: Export format (json or csv)
    """
    try:
        manager = ConversationManager(portfolio_name)
        history = manager.get_history()

        if format == "json":
            history_dicts = [msg.to_dict() for msg in history]
            return {
                "portfolio_name": portfolio_name,
                "format": "json",
                "data": history_dicts,
                "count": len(history_dicts),
            }

        elif format == "csv":
            import csv
            import io

            output = io.StringIO()
            if history:
                writer = csv.DictWriter(
                    output,
                    fieldnames=["source", "content", "datetime"],
                )
                writer.writeheader()
                for msg in history:
                    writer.writerow(msg.to_dict())

            return {
                "portfolio_name": portfolio_name,
                "format": "csv",
                "data": output.getvalue(),
                "count": len(history),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
