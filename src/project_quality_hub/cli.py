"""Command line interface for Project Quality Hub."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from . import (
    EnhancedProjectMindInterface,
    IntelligentQualityScorer,
    MultiLanguageStaticAnalyzer,
    QualityAnalyzer,
)

logger = logging.getLogger(__name__)

def _print_json(data: Dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def _score_file(project_root: Path, file_path: Path) -> Dict[str, Any]:
    if not file_path.is_absolute():
        file_path = project_root / file_path
    file_path = file_path.resolve()
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    analyzer = QualityAnalyzer()
    metrics, issues = analyzer.analyze_file(str(file_path))
    if not metrics:
        raise RuntimeError(f"Unable to collect metrics for {file_path}")

    static_results = MultiLanguageStaticAnalyzer().analyze_file(str(file_path))
    scorer = IntelligentQualityScorer()
    score = scorer.calculate_quality_score(metrics, static_results, issues)

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
    }


def _score_project(project_root: Path, max_files: int) -> Dict[str, Any]:
    project_root = project_root.resolve()
    analyzer = QualityAnalyzer()
    static_analyzer = MultiLanguageStaticAnalyzer()
    scorer = IntelligentQualityScorer()

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

    files: List[Path] = []
    for path in project_root.rglob("*"):
        if path.is_file() and path.suffix.lower() in supported_extensions:
            files.append(path)
            if len(files) >= max_files:
                break

    file_results: List[Dict[str, Any]] = []
    for path in files:
        metrics, issues = analyzer.analyze_file(str(path))
        if not metrics:
            logger.warning("Skipping %s (no metrics)", path)
            continue
        static_results = static_analyzer.analyze_file(str(path))
        score = scorer.calculate_quality_score(metrics, static_results, issues)
        file_results.append(
            {
                "file_path": str(path),
                "total_score": score.total_score,
                "grade": score.grade,
            }
        )

    average_score = (
        sum(result["total_score"] for result in file_results) / len(file_results)
        if file_results
        else 0.0
    )

    return {
        "project_root": str(project_root),
        "files_evaluated": len(file_results),
        "average_score": average_score,
        "files": file_results,
    }


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Project Quality Hub CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    analyze_cmd = sub.add_parser("analyze", help="Analyze project with knowledge graph")
    analyze_cmd.add_argument("project_root", help="Path to project root")
    analyze_cmd.add_argument("--force", action="store_true", help="Force re-analysis")
    analyze_cmd.add_argument(
        "--monitor",
        action="store_true",
        help="Start smart incremental monitoring after a successful analysis",
    )

    summary_cmd = sub.add_parser("summary", help="Get project summary")
    summary_cmd.add_argument("project_root")

    score_cmd = sub.add_parser("score", help="Score project or single file")
    score_cmd.add_argument("project_root")
    score_cmd.add_argument("--file", help="Relative or absolute path to file")
    score_cmd.add_argument("--max-files", type=int, default=50, help="Max files for project scoring")

    monitor_cmd = sub.add_parser("monitor", help="Control smart incremental monitoring")
    monitor_cmd.add_argument("project_root")
    monitor_cmd.add_argument("action", choices=["start", "stop", "status"], help="Monitor action")

    sub.add_parser("server", help="Run MCP stdio server")

    args = parser.parse_args(argv)

    project_root = None if not hasattr(args, "project_root") else Path(args.project_root)

    if args.command == "analyze":
        interface = EnhancedProjectMindInterface()
        result = interface.analyze_project(
            str(project_root),
            force=args.force,
            enable_monitoring=args.monitor,
        )
        _print_json(result)
    elif args.command == "summary":
        interface = EnhancedProjectMindInterface()
        result = interface.get_project_summary(str(project_root))
        _print_json(result)
    elif args.command == "score":
        if args.file:
            result = _score_file(project_root, Path(args.file))
            _print_json(result)
        else:
            result = _score_project(project_root, args.max_files)
            _print_json(result)
    elif args.command == "monitor":
        interface = EnhancedProjectMindInterface()
        if args.action == "start":
            _print_json(interface.start_monitoring(str(project_root)))
        elif args.action == "stop":
            _print_json(interface.stop_monitoring(str(project_root)))
        else:
            _print_json(interface.get_update_status(str(project_root)))
    elif args.command == "server":
        from .server.server import run as run_server
        run_server()
    else:  # pragma: no cover - defensive
        parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":  # pragma: no cover
    main()
