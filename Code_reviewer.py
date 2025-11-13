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
    1. GPT first understands what the code does (code understanding phase)
    2. Codebase analyzer finds dependency/call graph issues
    3. Pattern matcher finds AST antipatterns
    4. Type analyzer finds signature/type issues
    5. Duplicate detector finds code duplicates
    6. RAG provides context
    7. GPT organizes and adds logic/security suggestions with exact code references
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

        # NEW STEP 0: Code Understanding Phase (what does this code do?)
        print("🧠 Phase 1: Understanding what the code does...")
        code_understanding = self._understand_code_purpose(code, file_path)
        print(f"✅ Code purpose understood: {code_understanding.get('summary', 'N/A')[:100]}...")

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
                    all_issues.extend(self._convert_codebase_issues(codebase_issues, code, file_path))
                    print(f"✅ Found {len(codebase_issues)} codebase issues ({codebase_time:.1f}s)")
                else:
                    print(f"✅ Codebase analysis completed ({codebase_time:.1f}s) - no issues found")
            except Exception as e:
                print(f"⚠️ Codebase analysis failed for {file_path}: {e}")

        # Step 2: Pattern matching (AST antipattern detection)
        pattern_issues = []
        if file_path:
            print("🔍 Running AST pattern matching...")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                tree = ast.parse(source_code)
                pattern_issues = self.pattern_matcher.find_antipatterns(tree, file_path, source_code)
                all_issues.extend(self._convert_pattern_issues(pattern_issues, code, file_path))
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
                target_file=file_path
            )
            all_issues.extend(self._convert_type_issues(type_issues, code, file_path))
            print(f"✅ Found {len(type_issues)} type issues")

        # Step 4: Duplicate detection
        duplicate_issues = []
        if self.codebase_analyzer.is_analyzed and not self.skip_duplicate_detection:
            print("🔄 Running duplicate code detection...")
            try:
                duplicate_issues = self.duplicate_detector.analyze_duplicates(
                    self.codebase_analyzer.all_functions,
                    self.codebase_analyzer.all_files
                )
                all_issues.extend(self._convert_duplicate_issues(duplicate_issues, code, file_path))
                print(f"✅ Found {len(duplicate_issues)} duplicate issues")
            except Exception as e:
                print(f"⚠️ Duplicate detection failed: {e}")
        elif self.skip_duplicate_detection:
            print("⏭️ Skipping duplicate detection for large repository")

        # Step 5: Get RAG context
        print("📚 Retrieving RAG context...")
        rag_context = self._get_rag_context(code)
        print(f"✅ Retrieved {len(rag_context)} relevant items from knowledge base")

        # Step 6: Analyze code structure
        structure_analysis = self._analyze_code_structure(code)

        # Step 7: Filter and prioritize issues
        print("🧠 Filtering for high-impact issues...")
        high_impact_issues = self._filter_senior_engineer_issues(all_issues)
        print(f"✅ Filtered to {len(high_impact_issues)} critical issues (from {len(all_issues)} total)")

        # Step 8: Send to GPT with code understanding + filtered issues
        print("🤖 Sending to GPT for senior-level analysis with exact code references...")
        review = self._call_gpt_with_all_evidence(
            code,
            high_impact_issues,
            rag_context,
            structure_analysis,
            context,
            code_understanding,
            {
                'codebase': len(codebase_issues),
                'patterns': len(pattern_issues),
                'types': len(type_issues),
                'duplicates': len(duplicate_issues),
                'filtered_count': len(high_impact_issues),
                'original_count': len(all_issues)
            }
        )

        # Store analysis results
        self.last_analysis_results = {
            'codebase_issues': codebase_issues,
            'pattern_issues': pattern_issues,
            'type_issues': type_issues,
            'duplicate_issues': duplicate_issues,
            'total_issues': len(all_issues)
        }

        print("✅ Comprehensive review complete!\n")
        return review

    def _understand_code_purpose(self, code: str, file_path: Optional[str] = None) -> Dict:
        """
        NEW: First understand what the code does before analyzing it
        Like a senior engineer would - understand the intent, THEN find problems
        """
        prompt = f"""You are a senior software engineer reviewing code. Before analyzing for bugs, you need to understand what this code is supposed to do.

FILE: {file_path or 'Unknown'}

CODE:
```python
{code[:3000]}  # First 3000 chars for understanding
```

Provide a brief analysis of:
1. What is the main purpose/responsibility of this code?
2. What are the key functions/classes and what do they do?
3. What are the critical flows or algorithms?
4. What external dependencies or integrations does it have?

Return JSON in this format:
{{
    "summary": "One sentence summary of what this code does",
    "main_purpose": "Detailed explanation of the code's purpose",
    "key_components": [
        {{"name": "function/class name", "purpose": "what it does"}}
    ],
    "critical_flows": ["description of important logic flows"],
    "dependencies": ["external libraries or systems it depends on"]
}}

Keep it concise - this is just for context before the real analysis."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0
            )

            response_text = response.choices[0].message.content.strip()
            response_text = re.sub(r'```(?:json|python)?', '', response_text)

            return json.loads(response_text)
        except Exception as e:
            return {
                "summary": "Could not understand code purpose",
                "error": str(e)
            }

    def _extract_code_snippet(self, code: str, line_number: int, context_lines: int = 2) -> Dict:
        """
        Extract the actual code snippet around a line number
        Shows the exact problematic code
        """
        lines = code.split('\n')

        if line_number <= 0 or line_number > len(lines):
            return {
                "snippet": "Line number out of range",
                "start_line": line_number,
                "end_line": line_number
            }

        # Get context around the line (0-indexed)
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)

        snippet_lines = lines[start:end]

        return {
            "snippet": '\n'.join(snippet_lines),
            "start_line": start + 1,
            "end_line": end,
            "problem_line": line_number
        }

    def _convert_codebase_issues(self, issues: List[CodeIssue], code: str, file_path: str) -> List[Dict]:
        """Convert codebase issues to standard format WITH code snippets"""
        converted = []
        for issue in issues:
            code_snippet = self._extract_code_snippet(code, issue.line)
            converted.append({
                "severity": issue.severity,
                "line": issue.line,
                "issue": issue.issue,
                "suggestion": issue.suggestion,
                "category": issue.category,
                "source": "codebase_analyzer",
                "evidence": issue.evidence,
                "code_snippet": code_snippet  # NEW: actual code
            })
        return converted

    def _convert_pattern_issues(self, issues: List[PatternIssue], code: str, file_path: str) -> List[Dict]:
        """Convert pattern issues to standard format WITH code snippets"""
        converted = []
        for issue in issues:
            code_snippet = self._extract_code_snippet(code, issue.line)
            converted.append({
                "severity": issue.severity,
                "line": issue.line,
                "issue": issue.message,
                "suggestion": issue.suggestion,
                "category": f"pattern_{issue.rule_id}",
                "source": "pattern_matcher",
                "evidence": issue.evidence,
                "code_snippet": code_snippet  # NEW: actual code
            })
        return converted

    def _convert_type_issues(self, issues: List[TypeIssue], code: str, file_path: str) -> List[Dict]:
        """Convert type issues to standard format WITH code snippets"""
        converted = []
        for issue in issues:
            code_snippet = self._extract_code_snippet(code, issue.line)
            converted.append({
                "severity": issue.severity,
                "line": issue.line,
                "issue": issue.message,
                "suggestion": issue.suggestion,
                "category": f"type_{issue.rule_id}",
                "source": "type_analyzer",
                "evidence": issue.evidence,
                "code_snippet": code_snippet  # NEW: actual code
            })
        return converted

    def _convert_duplicate_issues(self, issues: List[DuplicateIssue], code: str, file_path: str) -> List[Dict]:
        """Convert duplicate issues to standard format WITH code snippets"""
        converted = []
        for issue in issues:
            code_snippet = self._extract_code_snippet(code, issue.line)
            converted.append({
                "severity": issue.severity,
                "line": issue.line,
                "issue": issue.message,
                "suggestion": issue.suggestion,
                "category": f"duplicate_{issue.rule_id}",
                "source": "duplicate_detector",
                "evidence": issue.evidence,
                "code_snippet": code_snippet  # NEW: actual code
            })
        return converted

    def _filter_senior_engineer_issues(self, all_issues: List[Dict]) -> List[Dict]:
        """
        Filter issues like a senior software engineer would:
        Focus ONLY on correctness, stability, performance, maintainability
        """
        HIGH_IMPACT_CATEGORIES = {
            # CORRECTNESS
            'circular_dependency': 10,
            'dead_code': 6,
            'high_impact': 9,

            # STABILITY
            'pattern_bare_except': 9,
            'pattern_dangerous_eval': 10,
            'pattern_string_exceptions': 8,
            'type_signature_mismatch': 9,
            'type_mypy_error': 8,

            # PERFORMANCE
            'pattern_nested_loops': 7,
            'complexity': 7,
            'pattern_long_functions': 6,

            # MAINTAINABILITY
            'duplicate_exact_duplicate': 8,
            'pattern_deep_nesting': 6,
            'pattern_global_assignments': 7,

            # LOWER PRIORITY
            'pattern_magic_numbers': 4,
            'duplicate_copy_paste_duplicate': 5,
            'duplicate_similar_duplicate': 4,
            'pattern_unused_variables': 3,
            'type_missing_type_hints': 4,
            'unused_import': 3,
            'pattern_long_parameter_list': 4,
            'pattern_complex_conditions': 5,
            'pattern_string_formatting': 3,
            'pattern_exception_handling': 6,
            'code_smell': 4,
            'maintainability': 5,
            'readability': 3,
            'performance': 6,
            'unknown': 3,
        }

        scored_issues = []

        for issue in all_issues:
            category = issue.get('category', 'unknown')
            severity = issue.get('severity', 'suggestion')
            evidence = issue.get('evidence', {})

            base_score = HIGH_IMPACT_CATEGORIES.get(category, 0)
            if base_score == 0:
                continue

            final_score = base_score

            if severity == 'critical':
                final_score += 3
            elif severity == 'warning':
                final_score += 1

            if 'complexity' in evidence and evidence.get('complexity', 0) > 15:
                final_score += 2
            if 'impact_level' in evidence and evidence.get('impact_level') in ['HIGH', 'CRITICAL']:
                final_score += 3
            if 'called_by_count' in evidence and evidence.get('called_by_count', 0) > 10:
                final_score += 2

            if category == 'duplicate_exact_duplicate' and len(all_issues) > 50:
                final_score -= 2

            if final_score >= 3:
                scored_issues.append((final_score, issue))

        scored_issues.sort(key=lambda x: x[0], reverse=True)
        top_issues = [issue for score, issue in scored_issues[:40]]

        print(f"🎯 Senior Engineer Filtering:")
        print(f"   📊 Input issues: {len(all_issues)}")
        print(f"   📊 Scored issues (≥3): {len(scored_issues)}")
        print(f"   📊 Top issues selected: {len(top_issues)}")

        final_issues = self._deduplicate_related_issues(top_issues)
        print(f"   📊 Final issues after deduplication: {len(final_issues)}")

        return final_issues

    def _deduplicate_related_issues(self, issues: List[Dict]) -> List[Dict]:
        """Remove duplicate/related issues - AGGRESSIVE"""
        seen_patterns = set()
        seen_messages = set()
        deduplicated = []

        for issue in issues:
            category = issue.get('category', '')
            source = issue.get('source', '')
            message = issue.get('issue', '')

            normalized_msg = message[:50].lower().strip()

            if normalized_msg in seen_messages:
                continue

            if category.startswith('duplicate_'):
                pattern = f"duplicate_{source}"
            elif category.startswith('pattern_'):
                pattern = f"pattern_{category}"
            elif category == 'dead_code':
                pattern = f"dead_code"
            elif category == 'unused_import':
                pattern = f"unused_import"
            else:
                pattern = f"{category}_{source}"

            if pattern in seen_patterns:
                continue

            seen_patterns.add(pattern)
            seen_messages.add(normalized_msg)
            deduplicated.append(issue)

        return deduplicated[:15]

    def _get_rag_context(self, code: str, top_k: int = 5) -> List[Dict]:
        """Get relevant context from RAG"""
        code_embedding = self.embedding_model.encode(code).tolist()
        relevant_context = []

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
            code_understanding: Dict,
            issue_counts: Dict[str, int]
    ) -> Dict:
        """
        Call GPT with code understanding + ALL issues with exact code snippets
        GPT's job: organize issues + add logic/security suggestions with specific examples
        """
        rag_str = "\n".join([f"- [{ctx['type']}] {ctx['content']}" for ctx in rag_context])

        # Format issues with code snippets for better visibility
        formatted_issues = []
        for issue in all_issues:
            snippet = issue.get('code_snippet', {})
            formatted_issues.append({
                'severity': issue['severity'],
                'line': issue['line'],
                'issue': issue['issue'],
                'suggestion': issue['suggestion'],
                'category': issue['category'],
                'source': issue['source'],
                'actual_code': snippet.get('snippet', 'N/A'),
                'evidence': issue.get('evidence', {})
            })

        issue_summary = f"""
