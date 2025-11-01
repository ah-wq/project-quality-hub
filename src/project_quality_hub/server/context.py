"""Shared runtime context for the MCP server."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from ..core import EnhancedProjectMindInterface, ProjectMindInterface
from ..core.project_memory import ProjectMemoryManager
from ..quality import (
    QualityAnalyzer,
    IntelligentQualityScorer,
    MultiLanguageStaticAnalyzer,
)

from .task_registry import TaskRegistry

logger = logging.getLogger(__name__)


class MCPServerContext:
    """Holds shared singletons used by MCP tool handlers."""

    def __init__(self, *, max_workers: int = 4) -> None:
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = TaskRegistry()
        self.enhanced_interface = EnhancedProjectMindInterface()
        self.base_interface = ProjectMindInterface()
        self.memory_manager = ProjectMemoryManager()
        self.quality_analyzer = QualityAnalyzer()
        self.static_analyzer = MultiLanguageStaticAnalyzer()
        self.quality_scorer = IntelligentQualityScorer()
        logger.debug("MCPServerContext initialized with max_workers=%s", max_workers)

    def shutdown(self) -> None:
        """Gracefully stop shared executors."""
        logger.debug("Shutting down MCPServerContext executor")
        self.executor.shutdown(wait=False)
