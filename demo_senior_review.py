#!/usr/bin/env python3
"""
Demo the senior engineer code review system
"""

import os

def demo_senior_review():
    """Demonstrate the enhanced filtering"""
    # Set dummy API key for demo
    os.environ['OPENAI_API_KEY'] = 'demo-key'
    
    from Code_reviewer import CodeReviewer
    
    print("🚀 ENHANCED CODE REVIEW SYSTEM - SENIOR ENGINEER MODE")
    print("=" * 70)
    
    # Initialize reviewer
    reviewer = CodeReviewer(openai_api_key='demo-key')
    reviewer.enable_codebase_analysis('.')
    
    # Test with the test file
    with open('test_modular_system.py', 'r') as f:
        code = f.read()
    
    print(f"\n📄 Analyzing: test_modular_system.py")
    print(f"📏 Lines of code: {len(code.splitlines())}")
    
    # Get raw analysis results
    codebase_issues = reviewer.codebase_analyzer.analyze_file('test_modular_system.py')
    
    import ast
    tree = ast.parse(code)
    pattern_issues = reviewer.pattern_matcher.find_antipatterns(tree, 'test_modular_system.py', code)
    type_issues = reviewer.type_analyzer.analyze_types(
        reviewer.codebase_analyzer.all_functions, 
        reviewer.codebase_analyzer.all_files
    )
    duplicate_issues = reviewer.duplicate_detector.analyze_duplicates(
        reviewer.codebase_analyzer.all_functions,
        reviewer.codebase_analyzer.all_files
    )
    
    # Convert to standard format
    all_issues = []
    all_issues.extend(reviewer._convert_codebase_issues(codebase_issues))
    all_issues.extend(reviewer._convert_pattern_issues(pattern_issues))
    all_issues.extend(reviewer._convert_type_issues(type_issues))
    all_issues.extend(reviewer._convert_duplicate_issues(duplicate_issues))
    
    print(f"\n📊 RAW ANALYSIS RESULTS:")
    print(f"  📊 Codebase Issues: {len(codebase_issues)}")
    print(f"  🔍 Pattern Issues: {len(pattern_issues)}")
    print(f"  🔎 Type Issues: {len(type_issues)}")  
    print(f"  🔄 Duplicate Issues: {len(duplicate_issues)}")
    print(f"  🎯 TOTAL RAW ISSUES: {len(all_issues)}")
    
    # Apply intelligent filtering
    print(f"\n🧠 APPLYING SENIOR ENGINEER FILTERING...")
    filtered_issues = reviewer._filter_senior_engineer_issues(all_issues)
    
    reduction_pct = ((len(all_issues) - len(filtered_issues)) / len(all_issues)) * 100
    
    print(f"  ✨ Noise Reduction: {reduction_pct:.1f}% ({len(all_issues)} → {len(filtered_issues)})")
    print(f"  🎯 Focus: Correctness, Stability, Performance, Maintainability")
    
    print(f"\n🔍 TOP {len(filtered_issues)} HIGH-IMPACT ISSUES:")
    print("=" * 70)
    
    for i, issue in enumerate(filtered_issues, 1):
        severity = issue['severity']
        category = issue['category']
        message = issue['issue']
        line = issue.get('line', 'N/A')
        
        severity_icons = {'critical': '🔴', 'warning': '🟡', 'suggestion': '🔵'}
        icon = severity_icons.get(severity, '⚪')
        
        print(f"{icon} {i}. [{severity.upper()}] Line {line}")
        print(f"   Category: {category}")
        print(f"   Issue: {message[:80]}{'...' if len(message) > 80 else ''}")
        print(f"   Fix: {issue['suggestion'][:60]}{'...' if len(issue['suggestion']) > 60 else ''}")
        print()
    
    print("=" * 70)
    print("🎯 SUMMARY:")
    print(f"  ✅ Intelligent filtering removes {reduction_pct:.0f}% of low-value issues")
    print(f"  🧠 Focus on REAL BUGS that could break production")
    print(f"  👨‍💻 Senior engineer perspective: Quality over quantity")
    print(f"  🚀 Ready for production deployment review")

if __name__ == "__main__":
    demo_senior_review()