from dataclasses import replace

from project_quality_hub.quality import (
    CodeMetrics,
    IntelligentQualityScorer,
    QualityIssue,
    QualityScore,
)
from project_quality_hub.quality.static_analyzers import StaticAnalysisResult


def _base_metrics(**overrides) -> CodeMetrics:
    base = CodeMetrics(
        file_path="sample.py",
        language="python",
        lines_of_code=42,
        cyclomatic_complexity=6,
        cognitive_complexity=8,
        function_count=3,
        class_count=1,
        max_nesting_depth=2,
        long_functions=[],
        duplicated_code_blocks=[],
        maintainability_index=92.0,
        technical_debt_minutes=15,
    )
    return replace(base, **overrides)


def test_quality_score_rewards_low_complexity():
    scorer = IntelligentQualityScorer()
    metrics = _base_metrics()

    score: QualityScore = scorer.calculate_quality_score(
        metrics=metrics,
        static_results=[],
        quality_issues=[],
    )

    assert 0 <= score.total_score <= 100
    assert score.grade in {"A+", "A", "B"}
    assert any("Well-sized functions" in item for item in score.strengths)
    assert score.priority_issues == []


def test_quality_score_surfaces_security_and_complexity_issues():
    scorer = IntelligentQualityScorer()
    metrics = _base_metrics(
        cyclomatic_complexity=28,
        cognitive_complexity=40,
        max_nesting_depth=6,
        long_functions=["def very_long_function(): ..."],
        duplicated_code_blocks=["duplicate_block"],
        maintainability_index=45.0,
        technical_debt_minutes=540,
    )

    static_results = [
        StaticAnalysisResult(
            tool_name="Bandit",
            file_path="sample.py",
            line=12,
            column=4,
            severity="error",
            rule_id="B101",
            message="Possible hardcoded secret",
            category="security",
            suggestion="Load secrets from environment variables",
            auto_fixable=False,
        ),
        StaticAnalysisResult(
            tool_name="ESLint",
            file_path="sample.ts",
            line=7,
            column=2,
            severity="warning",
            rule_id="prefer-const",
            message="Use const instead of let",
            category="style",
            suggestion="Convert variable declarations to const",
            auto_fixable=True,
        ),
    ]

    quality_issues = [
        QualityIssue(
            file_path="sample.py",
            line=30,
            column=1,
            severity="error",
            category="complexity",
            message="Function exceeds recommended branching factor",
            suggestion="Split the function into smaller units",
            auto_fixable=False,
        )
    ]

    score: QualityScore = scorer.calculate_quality_score(
        metrics=metrics,
        static_results=static_results,
        quality_issues=quality_issues,
    )

    assert score.total_score < 80
    assert any(item.startswith("🚨 Security") for item in score.priority_issues)
    assert any("Complexity" in item for item in score.priority_issues)
    assert any("security issues" in recommendation for recommendation in score.recommendations)
