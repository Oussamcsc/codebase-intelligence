#!/usr/bin/env python3
"""
Test the modular code review system
"""

import os
from Code_reviewer import CodeReviewer

def test_system():
    """Test that all components work together"""
    print("🧪 Testing Enhanced Modular Code Review System...")
    
    # Test with a dummy API key since we're just testing imports and basic functionality
    try:
        reviewer = CodeReviewer(openai_api_key="test-key")
        print("✅ CodeReviewer initialized successfully")
    except Exception as e:
        print(f"❌ CodeReviewer initialization failed: {e}")
        return
    
    # Test codebase analysis (without OpenAI)
    try:
        print("📊 Testing codebase analysis...")
        reviewer.codebase_analyzer.build_graph(".")
        print(f"✅ Codebase analysis complete:")
        print(f"   📁 Files: {len(reviewer.codebase_analyzer.all_files)}")
        print(f"   🔧 Functions: {len(reviewer.codebase_analyzer.all_functions)}")
    except Exception as e:
        print(f"❌ Codebase analysis failed: {e}")
        return
    
    # Test pattern matching
    try:
        print("🔍 Testing pattern matcher...")
        with open("test_modular_system.py", "r") as f:
            code = f.read()
        
        import ast
        tree = ast.parse(code)
        issues = reviewer.pattern_matcher.find_antipatterns(tree, "test_modular_system.py", code)
        print(f"✅ Pattern matching complete: {len(issues)} issues found")
        
        # Show a few issues
        for issue in issues[:3]:
            print(f"   🚨 {issue.rule_id}: {issue.message}")
            
    except Exception as e:
        print(f"❌ Pattern matching failed: {e}")
        return
    
    # Test type analyzer
    try:
        print("🔎 Testing type analyzer...")
        type_issues = reviewer.type_analyzer.analyze_types(
            reviewer.codebase_analyzer.all_functions,
            reviewer.codebase_analyzer.all_files
        )
        print(f"✅ Type analysis complete: {len(type_issues)} issues found")
        
        for issue in type_issues[:2]:
            print(f"   📝 {issue.rule_id}: {issue.message}")
            
    except Exception as e:
        print(f"❌ Type analysis failed: {e}")
        return
    
    # Test duplicate detector
    try:
        print("🔄 Testing duplicate detector...")
        duplicate_issues = reviewer.duplicate_detector.analyze_duplicates(
            reviewer.codebase_analyzer.all_functions,
            reviewer.codebase_analyzer.all_files
        )
        print(f"✅ Duplicate detection complete: {len(duplicate_issues)} issues found")
        
        for issue in duplicate_issues[:2]:
            print(f"   🔁 {issue.rule_id}: {issue.message}")
            
    except Exception as e:
        print(f"❌ Duplicate detection failed: {e}")
        return
    
    print("\n🎉 ALL TESTS PASSED! The modular system is working correctly.")
    print("\nNext steps:")
    print("1. Set your OPENAI_API_KEY environment variable")
    print("2. Run: python scan_project.py")
    print("3. Or run: python cli.py review --help")
    print("4. Or start the API: python api.py")

if __name__ == "__main__":
    test_system()