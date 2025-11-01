"""Tool definitions for the Project Quality Hub MCP server."""

from __future__ import annotations

import asyncio
import inspect
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List

import mcp.types as types

from .context import MCPServerContext
from .utils import ensure_project_path, to_serializable

logger = logging.getLogger(__name__)


class ToolHandlers:
    """Dispatches MCP tool calls to concrete implementations."""

    def __init__(self, context: MCPServerContext) -> None:
        self.context = context
        self._tool_specs = self._build_tool_specs()

    def list_tools(self) -> List[types.Tool]:
        """Return MCP tool descriptors."""

        return [
            types.Tool(
                name=name,
                description=spec["description"],
                inputSchema=spec["schema"],
            )
            for name, spec in self._tool_specs.items()
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool call and return serialisable output."""

        if name not in self._tool_specs:
            raise ValueError(f"Unknown tool: {name}")

        handler = self._tool_specs[name]["handler"]
        try:
            result = handler(arguments)
            if inspect.iscoroutine(result) or isinstance(result, asyncio.Future):
                result = await result
            return to_serializable(result)
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Tool execution failed: %s", name)
            raise

    # ------------------------------------------------------------------ helpers
    def _schedule_background_task(self, *, name: str, func: Callable[[], Any]) -> Dict[str, Any]:
        task_id = self.context.tasks.submit(self.context.executor, name=name, func=func)
        logger.debug("Scheduled task %s (%s)", task_id, name)
        return {"status": "scheduled", "task_id": task_id}

    def _resolve_file_path(self, project_root: str, file_path: str) -> Path:
        candidate = Path(file_path)
        if not candidate.is_absolute():
            candidate = Path(project_root) / candidate
        return candidate.expanduser().resolve()

    def _get_cached_file_list(self, project_root: str) -> List[str]:
        knowledge_graph = self.context.base_interface.memory_manager.load_project(project_root)
        if knowledge_graph and getattr(knowledge_graph, "files", None):
            return list(knowledge_graph.files.keys())
        return []

    def _discover_project_files(self, project_root: str) -> List[str]:
        supported_extensions = {
            ".py",
            ".js",
            ".ts",
            ".tsx",
            ".jsx",
            ".java",
            ".go",
            ".rs",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
        }
        files: List[str] = []
        root_path = Path(project_root)
        for path in root_path.rglob("*"):
            if path.is_file() and path.suffix.lower() in supported_extensions:
                files.append(str(path))
        return files

    def _score_file(self, file_path: Path) -> Dict[str, Any]:
        metrics, issues = self.context.quality_analyzer.analyze_file(str(file_path))
        if not metrics:
            raise ValueError(f"Unable to analyze file metrics: {file_path}")

        static_results = self.context.static_analyzer.analyze_file(str(file_path))
        score = self.context.quality_scorer.calculate_quality_score(metrics, static_results, issues)

        category_scores = {
            getattr(category, "value", str(category)): value
            for category, value in score.category_scores.items()
        }

        return {
            "file_path": str(file_path),
            "total_score": score.total_score,
            "grade": score.grade,
            "category_scores": category_scores,
            "technical_debt_hours": score.technical_debt_hours,
            "priority_issues": score.priority_issues,
            "recommendations": score.recommendations,
            "strengths": score.strengths,
            "metrics": to_serializable(metrics),
            "quality_issues": to_serializable(issues),
            "static_analysis": [to_serializable(res) for res in static_results],
        }

    # ------------------------------------------------------------------ tool specs
    def _build_tool_specs(self) -> Dict[str, Dict[str, Any]]:
        return {
            "analyze_project": {
                "description": "Analyze the target project and refresh the knowledge graph.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                        "force": {
                            "type": "boolean",
                            "description": "Force a full re-analysis even if cached data exists",
                            "default": False,
                        },
                        "enable_monitoring": {
                            "type": "boolean",
                            "description": "Start smart monitoring after a successful analysis",
                            "default": False,
                        },
                    },
                    "required": ["project_root"],
                },
                "handler": self._handle_analyze_project,
            },
            "get_project_summary": {
                "description": "Retrieve the current project summary including branch and monitoring status.",
                "schema": {
                    "type": "object",
                    "properties": {"project_root": {"type": "string"}},
                    "required": ["project_root"],
                },
                "handler": self._handle_get_project_summary,
            },
            "list_branches": {
                "description": "List analyzed branches for the project.",
                "schema": {
                    "type": "object",
                    "properties": {"project_root": {"type": "string"}},
                    "required": ["project_root"],
                },
                "handler": self._handle_list_branches,
            },
            "analyze_branch": {
                "description": "Analyze a specific Git branch.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                        "branch": {"type": "string"},
                        "force": {"type": "boolean", "default": False},
                    },
                    "required": ["project_root", "branch"],
                },
                "handler": self._handle_analyze_branch,
            },
            "switch_branch": {
                "description": "Switch analysis context to another branch.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                        "branch": {"type": "string"},
                    },
                    "required": ["project_root", "branch"],
                },
                "handler": self._handle_switch_branch,
            },
            "compare_branches": {
                "description": "Compare two branches and return structural differences.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                        "branch_a": {"type": "string"},
                        "branch_b": {"type": "string"},
                    },
                    "required": ["project_root", "branch_a", "branch_b"],
                },
                "handler": self._handle_compare_branches,
            },
            "start_monitoring": {
                "description": "Start real-time monitoring for incremental updates.",
                "schema": {
                    "type": "object",
                    "properties": {"project_root": {"type": "string"}},
                    "required": ["project_root"],
                },
                "handler": self._handle_start_monitoring,
            },
            "stop_monitoring": {
                "description": "Stop real-time monitoring.",
                "schema": {
                    "type": "object",
                    "properties": {"project_root": {"type": "string"}},
                    "required": ["project_root"],
                },
                "handler": self._handle_stop_monitoring,
            },
            "get_monitoring_status": {
                "description": "Get the monitoring and incremental update status.",
                "schema": {
                    "type": "object",
                    "properties": {"project_root": {"type": "string"}},
                    "required": ["project_root"],
                },
                "handler": self._handle_get_monitoring_status,
            },
            "score_project": {
                "description": "Compute quality scores for the project.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                        "max_files": {"type": "integer", "minimum": 1, "default": 50},
                        "include_details": {"type": "boolean", "default": False},
                    },
                    "required": ["project_root"],
                },
                "handler": self._handle_score_project,
            },
            "score_file": {
                "description": "Score a single file and return detailed diagnostics.",
                "schema": {
                    "type": "object",
                    "properties": {
                        "project_root": {"type": "string"},
                        "file_path": {"type": "string"},
                    },
                    "required": ["project_root", "file_path"],
                },
                "handler": self._handle_score_file,
            },
            "get_task_result": {
                "description": "Fetch the status/result of a previously scheduled task.",
                "schema": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"],
                },
                "handler": self._handle_get_task_result,
            },
            "list_tasks": {
                "description": "List all tracked background tasks.",
                "schema": {"type": "object", "properties": {}},
                "handler": self._handle_list_tasks,
            },
        }

    # ------------------------------------------------------------------ tool handlers
    def _handle_analyze_project(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        project_root = ensure_project_path(arguments["project_root"])
        force = bool(arguments.get("force", False))
        enable_monitoring = bool(arguments.get("enable_monitoring", False))

        def _job() -> Dict[str, Any]:
            return self.context.enhanced_interface.analyze_project(
                project_root,
                force=force,
                enable_monitoring=enable_monitoring,
            )

        return self._schedule_background_task(
            name=f"analyze_project:{project_root}",
            func=_job,
        )

    def _handle_get_project_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        project_root = ensure_project_path(arguments["project_root"])
        return self.context.enhanced_interface.get_project_summary(project_root)

    def _handle_list_branches(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        project_root = ensure_project_path(arguments["project_root"])
        return self.context.enhanced_interface.list_branches(project_root)

    def _handle_analyze_branch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        project_root = ensure_project_path(arguments["project_root"])
        branch = arguments["branch"]
        force = bool(arguments.get("force", False))

        def _job() -> Dict[str, Any]:
            return self.context.enhanced_interface.analyze_branch(project_root, branch, force=force)

        return self._schedule_background_task(name=f"analyze_branch:{branch}", func=_job)

    def _handle_switch_branch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        project_root = ensure_project_path(arguments["project_root"])
        branch = arguments["branch"]

        def _job() -> Dict[str, Any]:
            return self.context.enhanced_interface.switch_branch(project_root, branch)

        return self._schedule_background_task(name=f"switch_branch:{branch}", func=_job)

    def _handle_compare_branches(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        project_root = ensure_project_path(arguments["project_root"])
        branch_a = arguments["branch_a"]
        branch_b = arguments["branch_b"]
        return self.context.enhanced_interface.compare_branches(project_root, branch_a, branch_b)

    def _handle_start_monitoring(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        project_root = ensure_project_path(arguments["project_root"])
        return self.context.enhanced_interface.start_monitoring(project_root)

    def _handle_stop_monitoring(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        project_root = ensure_project_path(arguments["project_root"])
        return self.context.enhanced_interface.stop_monitoring(project_root)

    def _handle_get_monitoring_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        project_root = ensure_project_path(arguments["project_root"])
        updater = self.context.enhanced_interface._get_updater(project_root)
        return updater.get_update_status()

    def _handle_score_project(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        project_root = ensure_project_path(arguments["project_root"])
        max_files = int(arguments.get("max_files", 50))
        include_details = bool(arguments.get("include_details", False))

        cached_files = self._get_cached_file_list(project_root)
        file_paths = cached_files or self._discover_project_files(project_root)
        file_paths = file_paths[:max_files]

        file_results: List[Dict[str, Any]] = []
        category_totals: Dict[str, float] = defaultdict(float)
        skipped_files: List[str] = []

        for file_path in file_paths:
            try:
                result = self._score_file(Path(file_path))
                file_results.append(result)
                for category, value in result["category_scores"].items():
                    category_totals[category] += value
            except Exception as exc:  # pragma: no cover - log but continue
                logger.warning("Quality scoring failed for %s: %s", file_path, exc)
                skipped_files.append(file_path)

        file_count = len(file_results)
        average_score = (
            sum(entry["total_score"] for entry in file_results) / file_count if file_count else 0.0
        )
        category_average = {
            category: (total / file_count if file_count else 0.0)
            for category, total in category_totals.items()
        }

        response: Dict[str, Any] = {
            "project_root": project_root,
            "files_evaluated": file_count,
            "average_score": average_score,
            "category_average": category_average,
            "skipped_files": skipped_files,
        }

        if include_details:
            response["files"] = file_results
        else:
            response["files"] = [
                {
                    "file_path": entry["file_path"],
                    "total_score": entry["total_score"],
                    "grade": entry["grade"],
                }
                for entry in file_results
            ]

        return response

    def _handle_score_file(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        project_root = ensure_project_path(arguments["project_root"])
        file_path = self._resolve_file_path(project_root, arguments["file_path"])
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return self._score_file(file_path)

    def _handle_get_task_result(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        task_id = arguments["task_id"]
        return self.context.tasks.get_task_state(task_id)

    def _handle_list_tasks(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return self.context.tasks.list_tasks()
