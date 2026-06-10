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


def enrich_with_company_names(matches: List[dict]) -> List[dict]:
    """Add company_name to matches if not already present (only during save, not load)."""
    if not matches:
        return matches

    # Cache for company names to avoid repeated lookups
    company_cache = {}
    enriched = []

    for match in matches:
        enriched_match = dict(match)  # Create a copy

        # If company_name is missing, try to get it
        if 'company_name' not in enriched_match or not enriched_match.get('company_name'):
            ticker = enriched_match.get('ticker', '')
            if ticker:
                # Check cache first
                if ticker not in company_cache:
                    try:
                        import yfinance as yf
                        info = yf.Ticker(ticker).info
                        company_name = info.get('longName', info.get('shortName', ticker))
                        company_cache[ticker] = company_name
                    except Exception:
                        company_cache[ticker] = ticker

                enriched_match['company_name'] = company_cache[ticker]

        enriched.append(enriched_match)

    return enriched


def clean_matches(matches: List[dict], enrich: bool = False) -> List[dict]:
    """Convert NaN and Inf values to None for JSON serialization.

    Args:
        matches: List of match dicts
        enrich: If True, also add company names (only during save, not load)
    """
    # Optionally enrich with company names (only when saving, not when loading)
    if enrich:
        matches = enrich_with_company_names(matches)

    # Clean NaN/Inf values
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
    from tools.logger import get_task_logger
    import time

    try:
        task_logger = get_task_logger(f"alert.{name}")
        task_logger.info(f"Starting alert evaluation for '{name}'")

        manager = AlertManager()
        evaluator = AlertEvaluator(alert_name=name)
        notifier = AlertNotifier()

        alert = manager.get_alert(name)
        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert '{name}' not found")

        task_logger.info(f"Alert found: source={alert.source.value}, formula={alert.formula[:100]}")

        # Evaluate the alert
        start = time.time()
        result = evaluator.evaluate_alert(alert)
        elapsed = time.time() - start
        task_logger.info(f"Evaluation completed in {elapsed:.2f}s")

        # Check for evaluation errors
        if result.error:
            task_logger.error(f"Evaluation error: {result.error}")

        # Update last_run timestamp
        manager.update_last_run(name)
        task_logger.info(f"Last run timestamp updated")

        # Save result to disk
        save_result = manager.save_alert_result(name, result)
        task_logger.info(f"Result saved: {save_result['status']}")

        # Send notification if alert matched and is enabled
        if alert.enabled and result.matched:
            task_logger.info(f"Alert matched! Found {len(result.matches)} matches, notifying")
            notifier.send_alert(alert, result)
        elif result.matched:
            task_logger.info(f"Alert matched but disabled, no notification sent")
        else:
            task_logger.info(f"Alert did not match (checked {result.tickers_checked} tickers)")

        # Flush logs to disk
        time.sleep(0.2)
        task_logger.flush()

        return {
            "status": "success",
            "alert_name": result.alert_name,
            "matched": result.matched,
            "matches": clean_matches(result.matches, enrich=True),
            "tickers_checked": result.tickers_checked,
            "error": result.error,
            "evaluated_at": result.evaluated_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        task_logger = get_task_logger(f"alert.{name}")
        task_logger.error(f"Alert evaluation failed: {str(e)}")
        task_logger.flush()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{name}/results")
async def get_alert_results(name: str, limit: int = 10):
    """Get saved alert results."""
    try:
        manager = AlertManager()
        results = manager.get_alert_results(name, limit=limit)

        # Clean NaN/Inf values from results (don't re-enrich, already enriched when saved)
        cleaned_results = []
        for result in results:
            cleaned_result = {
                "alert_name": result.get("alert_name"),
                "matched": result.get("matched"),
                "matches": clean_matches(result.get("matches", []), enrich=False),
                "error": result.get("error"),
                "evaluated_at": result.get("evaluated_at"),
                "tickers_checked": result.get("tickers_checked"),
            }
            cleaned_results.append(cleaned_result)

        return {
            "status": "success",
            "alert_name": name,
            "results": cleaned_results,
            "total": len(cleaned_results),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/{name}/logs")
async def get_alert_logs(name: str, lines: int = 100):
    """Get logs for an alert."""
    try:
        from tools.logger import get_task_logger

        task_logger = get_task_logger(f"alert.{name}")
        logs = task_logger.get_logs(lines=lines)

        return {
            "status": "success",
            "alert_name": name,
            "logs": [line.rstrip('\n') for line in logs],
            "total_lines": len(logs),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
