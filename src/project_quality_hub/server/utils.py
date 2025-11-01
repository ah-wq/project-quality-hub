"""Utility helpers for the Project Quality Hub MCP server."""

from __future__ import annotations

import dataclasses
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def ensure_project_path(project_root: str) -> str:
    """Resolve project root to an absolute path and warn if missing."""
    resolved = Path(project_root).expanduser().resolve()
    if not resolved.exists():
        logger.warning("Project root does not exist: %s", resolved)
    return str(resolved)


def to_serializable(value: Any) -> Any:
    """Convert complex objects to JSON-serialisable structures."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if dataclasses.is_dataclass(value):
        return to_serializable(dataclasses.asdict(value))

    if isinstance(value, dict):
        return {str(k): to_serializable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_serializable(item) for item in value]

    if hasattr(value, "value"):
        return to_serializable(getattr(value, "value"))

    return str(value)
