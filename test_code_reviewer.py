"""
Tests for Code Review Assistant
"""

import pytest
from Code_reviewer import CodeReviewer
from scan_project import format_comprehensive_review_output
import os

# Sample code for testing
SAMPLE_GOOD_CODE = """
def calculate_sum(numbers: list[int]) -> int:
    \"\"\"Calculate sum of numbers.\"\"\"
    return sum(numbers)
"""

SAMPLE_BAD_CODE = """
def calc(x):
    result = 0
    for i in x:
        result = result + i
    return result/len(x)
"""

SAMPLE_BUGGY_CODE = """
def process_data(data):
    results = []
    for item in data:
        try:
            results.append(item / 0)
        except:
            pass
    return results
"""


@pytest.fixture
def assistant(monkeypatch):
    """Create a code review assistant instance for testing"""
    api_key = os.getenv("OPENAI_API_KEY", "test-key")
    reviewer = CodeReviewer(api_key)
    monkeypatch.setattr(reviewer, "get_embedding", lambda _text: [0.0] * 1536)
    return reviewer


def test_analyze_code_structure_good(assistant):
    """Test structure analysis on well-formed code"""
    analysis = assistant._analyze_code_structure(SAMPLE_GOOD_CODE)
    
    assert "error" not in analysis
    assert len(analysis["functions"]) == 1
    assert analysis["functions"][0]["name"] == "calculate_sum"
    assert analysis["functions"][0]["has_docstring"] == True


def test_analyze_code_structure_bad_syntax(assistant):
    """Test structure analysis on code with syntax errors"""
    bad_code = "def broken(\n    pass"
    analysis = assistant._analyze_code_structure(bad_code)
    
    assert "error" in analysis


def test_add_best_practice(assistant):
    """Test adding best practices to knowledge base"""
    initial_count = assistant.best_practices.count()
    
    assistant.add_best_practice(
        "Test practice",
        "testing",
        {"source": "test"}
    )
    
    assert assistant.best_practices.count() == initial_count + 1


def test_add_common_issue(assistant):
    """Test adding common issues to knowledge base"""
    initial_count = assistant.common_issues.count()
    
    assistant.add_common_issue(
        "Test issue",
        "testing",
        {"source": "test"}
    )
    
    assert assistant.common_issues.count() == initial_count + 1


def test_initialize_knowledge_base(assistant):
    """Test knowledge base initialization"""
    assistant.initialize_knowledge_base()
    
    assert assistant.best_practices.count() > 0
    assert assistant.common_issues.count() > 0


def test_format_review_output():
    """Test review output formatting"""
    review = {
        "overall_quality": "7",
        "summary": "Good code with minor issues",
        "issues": [
            {
                "severity": "warning",
                "line": 5,
                "issue": "Test issue",
                "suggestion": "Test fix",
                "category": "style"
            }
        ],
        "strengths": ["Good documentation"],
        "recommendations": ["Add type hints"],
        "structure_analysis": {
            "lines": 10,
            "functions": [{"name": "calculate_sum", "lineno": 1, "has_docstring": True}],
            "classes": []
        }
    }
    
    output = format_comprehensive_review_output(review)
    
    assert "SENIOR SOFTWARE ENGINEER CODE REVIEW" in output
    assert "7/10" in output
    assert "Test issue" in output
    assert "Good documentation" in output


@pytest.mark.asyncio
async def test_review_simple_code(assistant):
    """Test reviewing simple code (requires API key)"""
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    review = assistant.review_code(
        code=SAMPLE_GOOD_CODE,
        language="python",
        file_path=None,
        context="Test code"
    )
    
    assert "error" not in review
    assert "overall_quality" in review
    assert "issues" in review


def test_get_relevant_context_empty(assistant):
    """Test getting relevant context when DB is empty"""
    context = assistant._get_rag_context("print('hello')")
    
    # Should return empty list if DB is empty
    assert isinstance(context, list)


def test_senior_filter_suppresses_low_signal_repo_noise(assistant):
    """Fast repo review should not leak generic lint/style noise."""
    issues = [
        {
            "severity": "suggestion",
            "line": 49,
            "file_path": "apps/api/tests/test_admin_api_keys.py",
            "issue": "Magic number detected: 201",
            "suggestion": "Consider defining a named constant: MEANINGFUL_NAME = 201",
            "category": "pattern_magic_numbers",
            "evidence": {"magic_number": 201},
        },
        {
            "severity": "warning",
            "line": 84,
            "file_path": "apps/api/tests/test_metering_flow.py",
            "issue": "Function \"test_api_key_metering_flow\" is 57 lines long",
            "suggestion": "Consider breaking this function into smaller functions",
            "category": "pattern_long_functions",
            "evidence": {"line_count": 57},
        },
        {
            "severity": "warning",
            "line": 11,
            "file_path": "apps/api/app/core/redis.py",
            "issue": "Global statement found in function \"get_redis_client\": _redis_client",
            "suggestion": "Consider passing values as parameters and returning results instead of using global variables",
            "category": "pattern_global_assignments",
            "evidence": {"global_variables": ["_redis_client"]},
        },
        {
            "severity": "critical",
            "line": 17,
            "file_path": "apps/api/app/usage/routes.py",
            "issue": "Function \"next_month_reset_date\" expects 1 arguments but 0 were provided",
            "suggestion": "Pass the current timestamp argument or update the function signature.",
            "category": "type_signature_mismatch",
            "evidence": {"expected_args": 1, "provided_args": 0},
        },
    ]

    filtered = assistant._filter_senior_engineer_issues(issues)

    assert len(filtered) == 1
    assert filtered[0]["category"] == "type_signature_mismatch"
    assert "next_month_reset_date" in filtered[0]["issue"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
