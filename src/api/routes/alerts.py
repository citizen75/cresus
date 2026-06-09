"""Alert management API routes."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import math

from tools.alerts import AlertManager, AlertEvaluator, Alert
from tools.alerts.notifier import AlertNotifier

router = APIRouter(tags=["alerts"])


def clean_matches(matches: List[dict]) -> List[dict]:
    """Convert NaN and Inf values to None for JSON serialization."""
    cleaned = []
    for match in matches:
        clean_match = {}
        for key, value in match.items():
            if isinstance(value, float):
                if math.isnan(value) or math.isinf(value):
                    clean_match[key] = None
                else:
                    clean_match[key] = value
            else:
                clean_match[key] = value
        cleaned.append(clean_match)
    return cleaned


# Pydantic models for request bodies
class CreateAlertRequest(BaseModel):
    name: str
    source: str
    source_value: Optional[str] = None
    formula: str
    notify: str = "conversation"
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class UpdateAlertRequest(BaseModel):
    formula: Optional[str] = None
    enabled: Optional[bool] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    notify: Optional[str] = None


@router.get("/alerts")
async def list_alerts():
    """List all alerts."""
    try:
        manager = AlertManager()
        alerts = manager.list_alerts()

        return {
            "status": "success",
            "alerts": [alert.to_dict() for alert in alerts],
            "count": len(alerts),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts")
async def create_alert(request: Request):
    """Create a new alert.

    Accepts both JSON body and query parameters.
    """
    try:
        # Try to parse JSON body first
        try:
            body = await request.json()
        except:
            body = {}

        # Merge with query parameters (query params override body)
        query_params = dict(request.query_params)
        params = {**body, **query_params}

        required = ["name", "source", "formula"]
        for key in required:
            if key not in params:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {key}"
                )

        manager = AlertManager()
        result = manager.create_alert(
            name=params["name"],
            source=params["source"],
            source_value=params.get("source_value"),
            formula=params["formula"],
            notify=params.get("notify", "conversation"),
            description=params.get("description"),
            tags=params.get("tags"),
        )

        if result["status"] == "error":
            raise HTTPException(status_code=400, detail=result["message"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{name}")
async def get_alert(name: str):
    """Get a specific alert."""
    try:
        manager = AlertManager()
        alert = manager.get_alert(name)

        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert '{name}' not found")

        return {
            "status": "success",
            "alert": alert.to_dict(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/alerts/{name}")
async def update_alert(name: str, request: Request):
    """Update an alert.

    Accepts both JSON body and query parameters.
    """
    try:
        # Try to parse JSON body first
        try:
            body = await request.json()
        except:
            body = {}

        # Merge with query parameters (query params override body)
        query_params = dict(request.query_params)
        params = {**body, **query_params}

        manager = AlertManager()

        # Build kwargs for update
        kwargs = {}
        for key in ["formula", "enabled", "description", "tags", "notify"]:
            if key in params:
                kwargs[key] = params[key]

        if not kwargs:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = manager.update_alert(name, **kwargs)

        if result["status"] == "error":
            raise HTTPException(status_code=400 if "not found" in result["message"] else 500, detail=result["message"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/alerts/{name}")
async def delete_alert(name: str):
    """Delete an alert."""
    try:
        manager = AlertManager()
        result = manager.delete_alert(name)

        if result["status"] == "error":
            raise HTTPException(status_code=404, detail=result["message"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{name}/run")
async def run_alert(name: str):
    """Run alert evaluation and return matches."""
    try:
        manager = AlertManager()
        evaluator = AlertEvaluator()
        notifier = AlertNotifier()

        alert = manager.get_alert(name)
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert '{name}' not found")

        # Evaluate the alert
        result = evaluator.evaluate_alert(alert)

        # Update last_run timestamp
        manager.update_last_run(name)

        # Send notification if alert matched and is enabled
        if alert.enabled and result.matched:
            notifier.send_alert(alert, result)

        return {
            "status": "success",
            "alert_name": result.alert_name,
            "matched": result.matched,
            "matches": clean_matches(result.matches),
            "tickers_checked": result.tickers_checked,
            "error": result.error,
            "evaluated_at": result.evaluated_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
