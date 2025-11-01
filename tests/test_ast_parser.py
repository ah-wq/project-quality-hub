from project_quality_hub.quality.ast_parser import TreeSitterParser


def test_detect_language_supports_python_and_unknown():
    parser = TreeSitterParser()

    assert parser.detect_language("module.py") == "python"
    assert parser.detect_language("component.tsx") == "typescript"
    assert parser.detect_language("archive.custom") is None


def test_parse_file_returns_metrics(tmp_path):
    code = "\n".join(
        [
            "def compute(value: int) -> int:",
            "    if value > 1:",
            "        return value * 2",
            "    return value",
        ]
    )
    file_path = tmp_path / "example.py"
    file_path.write_text(code, encoding="utf-8")

    parser = TreeSitterParser()
    metrics = parser.parse_file(str(file_path))

    assert metrics is not None
    assert metrics.language == "python"
    assert metrics.lines_of_code > 0
    assert 0 <= metrics.maintainability_index <= 100
    assert metrics.technical_debt_minutes >= 0
