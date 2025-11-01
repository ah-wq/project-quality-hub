"""Top-level package exposing project graph analysis, quality scoring, and MCP helpers."""

from importlib import metadata

from .core import (
    EnhancedProjectMindInterface,
    ProjectMindInterface,
    ProjectKnowledgeGraph,
    ProjectMemoryManager,
    MultiBranchProjectMind,
    SmartIncrementalUpdater,
)
from .quality import (
    CodeMetrics,
    QualityAnalyzer,
    QualityIssue,
    IntelligentQualityScorer,
    QualityScore,
    QualityCategory,
    MultiLanguageStaticAnalyzer,
    StaticAnalysisResult,
)

def run_server(*args, **kwargs):
    from .server.server import run as _run
    return _run(*args, **kwargs)

try:
    __version__ = metadata.version("project-quality-hub")
except metadata.PackageNotFoundError:  # pragma: no cover - local dev fallback
    __version__ = "0.1.0"

__all__ = [
    "__version__",
    "EnhancedProjectMindInterface",
    "ProjectMindInterface",
    "ProjectKnowledgeGraph",
    "ProjectMemoryManager",
    "MultiBranchProjectMind",
    "SmartIncrementalUpdater",
    "CodeMetrics",
    "QualityAnalyzer",
    "QualityIssue",
    "IntelligentQualityScorer",
    "QualityScore",
    "QualityCategory",
    "MultiLanguageStaticAnalyzer",
    "StaticAnalysisResult",
    "run_server",
]
