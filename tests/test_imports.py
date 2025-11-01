from project_quality_hub import (
    EnhancedProjectMindInterface,
    IntelligentQualityScorer,
    MultiLanguageStaticAnalyzer,
    ProjectMindInterface,
    QualityAnalyzer,
    run_server,
)


def test_imports_available():
    assert EnhancedProjectMindInterface is not None
    assert ProjectMindInterface is not None
    assert QualityAnalyzer is not None
    assert IntelligentQualityScorer is not None
    assert MultiLanguageStaticAnalyzer is not None
    assert callable(run_server)
