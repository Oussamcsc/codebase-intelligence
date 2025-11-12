"""
Enhanced Modular Code Review Scanner
Uses the new modular architecture with all analyzers
"""

import os
from Code_reviewer import CodeReviewer

def format_comprehensive_review_output(review: dict) -> str:
    """Format senior engineer review results for display"""
    output = []
    output.append("=" * 100)
    output.append("👨‍💻 SENIOR SOFTWARE ENGINEER CODE REVIEW")
    output.append("=" * 100)
    
    # Executive summary
    output.append(f"\n📊 Overall Code Quality: {review.get('overall_quality', 'N/A')}/10")
    output.append(f"📝 Executive Summary: {review.get('summary', 'N/A')}")
    
    # Critical findings breakdown
    critical_findings = review.get('critical_findings', {})
    if critical_findings:
        output.append(f"\n🎯 CRITICAL FINDINGS BREAKDOWN:")
        output.append(f"  🔴 Correctness Issues: {critical_findings.get('correctness_issues', 0)}")
        output.append(f"  ⚠️ Stability Risks: {critical_findings.get('stability_risks', 0)}")
        output.append(f"  🐌 Performance Problems: {critical_findings.get('performance_problems', 0)}")
        output.append(f"  🔧 Maintainability Debt: {critical_findings.get('maintainability_debt', 0)}")
    
    # Analyzer filtering stats
    analyzer_counts = review.get('analyzer_counts', {})
    filtered_count = analyzer_counts.get('filtered_count', 0)
    original_count = analyzer_counts.get('original_count', 0)
    
    if original_count > 0:
        output.append(f"\n🧠 INTELLIGENT FILTERING:")
        output.append(f"  📊 Raw Issues Found: {original_count}")
        output.append(f"  🎯 High-Impact Issues: {filtered_count}")
        output.append(f"  🗑️ Low-Value Issues Filtered: {original_count - filtered_count}")
        output.append(f"  ✨ Signal-to-Noise Improvement: {((original_count - filtered_count) / original_count * 100):.1f}% noise removed")
    
    # Senior engineer issues section
    issues = review.get('issues', [])
    if issues:
        output.append(f"\n" + "=" * 100)
        output.append(f"🚨 CRITICAL CODE REVIEW FINDINGS ({len(issues)} issues)")
        output.append("=" * 100)
        
        for i, issue in enumerate(issues, 1):
            # Handle both old and new issue format
            issue_type = issue.get('issue_type', issue.get('severity', 'Warning'))
            location = issue.get('location', f"Line {issue.get('line', 'N/A')}")
            bug_risk = issue.get('bug_risk', issue.get('issue', 'N/A'))
            failure_mode = issue.get('failure_mode', 'Runtime behavior undefined')
            recommended_fix = issue.get('recommended_fix', issue.get('suggestion', 'See description'))
            refactor_suggestion = issue.get('refactor_suggestion', '')
            business_impact = issue.get('business_impact', 'Medium')
            
            # Issue type icons
            type_icons = {
                'Critical': '🔴',
                'Warning': '🟡', 
                'Suggestion': '🔵',
                'critical': '🔴',
                'warning': '🟡',
                'suggestion': '🔵'
            }
            icon = type_icons.get(issue_type, '⚪')
            
            output.append(f"\n{icon} ISSUE #{i}: {issue_type.upper()}")
            output.append("─" * 60)
            output.append(f"📍 Location: {location}")
            output.append(f"🐛 Bug Risk: {bug_risk}")
            output.append(f"💥 Failure Mode: {failure_mode}")
            output.append(f"🔧 Recommended Fix: {recommended_fix}")
            if refactor_suggestion:
                output.append(f"♻️ Refactor Suggestion: {refactor_suggestion}")
            output.append(f"💼 Business Impact: {business_impact}")
            
            # Show evidence for verified static analysis issues
            evidence = issue.get('evidence', {})
            if evidence:
                output.append(f"🔬 Static Analysis Evidence: {evidence.get('detection_method', 'verified')}")
                
                # Key evidence metrics
                key_metrics = ['complexity', 'impact_level', 'called_by_count', 'similarity_score']
                for metric in key_metrics:
                    if metric in evidence:
                        output.append(f"   • {metric}: {evidence[metric]}")
    
    # Architectural recommendations
    arch_recommendations = review.get('architectural_recommendations', [])
    if arch_recommendations:
        output.append(f"\n" + "=" * 100)
        output.append("🏗️ ARCHITECTURAL RECOMMENDATIONS")
        output.append("=" * 100)
        for i, rec in enumerate(arch_recommendations, 1):
            output.append(f"{i}. {rec}")
    
    # Immediate actions  
    immediate_actions = review.get('immediate_actions', [])
    if immediate_actions:
        output.append(f"\n" + "=" * 100)
        output.append("⚡ IMMEDIATE ACTIONS REQUIRED")
        output.append("=" * 100)
        for i, action in enumerate(immediate_actions, 1):
            output.append(f"🚨 {i}. {action}")
    
    # Strengths
    strengths = review.get('strengths', [])
    if strengths:
        output.append(f"\n" + "=" * 100)
        output.append("✅ STRENGTHS")
        output.append("=" * 100)
        for strength in strengths:
            output.append(f"✅ {strength}")
    
    # Recommendations
    recommendations = review.get('recommendations', [])
    if recommendations:
        output.append(f"\n" + "=" * 100)
        output.append("💡 RECOMMENDATIONS")
        output.append("=" * 100)
        for rec in recommendations:
            output.append(f"💡 {rec}")
    
    # Impact analysis
    impact = review.get('impact_analysis')
    if impact:
        output.append(f"\n" + "=" * 100)
        output.append("📈 CHANGE IMPACT ANALYSIS")
        output.append("=" * 100)
        output.append(f"📈 {impact}")
    
    # Code structure
    structure = review.get('structure_analysis', {})
    if structure and 'error' not in structure:
        output.append(f"\n" + "=" * 100)
        output.append("📊 CODE STRUCTURE")
        output.append("=" * 100)
        output.append(f"📄 Lines: {structure.get('lines', 0)}")
        output.append(f"🔧 Functions: {len(structure.get('functions', []))}")
        output.append(f"🏗️ Classes: {len(structure.get('classes', []))}")
        output.append(f"📦 Imports: {len(structure.get('imports', []))}")
    
    # Error handling
    if 'error' in review:
        output.append(f"\n⚠️ Warning: {review['error']}")
    
    output.append("\n" + "=" * 100)
    output.append("🚀 Analysis powered by modular static analyzers + RAG + GPT-4")
    output.append("=" * 100)
    
    return "\n".join(output)


def main():
    """Main execution function"""
    print("🚀 Initializing Comprehensive Code Review System...")
    
    # Get OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        return
    
    # Initialize the comprehensive code reviewer
    print("🔧 Loading all analyzers (codebase, patterns, types, duplicates)...")
    reviewer = CodeReviewer(openai_api_key=api_key)
    
    # Initialize RAG knowledge base
    print("📚 Initializing knowledge base...")
    reviewer.initialize_knowledge_base()
    
    # Scan the current folder for codebase analysis
    print("📊 Analyzing entire codebase (building dependency and call graphs)...")
    reviewer.enable_codebase_analysis(".")
    
    print("✅ System ready! All analyzers loaded and codebase analyzed.\n")
    
    # Ask the user which file to review
    while True:
        file_to_review = input("📁 Enter the relative path of the file to review (or 'quit' to exit): ").strip()
        
        if file_to_review.lower() in ['quit', 'exit', 'q']:
            print("👋 Goodbye!")
            break
            
        if not file_to_review:
            print("❌ Please enter a valid file path")
            continue
        
        # Check if file exists
        if not os.path.exists(file_to_review):
            print(f"❌ File '{file_to_review}' not found. Make sure the path is correct.")
            continue
            
        # Check if it's a Python file
        if not file_to_review.endswith('.py'):
            print("⚠️ Warning: This tool is optimized for Python files (.py)")
            proceed = input("Continue anyway? (y/N): ").strip().lower()
            if proceed not in ['y', 'yes']:
                continue
        
        print(f"\n🔍 Starting comprehensive analysis of: {file_to_review}")
        print("=" * 80)
        
        try:
            # Read the file
            with open(file_to_review, "r", encoding="utf-8") as f:
                code = f.read()
            
            # Run comprehensive review
            review = reviewer.review_code(
                code=code, 
                file_path=file_to_review,
                context=f"File: {file_to_review}"
            )
            
            # Display results
            print(format_comprehensive_review_output(review))
            
            # Option to save results
            save_option = input("\n💾 Save results to file? (y/N): ").strip().lower()
            if save_option in ['y', 'yes']:
                output_file = f"review_{os.path.basename(file_to_review)}.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(format_comprehensive_review_output(review))
                print(f"✅ Results saved to: {output_file}")
            
        except FileNotFoundError:
            print(f"❌ File '{file_to_review}' not found.")
        except Exception as e:
            print(f"❌ Error analyzing file: {e}")
        
        print("\n" + "="*80)


if __name__ == "__main__":
    main()
