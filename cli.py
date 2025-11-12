#!/usr/bin/env python3
"""
Enhanced CLI tool for Modular AI Code Review Assistant
"""

import argparse
import sys
import os
from pathlib import Path
from Code_reviewer import CodeReviewer
from scan_project import format_comprehensive_review_output
import json


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced Modular AI Code Review Assistant with 4 Specialized Analyzers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 ENHANCED MODULAR CODE REVIEW SYSTEM 🚀

Analyzers:
  📊 Codebase Analyzer  - Dependencies, dead code, impact analysis  
  🔍 Pattern Matcher    - AST antipatterns, complexity, bad practices
  🔎 Type Analyzer      - Signature validation, type mismatches
  🔄 Duplicate Detector - Code duplication, copy-paste detection

Examples:
  # Comprehensive review with all analyzers
  python cli.py review my_code.py
  
  # Review with codebase analysis enabled (recommended)
  python cli.py review --codebase app.py
  
  # Review with context
  python cli.py review app.py --context "Flask API endpoint" --codebase
  
  # Initialize knowledge base
  python cli.py init
  
  # Add custom patterns
  python cli.py add-practice "Always validate user input" --category security
  
  # Get codebase statistics
  python cli.py stats --codebase
  
  # Analyze function impact
  python cli.py analyze-function calculate_total --file utils.py
  
  # Review from stdin
  cat my_code.py | python cli.py review -
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Review command
    review_parser = subparsers.add_parser('review', help='Comprehensive code review with all analyzers')
    review_parser.add_argument('file', help='File to review (use - for stdin)')
    review_parser.add_argument(
        '--context',
        help='Additional context about the code',
        default=None
    )
    review_parser.add_argument(
        '--language',
        help='Programming language',
        default='python'
    )
    review_parser.add_argument(
        '--output',
        help='Output file (default: stdout)',
        default=None
    )
    review_parser.add_argument(
        '--format',
        choices=['text', 'json'],
        default='text',
        help='Output format'
    )
    review_parser.add_argument(
        '--codebase',
        action='store_true',
        help='Enable codebase analysis for full project context (recommended)'
    )
    review_parser.add_argument(
        '--project-root',
        help='Project root directory for codebase analysis',
        default='.'
    )

    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize knowledge base')

    # Add practice command
    practice_parser = subparsers.add_parser(
        'add-practice',
        help='Add best practice to knowledge base'
    )
    practice_parser.add_argument('practice', help='Best practice description')
    practice_parser.add_argument('--category', required=True, help='Category')

    # Add issue command
    issue_parser = subparsers.add_parser(
        'add-issue',
        help='Add common issue to knowledge base'
    )
    issue_parser.add_argument('issue', help='Common issue description')
    issue_parser.add_argument('--category', required=True, help='Category')

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show comprehensive system statistics')
    stats_parser.add_argument(
        '--codebase',
        action='store_true', 
        help='Include codebase analysis statistics'
    )
    
    # Function analysis command
    func_parser = subparsers.add_parser('analyze-function', help='Analyze function impact and dependencies')
    func_parser.add_argument('function', help='Function name to analyze')
    func_parser.add_argument('--file', help='File containing the function')
    func_parser.add_argument('--project-root', default='.', help='Project root directory')

    args = parser.parse_args()

    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key and args.command == 'review':
        print("❌ ERROR: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        print("Set with: export OPENAI_API_KEY=your-key-here", file=sys.stderr)
        sys.exit(1)

    # Initialize enhanced code reviewer
    try:
        print("🔧 Initializing Enhanced Code Review System...", file=sys.stderr)
        reviewer = CodeReviewer(openai_api_key=api_key or "dummy")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize reviewer: {e}", file=sys.stderr)
        sys.exit(1)

    # Execute command
    if args.command == 'review':
        # Initialize knowledge base
        print("📚 Loading knowledge base...", file=sys.stderr)
        reviewer.initialize_knowledge_base()
        
        # Enable codebase analysis if requested
        if args.codebase:
            print(f"📊 Analyzing codebase at {args.project_root}...", file=sys.stderr)
            reviewer.enable_codebase_analysis(args.project_root)
        
        # Read code
        if args.file == '-':
            code = sys.stdin.read()
            filename = "stdin"
            file_path_for_analysis = None
        else:
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"❌ ERROR: File not found: {args.file}", file=sys.stderr)
                sys.exit(1)

            code = file_path.read_text()
            filename = args.file
            file_path_for_analysis = args.file

        # Comprehensive review
        print(f"🔍 Running comprehensive analysis on {filename}...", file=sys.stderr)
        review = reviewer.review_code(
            code=code,
            language=args.language, 
            file_path=file_path_for_analysis,
            context=args.context
        )

        # Format output
        if args.format == 'json':
            output = json.dumps(review, indent=2)
        else:
            output = format_comprehensive_review_output(review)

        # Write output
        if args.output:
            Path(args.output).write_text(output)
            print(f"✅ Review saved to: {args.output}", file=sys.stderr)
        else:
            print(output)

    elif args.command == 'init':
        print("📚 Initializing knowledge base...")
        reviewer.initialize_knowledge_base()
        print("✅ Knowledge base initialized successfully!")
        print(f"   📖 Best practices: {reviewer.best_practices.count()}")
        print(f"   🚨 Common issues: {reviewer.common_issues.count()}")

    elif args.command == 'add-practice':
        reviewer.add_best_practice(args.practice, args.category)
        print(f"✅ Added best practice: {args.practice}")

    elif args.command == 'add-issue':
        reviewer.add_common_issue(args.issue, args.category)
        print(f"✅ Added common issue: {args.issue}")

    elif args.command == 'stats':
        print("📊 ENHANCED CODE REVIEW SYSTEM STATISTICS")
        print("=" * 50)
        print(f"📖 Knowledge Base:")
        print(f"  • Best Practices: {reviewer.best_practices.count()}")
        print(f"  • Common Issues: {reviewer.common_issues.count()}")
        
        if args.codebase:
            print(f"\n📊 Initializing codebase analysis...")
            reviewer.enable_codebase_analysis(".")
            print(f"🔍 Codebase Analysis:")
            print(f"  • Files analyzed: {len(reviewer.codebase_analyzer.all_files)}")
            print(f"  • Functions found: {len(reviewer.codebase_analyzer.all_functions)}")
            print(f"  • Dependencies mapped: {len(reviewer.codebase_analyzer.dependency_graph)}")
        
        print(f"\n🔧 Last Analysis Results:")
        results = reviewer.last_analysis_results
        print(f"  • Codebase issues: {len(results.get('codebase_issues', []))}")
        print(f"  • Pattern issues: {len(results.get('pattern_issues', []))}")  
        print(f"  • Type issues: {len(results.get('type_issues', []))}")
        print(f"  • Duplicate issues: {len(results.get('duplicate_issues', []))}")
        print(f"  • Total verified issues: {results.get('total_issues', 0)}")

    elif args.command == 'analyze-function':
        print(f"📊 Analyzing function '{args.function}'...")
        reviewer.enable_codebase_analysis(args.project_root)
        
        # Build function key
        if args.file:
            func_key = f"{args.file}::{args.function}"
        else:
            # Search for function across all files
            matching_funcs = []
            for func_key in reviewer.codebase_analyzer.all_functions.keys():
                if args.function in func_key:
                    matching_funcs.append(func_key)
            
            if not matching_funcs:
                print(f"❌ Function '{args.function}' not found in codebase")
                sys.exit(1)
            elif len(matching_funcs) > 1:
                print(f"🔍 Multiple functions found:")
                for func in matching_funcs:
                    print(f"  - {func}")
                print("Please specify --file parameter")
                sys.exit(1)
            else:
                func_key = matching_funcs[0]
        
        # Get analyses
        impact = reviewer.codebase_analyzer.get_function_impact_chain(func_key)
        deps = reviewer.codebase_analyzer.analyze_function_dependencies(func_key)
        
        print(f"\n🎯 FUNCTION IMPACT ANALYSIS")
        print("=" * 50)
        print(f"Function: {impact.get('function_name', 'N/A')}")
        print(f"File: {impact.get('file_path', 'N/A')}")
        print(f"Line: {impact.get('line_number', 'N/A')}")
        print(f"Risk Level: {impact.get('risk_level', 'N/A')}")
        print(f"Risk Score: {impact.get('risk_score', 'N/A')}")
        print(f"Direct Callers: {impact.get('direct_callers', 0)}")
        print(f"Total Upstream: {impact.get('total_upstream_functions', 0)}")
        print(f"Total Downstream: {impact.get('total_downstream_functions', 0)}")
        print(f"Affected Files: {impact.get('affected_files', 0)}")
        
        print(f"\n🔗 DEPENDENCY ANALYSIS") 
        print("=" * 50)
        analysis = deps.get('analysis', {})
        print(f"Direct Calls: {analysis.get('direct_calls', 0)}")
        print(f"External Dependencies: {analysis.get('external_dependencies', 0)}")
        print(f"Internal Dependencies: {analysis.get('internal_dependencies', 0)}")
        print(f"Is Leaf Function: {analysis.get('is_leaf_function', False)}")
        print(f"Is Entry Point: {analysis.get('is_entry_point', False)}")
        print(f"Coupling Score: {analysis.get('coupling_score', 0):.2f}")
        
        recommendations = deps.get('recommendations', [])
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in recommendations:
                print(f"  • {rec}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()