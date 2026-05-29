"""Scheduler (cron) management API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import json

from tools.cron import CronManager

router = APIRouter(tags=["scheduler"])


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

		return {
			"status": "success",
			"message": message,
		}
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/jobs/{name}/enable")
async def enable_job(name: str):
	"""Enable a cron job."""
	try:
		manager = CronManager()
		success, message = manager.enable_job(name)

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


@router.post("/scheduler/jobs/{name}/disable")
async def disable_job(name: str):
	"""Disable a cron job."""
	try:
		manager = CronManager()
		success, message = manager.disable_job(name)

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


@router.post("/scheduler/jobs/{name}/run")
async def run_job(name: str):
	"""Run a cron job immediately."""
	try:
		manager = CronManager()
		success, message = manager.run_job(name)

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


@router.delete("/scheduler/jobs/{name}")
async def delete_job(name: str):
	"""Delete a cron job."""
	try:
		manager = CronManager()
		success, message = manager.delete_job(name)

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
