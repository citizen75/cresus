"""Tests for task manager."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from tools.tasks import TaskManager, Task, TaskStatus, TaskPriority


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary task database."""
    db_path = tmp_path / "test_tasks.db"
    manager = TaskManager(db_path=db_path)
    return manager, db_path


def test_create_task(temp_db):
    """Test creating a task."""
    manager, _ = temp_db

    task = manager.create_task(
        title="Test Task",
        description="Test description",
        priority=TaskPriority.HIGH.value,
        status=TaskStatus.TODO.value,
    )

    assert task.id is not None
    assert task.title == "Test Task"
    assert task.description == "Test description"
    assert task.priority == TaskPriority.HIGH.value
    assert task.status == TaskStatus.TODO.value
    assert task.created_at is not None
    assert task.updated_at is not None


def test_get_task(temp_db):
    """Test retrieving a task."""
    manager, _ = temp_db

    created_task = manager.create_task(
        title="Get Task Test",
        priority=TaskPriority.MEDIUM.value,
    )

    retrieved_task = manager.get_task(created_task.id)

    assert retrieved_task is not None
    assert retrieved_task.id == created_task.id
    assert retrieved_task.title == created_task.title


def test_get_nonexistent_task(temp_db):
    """Test retrieving a non-existent task."""
    manager, _ = temp_db

    task = manager.get_task(99999)
    assert task is None


def test_list_tasks(temp_db):
    """Test listing tasks."""
    manager, _ = temp_db

    # Create multiple tasks
    manager.create_task(title="Task 1", status=TaskStatus.TODO.value)
    manager.create_task(title="Task 2", status=TaskStatus.IN_PROGRESS.value)
    manager.create_task(title="Task 3", status=TaskStatus.DONE.value)

    # List all tasks
    tasks = manager.list_tasks()
    assert len(tasks) == 3

    # List with status filter
    todo_tasks = manager.list_tasks(status=TaskStatus.TODO.value)
    assert len(todo_tasks) == 1
    assert todo_tasks[0].title == "Task 1"


def test_list_tasks_with_priority_filter(temp_db):
    """Test listing tasks with priority filter."""
    manager, _ = temp_db

    manager.create_task(title="High Priority", priority=TaskPriority.HIGH.value)
    manager.create_task(title="Medium Priority", priority=TaskPriority.MEDIUM.value)
    manager.create_task(title="Low Priority", priority=TaskPriority.LOW.value)

    high_priority = manager.list_tasks(priority=TaskPriority.HIGH.value)
    assert len(high_priority) == 1
    assert high_priority[0].title == "High Priority"


def test_list_tasks_with_assignee_filter(temp_db):
    """Test listing tasks with assignee filter."""
    manager, _ = temp_db

    manager.create_task(title="Task A", assignee="Alice")
    manager.create_task(title="Task B", assignee="Bob")
    manager.create_task(title="Task C", assignee="Alice")

    alice_tasks = manager.list_tasks(assignee="Alice")
    assert len(alice_tasks) == 2


def test_update_task(temp_db):
    """Test updating a task."""
    manager, _ = temp_db

    task = manager.create_task(
        title="Original Title",
        status=TaskStatus.TODO.value,
    )

    updated = manager.update_task(
        task.id,
        title="Updated Title",
        status=TaskStatus.IN_PROGRESS.value,
    )

    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.status == TaskStatus.IN_PROGRESS.value
    assert updated.updated_at > task.updated_at


def test_update_nonexistent_task(temp_db):
    """Test updating a non-existent task."""
    manager, _ = temp_db

    updated = manager.update_task(99999, title="Updated")
    assert updated is None


def test_delete_task(temp_db):
    """Test deleting a task."""
    manager, _ = temp_db

    task = manager.create_task(title="Task to Delete")

    deleted = manager.delete_task(task.id)
    assert deleted is True

    retrieved = manager.get_task(task.id)
    assert retrieved is None


def test_delete_nonexistent_task(temp_db):
    """Test deleting a non-existent task."""
    manager, _ = temp_db

    deleted = manager.delete_task(99999)
    assert deleted is False


