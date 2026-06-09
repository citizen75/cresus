"""Scheduler (cron) management API routes."""

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional
import json

from tools.cron import CronManager

router = APIRouter(tags=["scheduler"])


def get_cron_scheduler(request: Request):
	"""Get the cron scheduler instance from app state."""
	if not hasattr(request.app.state, 'cron_scheduler'):
		return None
	return request.app.state.cron_scheduler


@router.get("/scheduler/jobs")
async def list_jobs():
	"""List all cron jobs."""
	try:
		manager = CronManager()
		jobs = manager.list_jobs()

		return {
			"status": "success",
			"jobs": [
				{
					"name": job.name,
					"description": job.description,
					"enabled": job.enabled,
					"schedule": job.schedule,
					"type": job.type,
					"target": job.target,
					"params": job.params,
				}
				for job in jobs
			],
			"total": len(jobs),
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler/jobs/{name}")
async def get_job(name: str):
	"""Get a specific cron job."""
	try:
		manager = CronManager()
		job = manager.get_job(name)

		if not job:
			raise HTTPException(status_code=404, detail=f"Job '{name}' not found")

		return {
			"status": "success",
			"job": {
				"name": job.name,
				"description": job.description,
				"enabled": job.enabled,
				"schedule": job.schedule,
				"type": job.type,
				"target": job.target,
				"params": job.params,
			},
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/jobs")
async def create_job(
	request: Request,
	name: str,
	schedule: str,
	target: str,
	job_type: str = "flow",
	description: str = "",
	params: Optional[str] = None,
	enabled: bool = False,
):
	"""Create a new cron job."""
	try:
		# Parse params JSON if provided
		params_dict = {}
		if params:
			try:
				params_dict = json.loads(params)
			except json.JSONDecodeError:
				raise HTTPException(status_code=400, detail="Invalid JSON in params")

		manager = CronManager()
		success, message = manager.create_job(
			name=name,
			schedule=schedule,
			target=target,
			job_type=job_type,
			description=description,
			params=params_dict,
			enabled=enabled,
		)

		if not success:
			raise HTTPException(status_code=400, detail=message)

		# Add to running scheduler if enabled
		if enabled:
			cron_scheduler = get_cron_scheduler(request)
			if cron_scheduler:
				cron_scheduler.add_job_to_scheduler(name)

		return {
			"status": "success",
			"message": message,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.put("/scheduler/jobs/{name}")
async def update_job(
	request: Request,
	name: str,
	schedule: Optional[str] = None,
	target: Optional[str] = None,
	job_type: Optional[str] = None,
	description: Optional[str] = None,
	params: Optional[str] = None,
	enabled: Optional[bool] = None,
):
	"""Update a cron job."""
	try:
		# Parse params JSON if provided
		params_dict = None
		if params:
			try:
				params_dict = json.loads(params)
			except json.JSONDecodeError:
				raise HTTPException(status_code=400, detail="Invalid JSON in params")

		manager = CronManager()
		success, message = manager.update_job(
			name=name,
			schedule=schedule,
			target=target,
			job_type=job_type,
			description=description,
			params=params_dict,
			enabled=enabled,
		)

		if not success:
			raise HTTPException(status_code=400, detail=message)

		# Reload job in running scheduler
		cron_scheduler = get_cron_scheduler(request)
		if cron_scheduler:
			cron_scheduler.reload_job(name)

		return {
			"status": "success",
			"message": message,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/jobs/{name}/enable")
async def enable_job(request: Request, name: str):
	"""Enable a cron job."""
	try:
		manager = CronManager()
		success, message = manager.enable_job(name)

		if not success:
			raise HTTPException(status_code=400, detail=message)

		# Add to running scheduler
		cron_scheduler = get_cron_scheduler(request)
		if cron_scheduler:
			cron_scheduler.add_job_to_scheduler(name)

		return {
			"status": "success",
			"message": message,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/jobs/{name}/disable")
async def disable_job(request: Request, name: str):
	"""Disable a cron job."""
	try:
		manager = CronManager()
		success, message = manager.disable_job(name)

		if not success:
			raise HTTPException(status_code=400, detail=message)

		# Remove from running scheduler
		cron_scheduler = get_cron_scheduler(request)
		if cron_scheduler:
			cron_scheduler.remove_job_from_scheduler(name)

		return {
			"status": "success",
			"message": message,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/jobs/{name}/run")
async def run_job(request: Request, name: str):
	"""Run a cron job immediately (fire-and-forget)."""
	from threading import Thread
	from loguru import logger

	try:
		manager = CronManager()
		job = manager.get_job(name)

		if not job:
			raise HTTPException(status_code=404, detail=f"Job '{name}' not found")

		# Execute the job in background thread (fire-and-forget)
		cron_scheduler = get_cron_scheduler(request)
		if cron_scheduler:
			# Get the job execution function
			job_func = cron_scheduler._create_job_function(job)

			# Run in background thread - return immediately
			def run_in_background():
				try:
					logger.info(f"Background job started: {name}")
					job_func()
					logger.info(f"Background job completed: {name}")
				except Exception as e:
					logger.error(f"Background job failed: {name} - {e}", exc_info=True)

			thread = Thread(target=run_in_background, daemon=True)
			thread.start()

			return {
				"status": "queued",
				"message": f"Job '{name}' queued for execution (running in background)",
			}
		else:
			raise HTTPException(status_code=500, detail="Cron scheduler not available")

	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to run job: {str(e)}")


@router.post("/scheduler/jobs/{name}/duplicate")
async def duplicate_job(name: str, new_name: str = Query(...)):
	"""Duplicate a cron job with a new name."""
	try:
		if not new_name:
			raise HTTPException(status_code=400, detail="new_name is required")

		manager = CronManager()
		success, message = manager.duplicate_job(name, new_name)

		if not success:
			raise HTTPException(status_code=400, detail=message)

		return {
			"status": "success",
			"message": message,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/reload")
async def reload_scheduler(request: Request):
	"""Reload all cron jobs in the running scheduler.

	Useful when config file is modified externally or to sync scheduler with config.
	"""
	try:
		cron_scheduler = get_cron_scheduler(request)
		if not cron_scheduler:
			raise HTTPException(status_code=500, detail="Cron scheduler not available")

		manager = CronManager()

		# Stop and restart scheduler to reload all jobs
		cron_scheduler.stop()
		cron_scheduler.start()

		# Verify jobs loaded
		jobs = cron_scheduler.get_jobs()
		return {
			"status": "success",
			"message": f"Cron scheduler reloaded with {len(jobs)} jobs",
			"jobs_count": len(jobs),
		}
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scheduler/jobs/{name}")
async def delete_job(request: Request, name: str):
	"""Delete a cron job."""
	try:
		manager = CronManager()
		success, message = manager.delete_job(name)

		if not success:
			raise HTTPException(status_code=400, detail=message)

		# Remove from running scheduler
		cron_scheduler = get_cron_scheduler(request)
		if cron_scheduler:
			cron_scheduler.remove_job_from_scheduler(name)

		return {
			"status": "success",
			"message": message,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
