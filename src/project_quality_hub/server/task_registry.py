"""Thread-safe task registry used to track background operations."""

from __future__ import annotations

import threading
import traceback
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

from .utils import to_serializable


class TaskStatus(str, Enum):
    """Lifecycle states for background tasks."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskRecord:
    """Metadata captured for each submitted task."""

    task_id: str
    name: str
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None
    future: Optional[Future] = None


class TaskRegistry:
    """Tracks background tasks executed through a shared ThreadPoolExecutor."""

    def __init__(self) -> None:
        self._tasks: Dict[str, TaskRecord] = {}
        self._lock = threading.Lock()

    def submit(
        self,
        executor: ThreadPoolExecutor,
        *,
        name: str,
        func: Callable[..., Any],
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
    ) -> str:
        """Submit a callable and register it for monitoring."""

        args = args or ()
        kwargs = kwargs or {}
        task_id = str(uuid.uuid4())
        record = TaskRecord(task_id=task_id, name=name)

        def _runner() -> None:
            with self._lock:
                record.status = TaskStatus.RUNNING
                record.started_at = datetime.utcnow()
            try:
                result = func(*args, **kwargs)
                serialised = to_serializable(result)
                with self._lock:
                    record.result = serialised
                    record.status = TaskStatus.COMPLETED
                    record.finished_at = datetime.utcnow()
            except Exception as exc:  # pragma: no cover - defensive path
                with self._lock:
                    record.error_message = str(exc)
                    record.error_traceback = traceback.format_exc()
                    record.status = TaskStatus.FAILED
                    record.finished_at = datetime.utcnow()

        future = executor.submit(_runner)
        record.future = future

        with self._lock:
            self._tasks[task_id] = record

        return task_id

    def get_task_state(self, task_id: str) -> Dict[str, Any]:
        """Return a serialisable snapshot for a task."""

        with self._lock:
            record = self._tasks.get(task_id)

        if not record:
            raise KeyError(f"Task not found: {task_id}")

        return {
            "task_id": record.task_id,
            "name": record.name,
            "status": record.status.value,
            "submitted_at": to_serializable(record.submitted_at),
            "started_at": to_serializable(record.started_at),
            "finished_at": to_serializable(record.finished_at),
            "result": record.result,
            "error_message": record.error_message,
            "error_traceback": record.error_traceback,
        }

    def list_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Return a snapshot for all tracked tasks."""

        with self._lock:
            task_ids = list(self._tasks.keys())
        return {task_id: self.get_task_state(task_id) for task_id in task_ids}