def test_task_with_tags(temp_db):
    """Test task with tags."""
    manager, _ = temp_db

    task = manager.create_task(
        title="Tagged Task",
        tags=["urgent", "important", "project-x"],
    )

    retrieved = manager.get_task(task.id)
    assert retrieved.tags == ["urgent", "important", "project-x"]


def test_task_with_dependencies(temp_db):
    """Test task with dependencies."""
    manager, _ = temp_db

    task1 = manager.create_task(title="Task 1")
    task2 = manager.create_task(title="Task 2")
    task3 = manager.create_task(
        title="Task 3",
        dependencies=[task1.id, task2.id],
    )

    retrieved = manager.get_task(task3.id)
    assert task1.id in retrieved.dependencies
    assert task2.id in retrieved.dependencies


def test_task_with_checklist(temp_db):
    """Test task with checklist."""
    manager, _ = temp_db

    checklist = [
        {"text": "Step 1", "done": True},
        {"text": "Step 2", "done": False},
        {"text": "Step 3", "done": False},
    ]

    task = manager.create_task(
        title="Task with Checklist",
        checklist=checklist,
    )

    retrieved = manager.get_task(task.id)
    assert len(retrieved.checklist) == 3
    assert retrieved.checklist[0]["done"] is True
    assert retrieved.checklist[1]["done"] is False


def test_task_with_attachments(temp_db):
    """Test task with attachments."""
    manager, _ = temp_db

    attachments = [
        {"name": "document.pdf", "url": "https://example.com/doc.pdf"},
        {"name": "image.png", "url": "https://example.com/image.png"},
    ]

    task = manager.create_task(
        title="Task with Attachments",
        attachments=attachments,
    )

    retrieved = manager.get_task(task.id)
    assert len(retrieved.attachments) == 2
    assert retrieved.attachments[0]["name"] == "document.pdf"


def test_get_task_stats(temp_db):
    """Test getting task statistics."""
    manager, _ = temp_db

    # Create various tasks
    manager.create_task(title="Task 1", status=TaskStatus.DONE.value)
    manager.create_task(title="Task 2", status=TaskStatus.DONE.value)
    manager.create_task(title="Task 3", status=TaskStatus.IN_PROGRESS.value)
    manager.create_task(title="Task 4", status=TaskStatus.TODO.value)
    manager.create_task(title="Task 5", status=TaskStatus.BLOCKED.value)
    manager.create_task(title="Task 6", priority=TaskPriority.HIGH.value)

    stats = manager.get_task_stats()

    assert stats["total"] == 6
    assert stats["completed"] == 2
    assert stats["in_progress"] == 1
    assert stats["blocked"] == 1
    assert stats["high_priority"] == 1
    assert stats["completion_rate"] == pytest.approx(33.33, 0.01)


def test_task_pagination(temp_db):
    """Test task pagination."""
    manager, _ = temp_db

    # Create 10 tasks
    for i in range(10):
        manager.create_task(title=f"Task {i}")

    # Get first 5
    page1 = manager.list_tasks(limit=5, offset=0)
    assert len(page1) == 5

    # Get next 5
    page2 = manager.list_tasks(limit=5, offset=5)
    assert len(page2) == 5

    # Get beyond available
    page3 = manager.list_tasks(limit=5, offset=10)
    assert len(page3) == 0


def test_task_due_date(temp_db):
    """Test task with due date."""
    manager, _ = temp_db

    due_date = (datetime.now() + timedelta(days=7)).isoformat()
    task = manager.create_task(
        title="Task with Due Date",
        due_date=due_date,
    )

    retrieved = manager.get_task(task.id)
    assert retrieved.due_date == due_date


def test_list_tasks_with_tags_filter(temp_db):
    """Test listing tasks filtered by tags."""
    manager, _ = temp_db

    manager.create_task(title="Task 1", tags=["urgent", "project-x"])
    manager.create_task(title="Task 2", tags=["important"])
    manager.create_task(title="Task 3", tags=["urgent", "backlog"])

    # Filter by urgent tag
    urgent_tasks = manager.list_tasks(tags=["urgent"])
    assert len(urgent_tasks) == 2

    # Filter by important tag
    important_tasks = manager.list_tasks(tags=["important"])
    assert len(important_tasks) == 1

    # Filter by backlog tag
    backlog_tasks = manager.list_tasks(tags=["backlog"])
    assert len(backlog_tasks) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