COMPREHENSIVE CODE ANALYSIS:

CODE PURPOSE (from Phase 1):
{json.dumps(code_understanding, indent=2)}

STATIC ANALYSIS RESULTS:
- Total issues found: {issue_counts.get('original_count', 0)}
- High-impact issues: {issue_counts.get('filtered_count', len(all_issues))}
- Analysis sources: Codebase Graph, AST Patterns, Type System, Duplication Detection

VERIFIED ISSUES WITH EXACT CODE:
{json.dumps(formatted_issues, indent=2)}
"""

        prompt = f"""You are a SENIOR SOFTWARE ENGINEER conducting a comprehensive code review.

You've already understood what this code does (Phase 1).
Now analyze the VERIFIED ISSUES with EXACT CODE REFERENCES.

FILE CODE:
```python
{code}
```

{issue_summary}

KNOWLEDGE BASE:
{rag_str}

CODE STRUCTURE:
{json.dumps(structure_analysis, indent=2)}

{f"USER CONTEXT: {user_context}" if user_context else ""}

YOUR SENIOR ENGINEER ANALYSIS:

First, provide:
1. WHAT THIS CODE DOES (based on Phase 1 understanding)
2. OVERALL CODE QUALITY ASSESSMENT

Then analyze issues focusing on:
- CORRECTNESS: Logic errors, edge cases, crashes
- STABILITY: Exception handling, error states
- PERFORMANCE: Inefficient algorithms, bottlenecks
- MAINTAINABILITY: Code complexity, coupling

