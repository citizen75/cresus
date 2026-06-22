"""Task management system with SQLite storage."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from utils.env import get_db_root

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task status enumeration."""
    TODO = "To-Do"
    IN_PROGRESS = "In Progress"
    DONE = "Done"
    BLOCKED = "Blocked"


class TaskPriority(str, Enum):
    """Task priority enumeration."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


@dataclass
class Task:
    """Task data model."""
    title: str
    description: Optional[str] = None
    priority: str = TaskPriority.MEDIUM.value
    due_date: Optional[str] = None
    status: str = TaskStatus.TODO.value
    assignee: Optional[str] = None
    portfolio: Optional[str] = None
    ticker: Optional[str] = None
    tags: Optional[List[str]] = None
    dependencies: Optional[List[int]] = None  # Task IDs
    checklist: Optional[List[Dict[str, Any]]] = None  # [{"text": "...", "done": bool}]
    attachments: Optional[List[Dict[str, str]]] = None  # [{"name": "...", "url": "..."}]
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert lists to JSON strings for storage
        if self.tags:
            data['tags'] = json.dumps(self.tags)
        if self.dependencies:
            data['dependencies'] = json.dumps(self.dependencies)
        if self.checklist:
            data['checklist'] = json.dumps(self.checklist)
        if self.attachments:
            data['attachments'] = json.dumps(self.attachments)
        return data


class TaskManager:
    """Manage tasks with SQLite storage."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize task manager.

        Args:
            db_path: Path to database file (defaults to ~/.cresus/db/tasks.db)
        """
        if db_path is None:
            db_root = get_db_root()
            db_path = db_root / "tasks.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    priority TEXT DEFAULT 'Medium',
                    due_date TEXT,
                    status TEXT DEFAULT 'To-Do',
                    assignee TEXT,
                    portfolio TEXT,
                    ticker TEXT,
                    tags TEXT,
                    dependencies TEXT,
                    checklist TEXT,
                    attachments TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()
            logger.info(f"Tasks database initialized at {self.db_path}")

    def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = TaskPriority.MEDIUM.value,
        due_date: Optional[str] = None,
        status: str = TaskStatus.TODO.value,
        assignee: Optional[str] = None,
        portfolio: Optional[str] = None,
        ticker: Optional[str] = None,
        tags: Optional[List[str]] = None,
        dependencies: Optional[List[int]] = None,
        checklist: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
    ) -> Task:
        """Create a new task.

        Args:
            title: Task title
            description: Task description
            priority: Task priority (Low/Medium/High)
            due_date: Due date (ISO format)
            status: Task status (To-Do/In Progress/Done/Blocked)
            assignee: Person responsible
            portfolio: Portfolio context (e.g., "My Investment")
            ticker: Stock ticker (e.g., "AAPL")
            tags: Task tags/labels
            dependencies: List of task IDs this depends on
            checklist: List of sub-tasks
            attachments: List of file references

        Returns:
            Created task with ID
        """
        now = datetime.now().isoformat()
        task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            status=status,
            assignee=assignee,
            portfolio=portfolio,
            ticker=ticker,
            tags=tags or [],
            dependencies=dependencies or [],
            checklist=checklist or [],
            attachments=attachments or [],
            created_at=now,
            updated_at=now,
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (
                    title, description, priority, due_date, status,
                    assignee, portfolio, ticker, tags, dependencies, checklist, attachments,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.title, task.description, task.priority, task.due_date,
                task.status, task.assignee, task.portfolio, task.ticker,
                json.dumps(task.tags) if task.tags else None,
                json.dumps(task.dependencies) if task.dependencies else None,
                json.dumps(task.checklist) if task.checklist else None,
                json.dumps(task.attachments) if task.attachments else None,
                task.created_at, task.updated_at
            ))
            conn.commit()
            task.id = cursor.lastrowid

        logger.info(f"Created task: {task.id} - {task.title}")
        return task

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task object or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_task(dict(row))

    def list_tasks(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        portfolio: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Task]:
        """List tasks with filtering.

        Args:
            status: Filter by status
            priority: Filter by priority
            assignee: Filter by assignee
            portfolio: Filter by portfolio name
            tags: Filter by tags (match any)
            limit: Max results
            offset: Pagination offset

        Returns:
            List of tasks
        """
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if priority:
            query += " AND priority = ?"
            params.append(priority)

        if assignee:
            query += " AND assignee = ?"
            params.append(assignee)

        if portfolio:
            query += " AND portfolio = ?"
            params.append(portfolio)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

        tasks = [self._row_to_task(dict(row)) for row in rows]

        # Filter by tags if provided
        if tags:
            tasks = [t for t in tasks if any(tag in (t.tags or []) for tag in tags)]

        return tasks

    def update_task(self, task_id: int, **kwargs) -> Optional[Task]:
        """Update a task.

        Args:
            task_id: Task ID
            **kwargs: Fields to update

        Returns:
            Updated task or None if not found
        """
        task = self.get_task(task_id)
        if not task:
            return None

        # Update allowed fields
        allowed_fields = {
            'title', 'description', 'priority', 'due_date', 'status',
            'assignee', 'portfolio', 'ticker', 'tags', 'dependencies', 'checklist', 'attachments'
        }

        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(task, key, value)

        task.updated_at = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks SET
                    title = ?, description = ?, priority = ?, due_date = ?,
                    status = ?, assignee = ?, portfolio = ?, ticker = ?, tags = ?, dependencies = ?,
                    checklist = ?, attachments = ?, updated_at = ?
                WHERE id = ?
            """, (
                task.title, task.description, task.priority, task.due_date,
                task.status, task.assignee, task.portfolio, task.ticker,
                json.dumps(task.tags) if task.tags else None,
                json.dumps(task.dependencies) if task.dependencies else None,
                json.dumps(task.checklist) if task.checklist else None,
                json.dumps(task.attachments) if task.attachments else None,
                task.updated_at, task_id
            ))
            conn.commit()

        logger.info(f"Updated task: {task_id}")
        return task

    def delete_task(self, task_id: int) -> bool:
        """Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            logger.info(f"Deleted task: {task_id}")

        return deleted

    def get_task_stats(self) -> Dict[str, Any]:
        """Get task statistics.

        Returns:
            Statistics object
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM tasks")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = ?", (TaskStatus.DONE.value,))
            completed = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = ?", (TaskStatus.IN_PROGRESS.value,))
            in_progress = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = ?", (TaskStatus.BLOCKED.value,))
            blocked = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tasks WHERE priority = ?", (TaskPriority.HIGH.value,))
            high_priority = cursor.fetchone()[0]

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "blocked": blocked,
            "high_priority": high_priority,
            "completion_rate": (completed / total * 100) if total > 0 else 0,
        }

    @staticmethod
    def _row_to_task(row: Dict[str, Any]) -> Task:
        """Convert database row to Task object.

        Args:
            row: Database row

        Returns:
            Task object
        """
        return Task(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            priority=row['priority'],
            due_date=row['due_date'],
            status=row['status'],
            assignee=row['assignee'],
            portfolio=row.get('portfolio'),
            ticker=row.get('ticker'),
            tags=json.loads(row['tags']) if row['tags'] else [],
            dependencies=json.loads(row['dependencies']) if row['dependencies'] else [],
            checklist=json.loads(row['checklist']) if row['checklist'] else [],
            attachments=json.loads(row['attachments']) if row['attachments'] else [],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )
