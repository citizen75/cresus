"""Task management API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from tools.tasks import TaskManager, TaskStatus, TaskPriority, Task

router = APIRouter(prefix="/tasks", tags=["tasks"])


# Request/Response models
class TaskRequest(BaseModel):
    """Task creation/update request."""
    title: str
    description: Optional[str] = None
    priority: str = TaskPriority.MEDIUM.value
    due_date: Optional[str] = None
    status: str = TaskStatus.TODO.value
    assignee: Optional[str] = None
    portfolio: Optional[str] = None
    ticker: Optional[str] = None
    tags: Optional[List[str]] = None
    dependencies: Optional[List[int]] = None
    checklist: Optional[List[Dict[str, Any]]] = None
    attachments: Optional[List[Dict[str, str]]] = None


class TaskResponse(BaseModel):
    """Task response."""
    id: int
    title: str
    description: Optional[str]
    priority: str
    due_date: Optional[str]
    status: str
    assignee: Optional[str]
    portfolio: Optional[str]
    ticker: Optional[str]
    tags: List[str]
    dependencies: List[int]
    checklist: List[Dict[str, Any]]
    attachments: List[Dict[str, str]]
    created_at: str
    updated_at: str


class TasksListResponse(BaseModel):
    """Tasks list response."""
    status: str
    tasks: List[TaskResponse]
    count: int
    total: int


class TaskStatsResponse(BaseModel):
    """Task statistics response."""
    status: str
    stats: Dict[str, Any]


# Create task
@router.post("")
async def create_task(request: TaskRequest):
    """Create a new task.

    Args:
        request: Task data

    Returns:
        Created task
    """
    try:
        manager = TaskManager()
        task = manager.create_task(
            title=request.title,
            description=request.description,
            priority=request.priority,
            due_date=request.due_date,
            status=request.status,
            assignee=request.assignee,
            portfolio=request.portfolio,
            ticker=request.ticker,
            tags=request.tags,
            dependencies=request.dependencies,
            checklist=request.checklist,
            attachments=request.attachments,
        )

        return {
            "status": "success",
            "message": f"Task '{task.title}' created",
            "task": _task_to_dict(task),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Get task by ID
@router.get("/{task_id}")
async def get_task(task_id: int):
    """Get a task by ID.

    Args:
        task_id: Task ID

    Returns:
        Task object
    """
    try:
        manager = TaskManager()
        task = manager.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return {
            "status": "success",
            "task": _task_to_dict(task),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# List tasks
@router.get("")
async def list_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assignee: Optional[str] = Query(None),
    portfolio: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),  # Comma-separated
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List tasks with filtering.

    Args:
        status: Filter by status
        priority: Filter by priority
        assignee: Filter by assignee
        portfolio: Filter by portfolio name
        tags: Comma-separated tags to filter by
        limit: Max results
        offset: Pagination offset

    Returns:
        List of tasks
    """
    try:
        manager = TaskManager()

        # Parse tags
        tags_list = None
        if tags:
            tags_list = [t.strip() for t in tags.split(",")]

        tasks = manager.list_tasks(
            status=status,
            priority=priority,
            assignee=assignee,
            portfolio=portfolio,
            tags=tags_list,
            limit=limit,
            offset=offset,
        )

        # Get total count
        all_tasks = manager.list_tasks(limit=999999)
        total = len(all_tasks)

        return {
            "status": "success",
            "tasks": [_task_to_dict(t) for t in tasks],
            "count": len(tasks),
            "total": total,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Update task
@router.put("/{task_id}")
async def update_task(task_id: int, request: TaskRequest):
    """Update a task.

    Args:
        task_id: Task ID
        request: Updated task data

    Returns:
        Updated task
    """
    try:
        manager = TaskManager()
        task = manager.update_task(
            task_id,
            title=request.title,
            description=request.description,
            priority=request.priority,
            due_date=request.due_date,
            status=request.status,
            assignee=request.assignee,
            portfolio=request.portfolio,
            ticker=request.ticker,
            tags=request.tags,
            dependencies=request.dependencies,
            checklist=request.checklist,
            attachments=request.attachments,
        )

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return {
            "status": "success",
            "message": f"Task {task_id} updated",
            "task": _task_to_dict(task),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Delete task
@router.delete("/{task_id}")
async def delete_task(task_id: int):
    """Delete a task.

    Args:
        task_id: Task ID

    Returns:
        Success status
    """
    try:
        manager = TaskManager()
        deleted = manager.delete_task(task_id)

        if not deleted:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return {
            "status": "success",
            "message": f"Task {task_id} deleted",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Get task statistics
@router.get("/stats/overview")
async def get_task_stats():
    """Get task statistics.

    Returns:
        Statistics object
    """
    try:
        manager = TaskManager()
        stats = manager.get_task_stats()

        return {
            "status": "success",
            "stats": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _task_to_dict(task: Task) -> Dict[str, Any]:
    """Convert task to dictionary.

    Args:
        task: Task object

    Returns:
        Dictionary representation
    """
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "due_date": task.due_date,
        "status": task.status,
        "assignee": task.assignee,
        "portfolio": task.portfolio,
        "ticker": task.ticker,
        "tags": task.tags or [],
        "dependencies": task.dependencies or [],
        "checklist": task.checklist or [],
        "attachments": task.attachments or [],
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }
