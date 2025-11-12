"""
Code Reviewer - Orchestrator
Combines graph analysis + pattern matching + type checking + duplicate detection + RAG + GPT
All analyzers do heavy lifting, GPT organizes and adds suggestions
"""

import os
import json
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
from sentence_transformers import SentenceTransformer
import chromadb
import ast

# Import all our analyzers
from Codebase_analyzer import CodebaseAnalyzer, CodeIssue
from pattern_matcher import PatternMatcher, PatternIssue
from type_analyzer import TypeAnalyzer, TypeIssue  
from duplicate_detector import DuplicateDetector, DuplicateIssue


class CodeReviewer:
    """
    Main code reviewer - orchestrates everything

    Workflow:
    1. Codebase analyzer finds dependency/call graph issues
    2. Pattern matcher finds AST antipatterns  
    3. Type analyzer finds signature/type issues
    4. Duplicate detector finds code duplicates
    5. RAG provides context
    6. GPT organizes and adds logic/security suggestions
    """

    def __init__(
            self,
            openai_api_key: str,
            analyzer: Optional[CodebaseAnalyzer] = None,
            pattern_matcher: Optional[PatternMatcher] = None,
            type_analyzer: Optional[TypeAnalyzer] = None,
            duplicate_detector: Optional[DuplicateDetector] = None,
            embedding_model: str = "all-MiniLM-L6-v2",
            vector_db_path: str = "./chroma_db",
            skip_duplicate_detection: bool = False  # New parameter for large repos
    ):
        """Initialize reviewer with all analyzers"""
        self.client = OpenAI(api_key=openai_api_key)
        
        # Initialize all analyzers
        self.codebase_analyzer = analyzer or CodebaseAnalyzer()
        self.pattern_matcher = pattern_matcher or PatternMatcher()
        self.type_analyzer = type_analyzer or TypeAnalyzer()
        self.duplicate_detector = duplicate_detector or DuplicateDetector()
        self.skip_duplicate_detection = skip_duplicate_detection
        
        self.embedding_model = SentenceTransformer(embedding_model)

        # Initialize ChromaDB for RAG
        self.chroma_client = chromadb.PersistentClient(path=vector_db_path)

        try:
            self.best_practices = self.chroma_client.get_collection("best_practices")
        except:
            self.best_practices = self.chroma_client.create_collection("best_practices")

        try:
            self.common_issues = self.chroma_client.get_collection("common_issues")
        except:
            self.common_issues = self.chroma_client.create_collection("common_issues")
            
        # Store results from each analyzer for access
        self.last_analysis_results = {
            'codebase_issues': [],
            'pattern_issues': [],
            'type_issues': [],
            'duplicate_issues': [],
            'total_issues': 0
        }

    def enable_codebase_analysis(self, project_root: str = "."):
        """Enable codebase-aware reviews"""
        self.codebase_analyzer.build_graph(project_root)

    def review_code(
            self,
            code: str,
            language: str = "python",
            file_path: Optional[str] = None,
            context: Optional[str] = None
    ) -> Dict:
        """
        Comprehensive code review with ALL analyzers

        Returns dict with review results from all analyzers
        """
        print(f"\n🔍 Starting comprehensive code review...")

        all_issues = []
        
        # Step 1: Codebase analysis (dependency/call graph issues)
        codebase_issues = []
        if self.codebase_analyzer.is_analyzed and file_path:
            print("📊 Running codebase dependency/call graph analysis...")
            try:
                import time
                codebase_start = time.time()
                codebase_issues = self.codebase_analyzer.analyze_file(file_path)
                codebase_time = time.time() - codebase_start
                
                if codebase_issues:
                    all_issues.extend(self._convert_codebase_issues(codebase_issues))
                    print(f"✅ Found {len(codebase_issues)} codebase issues ({codebase_time:.1f}s)")
                else:
                    print(f"✅ Codebase analysis completed ({codebase_time:.1f}s) - no issues found")
            except Exception as e:
                print(f"⚠️ Codebase analysis failed for {file_path}: {e}")
                # Continue with other analysis even if codebase analysis fails

        # Step 2: Pattern matching (AST antipattern detection)
        pattern_issues = []
        if file_path:
            print("🔍 Running AST pattern matching...")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                tree = ast.parse(source_code)
                pattern_issues = self.pattern_matcher.find_antipatterns(tree, file_path, source_code)
                all_issues.extend(self._convert_pattern_issues(pattern_issues))
                print(f"✅ Found {len(pattern_issues)} pattern issues")
            except Exception as e:
                print(f"⚠️ Pattern analysis failed: {e}")

        # Step 3: Type analysis (signature validation)  
        type_issues = []
        if self.codebase_analyzer.is_analyzed:
            print("🔎 Running type signature analysis...")
            type_issues = self.type_analyzer.analyze_types(
                self.codebase_analyzer.all_functions, 
                self.codebase_analyzer.all_files,
                target_file=file_path  # Only analyze issues in the target file
            )
            all_issues.extend(self._convert_type_issues(type_issues))
            print(f"✅ Found {len(type_issues)} type issues")

        # Step 4: Duplicate detection (skip for large repos to prevent memory issues)
        duplicate_issues = []
        print(f"🔍 Duplicate detection check: codebase_analyzed={self.codebase_analyzer.is_analyzed}, skip_duplicate={self.skip_duplicate_detection}")
        if self.codebase_analyzer.is_analyzed and not self.skip_duplicate_detection:
            print("🔄 Running duplicate code detection...")
            try:
                duplicate_issues = self.duplicate_detector.analyze_duplicates(
                    self.codebase_analyzer.all_functions,
                    self.codebase_analyzer.all_files
                )
                all_issues.extend(self._convert_duplicate_issues(duplicate_issues))
                print(f"✅ Found {len(duplicate_issues)} duplicate issues")
            except Exception as e:
                print(f"⚠️ Duplicate detection failed: {e}")
                print("📊 Continuing with other analysis steps...")
        elif self.skip_duplicate_detection:
            print("⏭️ Skipping duplicate detection for large repository (memory optimization)")
        else:
            print("⏭️ Skipping duplicate detection (codebase not analyzed)")

        # Step 5: Get RAG context
        print("📚 Retrieving RAG context...")
        rag_context = self._get_rag_context(code)
        print(f"✅ Retrieved {len(rag_context)} relevant items from knowledge base")

        # Step 6: Analyze code structure
        structure_analysis = self._analyze_code_structure(code)

        # Step 7: Filter and prioritize issues like a senior engineer
        print("🧠 Filtering for high-impact issues...")
        high_impact_issues = self._filter_senior_engineer_issues(all_issues)
        print(f"✅ Filtered to {len(high_impact_issues)} critical issues (from {len(all_issues)} total)")

        # Step 8: Send to GPT with FILTERED high-impact issues
        print("🤖 Sending to GPT for senior-level analysis...")
        review = self._call_gpt_with_all_evidence(
            code,
            high_impact_issues,
            rag_context,
            structure_analysis,
            context,
            {
                'codebase': len(codebase_issues),
                'patterns': len(pattern_issues),
                'types': len(type_issues),
                'duplicates': len(duplicate_issues),
                'filtered_count': len(high_impact_issues),
                'original_count': len(all_issues)
            }
        )

        # Store analysis results for later access
        self.last_analysis_results = {
            'codebase_issues': codebase_issues,
            'pattern_issues': pattern_issues,
            'type_issues': type_issues,
            'duplicate_issues': duplicate_issues,
            'total_issues': len(all_issues)
        }

        print("✅ Comprehensive review complete!\n")
        return review
        
    def _convert_codebase_issues(self, issues: List[CodeIssue]) -> List[Dict]:
        """Convert codebase issues to standard format"""
        return [
            {
                "severity": issue.severity,
                "line": issue.line,
                "issue": issue.issue,
                "suggestion": issue.suggestion,
                "category": issue.category,
                "source": "codebase_analyzer",
                "evidence": issue.evidence
            }
            for issue in issues
        ]
        
    def _convert_pattern_issues(self, issues: List[PatternIssue]) -> List[Dict]:
        """Convert pattern issues to standard format"""
        return [
            {
                "severity": issue.severity,
                "line": issue.line,
                "issue": issue.message,
                "suggestion": issue.suggestion,
                "category": f"pattern_{issue.rule_id}",
                "source": "pattern_matcher",
                "evidence": issue.evidence
            }
            for issue in issues
        ]
        
    def _convert_type_issues(self, issues: List[TypeIssue]) -> List[Dict]:
        """Convert type issues to standard format"""
        return [
            {
                "severity": issue.severity,
                "line": issue.line,
                "issue": issue.message,
                "suggestion": issue.suggestion,
                "category": f"type_{issue.rule_id}",
                "source": "type_analyzer",
                "evidence": issue.evidence
            }
            for issue in issues
        ]
        
    def _convert_duplicate_issues(self, issues: List[DuplicateIssue]) -> List[Dict]:
        """Convert duplicate issues to standard format"""
        return [
            {
                "severity": issue.severity,
                "line": issue.line,
                "issue": issue.message,
                "suggestion": issue.suggestion,
                "category": f"duplicate_{issue.rule_id}",
                "source": "duplicate_detector",
                "evidence": issue.evidence
            }
            for issue in issues
        ]

    def _filter_senior_engineer_issues(self, all_issues: List[Dict]) -> List[Dict]:
        """
        Filter issues like a senior software engineer would:
        Focus ONLY on correctness, stability, performance, maintainability
        Ignore cosmetic/style issues
        """
        HIGH_IMPACT_CATEGORIES = {
            # CORRECTNESS - Logic errors, edge cases
            'circular_dependency': 10,  # Critical: will cause import failures
            'dead_code': 6,             # Warning: unused code clutters codebase
            'high_impact': 9,           # Critical: changing this breaks many things
            
            # STABILITY - Exceptions, crashes  
            'pattern_bare_except': 9,   # Critical: swallows all exceptions
            'pattern_dangerous_eval': 10, # Critical: security + injection risk
            'pattern_string_exceptions': 8, # Warning: deprecated, will break
            'type_signature_mismatch': 9, # Critical: runtime errors
            'type_mypy_error': 8,       # Warning: type errors
            
            # PERFORMANCE - Slow operations
            'pattern_nested_loops': 7,  # Warning: O(n^4) complexity 
            'complexity': 7,            # Warning: hard to test/maintain
            'pattern_long_functions': 6, # Suggestion: maintainability
            
            # MAINTAINABILITY - Coupling, patterns
            'duplicate_exact_duplicate': 8, # Warning: maintenance burden
            'pattern_deep_nesting': 6,  # Suggestion: readability
            'pattern_global_assignments': 7, # Warning: tight coupling
            
            # LOWER PRIORITY BUT STILL RELEVANT
            'pattern_magic_numbers': 4,     # Suggestion: maintainability  
            'duplicate_copy_paste_duplicate': 5, # Suggestion: reduce duplication
            'duplicate_similar_duplicate': 4,    # Suggestion: potential refactor
            'pattern_unused_variables': 3,      # Suggestion: clean code
            'type_missing_type_hints': 4,       # Suggestion: better documentation
            'unused_import': 3,                 # Suggestion: clean imports
            
            # ADDITIONAL CATEGORIES FOR BETTER DEMO VISIBILITY
            'pattern_long_parameter_list': 4,   # Suggestion: refactor parameters
            'pattern_complex_conditions': 5,    # Warning: hard to understand
            'pattern_string_formatting': 3,     # Suggestion: use f-strings
            'pattern_exception_handling': 6,    # Warning: poor exception handling
            'code_smell': 4,                    # Suggestion: general code smell
            'maintainability': 5,               # Warning: maintainability issue
            'readability': 3,                   # Suggestion: readability issue
            'performance': 6,                   # Warning: performance concern
            'unknown': 3,                       # Include unknown categories with low score
        }
        
        # Score and filter issues
        scored_issues = []
        
        for issue in all_issues:
            category = issue.get('category', 'unknown')
            severity = issue.get('severity', 'suggestion')
            evidence = issue.get('evidence', {})
            
            # Get base score from category
            base_score = HIGH_IMPACT_CATEGORIES.get(category, 0)
            
            if base_score == 0:
                continue  # Skip low-value issues
                
            # Boost score based on evidence and context
            final_score = base_score
            
            # Boost for critical severity
            if severity == 'critical':
                final_score += 3
            elif severity == 'warning':
                final_score += 1
                
            # Boost for high complexity/impact evidence
            if 'complexity' in evidence and evidence.get('complexity', 0) > 15:
                final_score += 2
            if 'impact_level' in evidence and evidence.get('impact_level') in ['HIGH', 'CRITICAL']:
                final_score += 3
            if 'called_by_count' in evidence and evidence.get('called_by_count', 0) > 10:
                final_score += 2
                
            # Reduce score for very common patterns (noise reduction)
            if category == 'duplicate_exact_duplicate' and len(all_issues) > 50:
                final_score -= 2
                
            # Only keep issues above threshold
            if final_score >= 3:  # Senior engineer threshold (lowered for demo visibility)
                scored_issues.append((final_score, issue))
        
        # Sort by score descending and take top 40 issues
        scored_issues.sort(key=lambda x: x[0], reverse=True)
        top_issues = [issue for score, issue in scored_issues[:40]]
        
        # Debug logging for filtering effectiveness
        print(f"🎯 Senior Engineer Filtering:")
        print(f"   📊 Input issues: {len(all_issues)}")
        print(f"   📊 Scored issues (≥3): {len(scored_issues)}")
        print(f"   📊 Top issues selected: {len(top_issues)}")
        
        # Group related issues to avoid spam
        final_issues = self._deduplicate_related_issues(top_issues)
        print(f"   📊 Final issues after deduplication: {len(final_issues)}")
        
        return final_issues
    
    def _deduplicate_related_issues(self, issues: List[Dict]) -> List[Dict]:
        """Remove duplicate/related issues to reduce noise"""
        seen_patterns = set()
        deduplicated = []
        
        for issue in issues:
            # Create a pattern key for deduplication
            category = issue.get('category', '')
            line = issue.get('line', 0)
            source = issue.get('source', '')
            
            # Group similar issues by pattern
            if category.startswith('duplicate_'):
                pattern = f"duplicate_{source}"
            elif category.startswith('pattern_'):
                pattern = f"pattern_{category.split('_')[-1]}_{line//10}"  # Group by 10-line blocks
            else:
                pattern = f"{category}_{line}"
                
            if pattern in seen_patterns:
                continue  # Skip similar issue
                
            seen_patterns.add(pattern)
            deduplicated.append(issue)
            
        return deduplicated[:20]  # Hard limit to 20 issues max

    def _get_rag_context(self, code: str, top_k: int = 5) -> List[Dict]:
        """Get relevant context from RAG"""
        code_embedding = self.embedding_model.encode(code).tolist()
        relevant_context = []

        # Query best practices
        if self.best_practices.count() > 0:
            results = self.best_practices.query(
                query_embeddings=[code_embedding],
                n_results=min(top_k, self.best_practices.count())
            )
            for i, doc in enumerate(results['documents'][0]):
                relevant_context.append({
                    "type": "best_practice",
                    "content": doc,
                    "metadata": results['metadatas'][0][i]
                })

        # Query common issues
        if self.common_issues.count() > 0:
            results = self.common_issues.query(
                query_embeddings=[code_embedding],
                n_results=min(top_k, self.common_issues.count())
            )
            for i, doc in enumerate(results['documents'][0]):
                relevant_context.append({
                    "type": "common_issue",
                    "content": doc,
                    "metadata": results['metadatas'][0][i]
                })

        return relevant_context

    def _call_gpt_with_all_evidence(
            self,
            code: str,
            all_issues: List[Dict],
            rag_context: List[Dict],
            structure_analysis: Dict,
            user_context: Optional[str],
            issue_counts: Dict[str, int]
    ) -> Dict:
        """
        Call GPT with ALL REAL issues from all analyzers
        GPT's job: organize issues + add logic/security suggestions
        """
        # Build context strings
        rag_str = "\n".join([f"- [{ctx['type']}] {ctx['content']}" for ctx in rag_context])

        # Build focused issue summary
        issue_summary = f"""
SENIOR ENGINEER STATIC ANALYSIS - HIGH-IMPACT ISSUES ONLY:
- Original scan found {issue_counts.get('original_count', 0)} total issues
- Filtered to {issue_counts.get('filtered_count', len(all_issues))} high-impact issues
- Focus areas: Correctness, Stability, Performance, Maintainability

FILTERED HIGH-IMPACT ISSUES (with concrete evidence):
{json.dumps(all_issues, indent=2)}
"""

        # Build senior engineer prompt
        prompt = f"""You are a SENIOR SOFTWARE ENGINEER conducting a deep code review. Your focus is on REAL BUGS and ARCHITECTURAL PROBLEMS, not style issues.

CODE TO REVIEW:
```python
{code}
```

{issue_summary}

KNOWLEDGE BASE CONTEXT:
{rag_str}

CODE STRUCTURE:
{json.dumps(structure_analysis, indent=2)}

{f"CONTEXT: {user_context}" if user_context else ""}

SENIOR ENGINEER ANALYSIS CRITERIA:
Focus ONLY on these areas (ignore cosmetic/style issues):

1. CORRECTNESS: Logic errors, edge cases, invalid inputs, null handling
2. STABILITY: Unhandled exceptions, crash scenarios, data inconsistencies  
3. PERFORMANCE: Inefficient algorithms, memory leaks, slow operations
4. MAINTAINABILITY: Tight coupling, overly complex functions, architectural issues

For each issue, analyze:
- What could break in production?
- What's the actual business impact?
- How would you fix this at the code level?

RESPONSE FORMAT - Senior Engineer Review:
{{
    "overall_quality": "1-10",
    "summary": "Executive summary of critical findings and production risks",
    "critical_findings": {{
        "correctness_issues": number,
        "stability_risks": number,
        "performance_problems": number,
        "maintainability_debt": number
    }},
    "issues": [
        {{
            "issue_type": "Critical|Warning|Suggestion",
            "location": "Function/Class name and line number",  
            "bug_risk": "What could go wrong in production",
            "failure_mode": "How this would manifest as a bug",
            "recommended_fix": "Exact code-level changes needed",
            "refactor_suggestion": "Optional architectural improvement",
            "business_impact": "High|Medium|Low"
        }}
    ],
    "architectural_recommendations": [
        "High-level structural improvements for long-term maintainability"
    ],
    "immediate_actions": [
        "Critical fixes needed before production deployment"
    ]
}}

Limit output to TOP 15-20 REAL ISSUES MAX. Quality over quantity. 
Each issue should be something that could cause:
- Runtime errors/crashes
- Security vulnerabilities  
- Performance degradation
- Maintenance headaches

Ignore: missing type hints, magic numbers, unused variables, minor style issues."""

        try:
            # Add timeout and retry logic to prevent infinite hangs
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("GPT API call timed out after 30 seconds")
                
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 second timeout
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0
            )
            
            signal.alarm(0)  # Cancel timeout
            response_text = response.choices[0].message.content

            # Clean and parse JSON
            response_text = response_text.strip()
            response_text = re.sub(r'```(?:json|python)?', '', response_text)
            response_text = response_text.replace("None", "null")
            response_text = response_text.replace("True", "true")
            response_text = response_text.replace("False", "false")

            try:
                review_data = json.loads(response_text)
            except json.JSONDecodeError:
                # If parsing fails, at least return all verified issues
                review_data = {
                    "overall_quality": "N/A",
                    "summary": "Could not parse GPT response",
                    "analyzer_counts": issue_counts,
                    "total_verified_issues": len(all_issues),
                    "issues": all_issues,
                    "strengths": [],
                    "recommendations": [],
                    "error": "JSON parsing failed"
                }

            # Add metadata
            review_data["structure_analysis"] = structure_analysis
            review_data["rag_context_used"] = len(rag_context)
            review_data["codebase_aware"] = self.codebase_analyzer.is_analyzed

            return review_data

        except Exception as e:
            # If GPT fails, still return all verified issues
            return {
                "overall_quality": "N/A",
                "summary": f"GPT call failed: {str(e)}",
                "analyzer_counts": issue_counts,
                "total_verified_issues": len(all_issues),
                "issues": all_issues,
                "strengths": [],
                "recommendations": [],
                "structure_analysis": structure_analysis,
                "rag_context_used": len(rag_context),
                "codebase_aware": self.codebase_analyzer.is_analyzed,
                "error": str(e)
            }

    def _analyze_code_structure(self, code: str) -> Dict:
        """Quick AST-based structure analysis"""
        try:
            tree = ast.parse(code)
            analysis = {
                "functions": [],
                "classes": [],
                "imports": [],
                "lines": len(code.split('\n'))
            }

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis["functions"].append({
                        "name": node.name,
                        "lineno": node.lineno,
                        "has_docstring": ast.get_docstring(node) is not None
                    })
                elif isinstance(node, ast.ClassDef):
                    analysis["classes"].append({
                        "name": node.name,
                        "lineno": node.lineno,
                        "has_docstring": ast.get_docstring(node) is not None
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    analysis["imports"].append("import")

            return analysis
        except:
            return {"error": "Could not parse code"}

    def _call_gpt_with_evidence(
            self,
            code: str,
            graph_issues: List[CodeIssue],
            rag_context: List[Dict],
            structure_analysis: Dict,
            user_context: Optional[str]
    ) -> Dict:
        """
        Call GPT with REAL issues from graph analysis
        GPT's job: organize issues + add logic/security suggestions
        """
        # Build context strings
        rag_str = "\n".join([f"- [{ctx['type']}] {ctx['content']}" for ctx in rag_context])

        # Convert graph issues to dict for prompt
        graph_issues_data = [
            {
                "severity": issue.severity,
                "line": issue.line,
                "issue": issue.issue,
                "suggestion": issue.suggestion,
                "category": issue.category,
                "evidence": issue.evidence
            }
            for issue in graph_issues
        ]

        # Build prompt
        prompt = f"""You are a code review assistant. You have REAL STATIC ANALYSIS RESULTS from graph analysis.

CODE TO REVIEW:
```python
{code}
```

REAL ISSUES FROM GRAPH ANALYSIS (with evidence):
{json.dumps(graph_issues_data, indent=2)}

These are VERIFIED issues from:
- DFS for circular dependencies
- Call graph analysis for dead code
- BFS for impact analysis
- Type hint extraction
- Complexity calculation

RAG KNOWLEDGE BASE CONTEXT:
{rag_str}

CODE STRUCTURE:
{json.dumps(structure_analysis, indent=2)}

{f"ADDITIONAL CONTEXT: {user_context}" if user_context else ""}

YOUR JOB:
1. Take the REAL issues from graph analysis (they have proof/evidence)
2. Organize them clearly
3. ADD any logic errors, security issues, or performance problems you notice
4. Format everything nicely

IMPORTANT: The graph issues are FACTS (verified by analysis). Don't question them.
Your additions should focus on:
- Logic errors
- Security vulnerabilities (SQL injection, XSS, etc.)
- Performance problems
- Code style issues

Return JSON in this EXACT format:
{{
    "overall_quality": "1-10",
    "summary": "brief summary",
    "graph_issues_count": {len(graph_issues)},
    "issues": [
        {{
            "severity": "critical|warning|suggestion",
            "line": number_or_null,
            "issue": "description",
            "suggestion": "how to fix",
            "category": "category",
            "source": "graph_analysis|gpt_analysis",
            "evidence": {{}} // only for graph issues
        }}
    ],
    "strengths": ["good practices observed"],
    "recommendations": ["improvement suggestions"]
}}

Include ALL graph issues in your output, plus any additional issues you find."""

        try:
            # Add timeout to prevent infinite hangs
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("GPT API call timed out after 30 seconds")
                
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 second timeout
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
                temperature=0
            )
            
            signal.alarm(0)  # Cancel timeout
            response_text = response.choices[0].message.content

            # Clean and parse JSON
            response_text = response_text.strip()
            response_text = re.sub(r'```(?:json|python)?', '', response_text)
            response_text = response_text.replace("None", "null")
            response_text = response_text.replace("True", "true")
            response_text = response_text.replace("False", "false")

            try:
                review_data = json.loads(response_text)
            except json.JSONDecodeError:
                # If parsing fails, at least return graph issues
                review_data = {
                    "overall_quality": "N/A",
                    "summary": "Could not parse GPT response",
                    "graph_issues_count": len(graph_issues),
                    "issues": graph_issues_data,
                    "strengths": [],
                    "recommendations": [],
                    "error": "JSON parsing failed"
                }

            # Add metadata
            review_data["structure_analysis"] = structure_analysis
            review_data["rag_context_used"] = len(rag_context)
            review_data["codebase_aware"] = self.analyzer.is_analyzed

            return review_data

        except Exception as e:
            # If GPT fails, still return graph issues
            return {
                "overall_quality": "N/A",
                "summary": f"GPT call failed: {str(e)}",
                "graph_issues_count": len(graph_issues),
                "issues": graph_issues_data,
                "strengths": [],
                "recommendations": [],
                "structure_analysis": structure_analysis,
                "rag_context_used": len(rag_context),
                "codebase_aware": self.analyzer.is_analyzed,
                "error": str(e)
            }

    # ==================== RAG MANAGEMENT ====================

    def add_best_practice(self, practice: str, category: str, metadata: Dict = None):
        """Add best practice to knowledge base"""
        embedding = self.embedding_model.encode(practice).tolist()
        meta = metadata or {}
        meta["category"] = category

        self.best_practices.add(
            embeddings=[embedding],
            documents=[practice],
            metadatas=[meta],
            ids=[f"bp_{self.best_practices.count() + 1}"]
        )

    def add_common_issue(self, issue: str, category: str, metadata: Dict = None):
        """Add common issue to knowledge base"""
        embedding = self.embedding_model.encode(issue).tolist()
        meta = metadata or {}
        meta["category"] = category

        self.common_issues.add(
            embeddings=[embedding],
            documents=[issue],
            metadatas=[meta],
            ids=[f"issue_{self.common_issues.count() + 1}"]
        )

    def initialize_knowledge_base(self):
        """Initialize RAG with best practices"""
        best_practices = [
            ("Use type hints for all function parameters", "typing"),
            ("Write docstrings for public functions", "documentation"),
            ("Use context managers for resource management", "resources"),
            ("Prefer list comprehensions when appropriate", "performance"),
            ("Use f-strings for string formatting", "style"),
            ("Handle specific exception types", "errors"),
            ("Use meaningful variable names", "readability"),
            ("Keep functions small and focused", "design"),
            ("Avoid global variables", "design"),
            ("Use dataclasses for data structures", "data_structures"),
        ]

        for practice, category in best_practices:
            try:
                self.add_best_practice(practice, category)
            except:
                pass

        common_issues = [
            ("Missing input validation can lead to security vulnerabilities", "security"),
            ("Bare except clauses catch all exceptions", "bugs"),
            ("Mutable default arguments are shared", "bugs"),
            ("Using == instead of 'is' for None", "style"),
            ("Not closing files can leak resources", "resources"),
            ("Deeply nested code is hard to maintain", "readability"),
            ("Magic numbers make code unclear", "readability"),
            ("SQL injection risk with string formatting", "security"),
            ("Race conditions without proper locks", "concurrency"),
            ("Circular references can cause memory leaks", "memory"),
        ]

        for issue, category in common_issues:
            try:
                self.add_common_issue(issue, category)
            except:
                pass