For EACH issue, you must show:
- The EXACT problematic code (from the code_snippet data)
- WHY it's a problem (concrete impact)
- The EXACT fix (show the corrected code)

RESPONSE FORMAT:
{{
    "code_purpose": {{
        "summary": "What this code does (1-2 sentences)",
        "key_functionality": ["main features/responsibilities"]
    }},
    "overall_quality": "1-10",
    "quality_summary": "Executive summary of code quality and risks",
    "critical_findings": {{
        "correctness_issues": number,
        "stability_risks": number,
        "performance_problems": number,
        "maintainability_debt": number
    }},
    "issues": [
        {{
            "severity": "Critical|Warning|Suggestion",
            "location": "Function/line reference",
            "problematic_code": "EXACT code that's problematic",
            "bug_risk": "What could go wrong in production",
            "impact": "High|Medium|Low - concrete business impact",
            "fixed_code": "EXACT corrected code",
            "explanation": "Why this fix works"
        }}
    ],
    "strengths": ["Good practices observed in the code"],
    "architectural_recommendations": [
        "High-level improvements for better design"
    ],
    "immediate_actions": [
        "Critical fixes needed before deployment"
    ]
}}

CRITICAL REQUIREMENTS:
- Include "problematic_code" and "fixed_code" for EVERY issue
- Show EXACT code, not pseudo-code
- Limit to 15-20 most impactful issues
- Focus on production-breaking problems"""

        try:
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError("GPT API call timed out")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(45)  # 45 second timeout for comprehensive analysis

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5000,
                temperature=0
            )

            signal.alarm(0)
            response_text = response.choices[0].message.content

            response_text = response_text.strip()
            response_text = re.sub(r'```(?:json|python)?', '', response_text)
            response_text = response_text.replace("None", "null")
            response_text = response_text.replace("True", "true")
            response_text = response_text.replace("False", "false")

            try:
                review_data = json.loads(response_text)
            except json.JSONDecodeError:
                review_data = {
                    "code_purpose": code_understanding,
                    "overall_quality": "N/A",
                    "quality_summary": "Could not parse GPT response",
                    "analyzer_counts": issue_counts,
                    "total_verified_issues": len(all_issues),
                    "issues": all_issues,
                    "strengths": [],
                    "recommendations": [],
                    "error": "JSON parsing failed"
                }

            # Add metadata
            review_data["code_understanding"] = code_understanding
            review_data["structure_analysis"] = structure_analysis
            review_data["rag_context_used"] = len(rag_context)
            review_data["codebase_aware"] = self.codebase_analyzer.is_analyzed

            return review_data

        except Exception as e:
            return {
                "code_purpose": code_understanding,
                "overall_quality": "N/A",
                "quality_summary": f"GPT analysis failed: {str(e)}",
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