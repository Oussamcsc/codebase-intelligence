"""
Tests for Code Review Assistant
"""

import pytest
from Enhanced_code_review_assistant import CodeReviewAssistant, format_review_output
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
def assistant():
    """Create a code review assistant instance for testing"""
    api_key = os.getenv("ANTHROPIC_API_KEY", "test-key")
    return CodeReviewAssistant(api_key)


def test_analyze_code_structure_good(assistant):
    """Test structure analysis on well-formed code"""
    analysis = assistant.analyze_code_structure(SAMPLE_GOOD_CODE)
    
    assert "error" not in analysis
    assert len(analysis["functions"]) == 1
    assert analysis["functions"][0]["name"] == "calculate_sum"
    assert analysis["functions"][0]["has_docstring"] == True


def test_analyze_code_structure_bad_syntax(assistant):
    """Test structure analysis on code with syntax errors"""
    bad_code = "def broken(\n    pass"
    analysis = assistant.analyze_code_structure(bad_code)
    
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
            "functions": 1,
            "classes": 0
        }
    }
    
    output = format_review_output(review)
    
    assert "CODE REVIEW REPORT" in output
    assert "7/10" in output
    assert "Test issue" in output
    assert "Good documentation" in output


@pytest.mark.asyncio
async def test_review_simple_code(assistant):
    """Test reviewing simple code (requires API key)"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")
    
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
    context = assistant.get_relevant_context("print('hello')")
    
    # Should return empty list if DB is empty
    assert isinstance(context, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
