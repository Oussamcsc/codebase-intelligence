"""
Codebase Analyzer - Pure Graph Analysis Engine
Does ALL the heavy lifting: circular deps, dead code, impact analysis, etc.
NO GPT, NO RAG - just real static analysis
"""

import ast
import os
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class CodeIssue:
    """Issue found by static analysis"""
    severity: str  # 'critical', 'warning', 'suggestion'
    line: Optional[int]
    issue: str
    suggestion: str
    category: str
    evidence: Dict  # PROOF from graph analysis


@dataclass
class FunctionInfo:
    """Complete function information"""
    name: str
    file_path: str
    line_number: int
    parameters: List[Tuple[str, Optional[str]]]  # (name, type_hint)
    return_type: Optional[str]
    calls: List[str] = field(default_factory=list)
    called_by: List[str] = field(default_factory=list)
    complexity: int = 0
    is_public: bool = True
    docstring: Optional[str] = None


@dataclass
class ImpactMetrics:
    """Impact analysis for a function"""
    function_name: str
    file_path: str
    called_by_count: int
    called_by_files: List[str]
    downstream_functions: int
    downstream_files: int
    complexity: int

    def impact_level(self) -> str:
        """Calculate impact level"""
        score = self.called_by_count * 2 + self.downstream_functions
        if score > 20:
            return "CRITICAL"
        elif score > 10:
            return "HIGH"
        elif score > 5:
            return "MEDIUM"
        return "LOW"


class CodebaseAnalyzer:
    """
    Pure static analysis engine
    Builds graphs and performs REAL analysis
    """

    def __init__(self):
        self.project_root = None
        self.all_files = {}
        self.all_functions: Dict[str, FunctionInfo] = {}
        self.dependency_graph = defaultdict(set)  # file -> files
        self.function_call_graph = defaultdict(set)  # func -> funcs
        self.is_analyzed = False

    def _safe_relative_to(self, file_path: Path) -> str:
        """Safely get relative path, handling macOS symlink issues"""
        try:
            # Resolve both paths to handle symlinks (e.g., /var/folders -> /private/var/folders on macOS)
            resolved_file = Path(os.path.realpath(file_path))
            resolved_root = Path(os.path.realpath(self.project_root))
            return str(resolved_file.relative_to(resolved_root))
        except ValueError:
            # If relative_to fails, try with original paths
            try:
                return str(file_path.relative_to(self.project_root))
            except ValueError:
                # Last resort: return just the filename
                return file_path.name

    def build_graph(self, project_root: str = "."):
        """
        Build complete codebase graph
        This is where the magic happens!
        """
        print(f"\n🔍 Building codebase graph...")
        self.project_root = Path(project_root).resolve()

        # Phase 1: Parse all files
        print("📊 Phase 1: Parsing all Python files...")
        file_count = 0
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            try:
                result = self._parse_file(py_file)
                if result is not None:
                    file_count += 1
            except Exception as e:
                print(f"⚠️  Could not parse {py_file}: {e}")

        print(f"✅ Parsed {file_count} files, found {len(self.all_functions)} functions")

        # Phase 2: Build dependency graph
        print("📊 Phase 2: Building file dependency graph...")
        self._build_dependency_graph()

        # Phase 3: Build function call graph
        print("📊 Phase 3: Building function call graph...")
        self._build_function_call_graph()

        self.is_analyzed = True
        print("✅ Codebase graph complete!\n")

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_patterns = ['__pycache__', '.venv', 'venv', 'env', '.git']
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _parse_file(self, file_path: Path):
        """Parse a single file and extract everything"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)

            relative_path = self._safe_relative_to(file_path)
        except Exception as e:
            print(f"⚠️ Error parsing {file_path}: {e}")
            return None

        file_info = {
            "path": str(file_path),
            "relative_path": relative_path,
            "functions": {},
            "classes": [],
            "imports": [],
            "from_imports": {}
        }

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    file_info["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    file_info["imports"].append(node.module)
                    file_info["from_imports"][node.module] = [
                        alias.name for alias in node.names
                    ]

        # Extract functions and classes
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                func_info = self._extract_function_info(node, relative_path)
                file_info["functions"][func_info.name] = func_info
                self.all_functions[f"{relative_path}::{func_info.name}"] = func_info

            elif isinstance(node, ast.ClassDef):
                file_info["classes"].append(node.name)
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_info = self._extract_function_info(
                            item, relative_path, class_name=node.name
                        )
                        func_key = f"{node.name}.{method_info.name}"
                        file_info["functions"][func_key] = method_info
                        self.all_functions[f"{relative_path}::{func_key}"] = method_info

        self.all_files[relative_path] = file_info

    def _extract_function_info(
            self,
            node: ast.FunctionDef,
            file_path: str,
            class_name: str = None
    ) -> FunctionInfo:
        """Extract detailed function info with type hints"""
        # Get parameters with type hints
        params = []
        for arg in node.args.args:
            type_hint = None
            if arg.annotation:
                type_hint = self._get_type_string(arg.annotation)
            params.append((arg.arg, type_hint))

        # Get return type
        return_type = None
        if node.returns:
            return_type = self._get_type_string(node.returns)

        # Extract function calls
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_call_name(child.func)
                if call_name:
                    calls.append(call_name)

        # Calculate cyclomatic complexity
        complexity = self._calculate_complexity(node)

        # Check if public
        is_public = not node.name.startswith('_')

        # Get docstring
        docstring = ast.get_docstring(node)

        return FunctionInfo(
            name=node.name,
            file_path=file_path,
            line_number=node.lineno,
            parameters=params,
            return_type=return_type,
            calls=calls,
            complexity=complexity,
            is_public=is_public,
            docstring=docstring
        )

    def _get_type_string(self, annotation) -> str:
        """Extract type hint as string"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        elif isinstance(annotation, ast.Subscript):
            # Handle List[str], Dict[str, int], etc.
            base = self._get_type_string(annotation.value)
            return f"{base}[...]"
        return "Unknown"

    def _get_call_name(self, node) -> Optional[str]:
        """Get function call name"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return f"{node.value.id}.{node.attr}"
        return None

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def _build_dependency_graph(self):
        """Build file-level dependency graph"""
        for file_path, file_info in self.all_files.items():
            for imported_module in file_info["imports"]:
                # Try to resolve to internal file
                for other_file in self.all_files.keys():
                    if self._is_import_match(imported_module, other_file):
                        self.dependency_graph[file_path].add(other_file)

    def _is_import_match(self, import_name: str, file_path: str) -> bool:
        """Check if import matches file"""
        other_path_no_ext = str(Path(file_path).with_suffix(''))
        imported_as_path = import_name.replace('.', '/')

        if other_path_no_ext == imported_as_path:
            return True

        module_name = Path(file_path).stem
        if module_name == import_name or import_name.endswith(f".{module_name}"):
            return True

        return False

    def _build_function_call_graph(self):
        """Build function-level call graph"""
        for file_path, file_info in self.all_files.items():
            imported_functions = set()
            for module, items in file_info["from_imports"].items():
                imported_functions.update(items)

            for func_name, func_info in file_info["functions"].items():
                func_key = f"{file_path}::{func_name}"

                # Calls within same file
                for called_func in func_info.calls:
                    base_name = called_func.split('.')[-1]

                    if base_name in file_info["functions"]:
                        callee_key = f"{file_path}::{base_name}"
                        self.function_call_graph[func_key].add(callee_key)
                        if callee_key in self.all_functions:
                            self.all_functions[callee_key].called_by.append(func_key)

                    # Calls to imported functions
                    elif base_name in imported_functions:
                        for other_file in self.all_files.keys():
                            other_info = self.all_files[other_file]
                            if base_name in other_info["functions"]:
                                callee_key = f"{other_file}::{base_name}"
                                self.function_call_graph[func_key].add(callee_key)
                                if callee_key in self.all_functions:
                                    self.all_functions[callee_key].called_by.append(func_key)

    # ==================== REAL ANALYSIS METHODS ====================

    def analyze_file(self, file_path: str) -> List[CodeIssue]:
        """
        Run ALL static analysis on a file with timeout protection
        Returns list of issues with EVIDENCE
        """
        if not self.is_analyzed:
            return []

        # Convert to relative path
        if Path(file_path).is_absolute():
            file_path = self._safe_relative_to(Path(file_path))

        if file_path not in self.all_files:
            return []

        issues = []
        
        # Add overall timeout protection for the entire analysis
        import time
        analysis_start = time.time()
        MAX_FILE_ANALYSIS_TIME = 30  # 30 seconds max per file

        try:
            # 1. Find circular dependencies (with built-in timeout)
            if time.time() - analysis_start < MAX_FILE_ANALYSIS_TIME:
                issues.extend(self._find_circular_deps(file_path))

            # 2. Find unused imports
            if time.time() - analysis_start < MAX_FILE_ANALYSIS_TIME:
                issues.extend(self._find_unused_imports(file_path))

            # 3. Find dead code
            if time.time() - analysis_start < MAX_FILE_ANALYSIS_TIME:
                issues.extend(self._find_dead_code(file_path))

            # 4. Analyze impact (high impact = risky to change)
            if time.time() - analysis_start < MAX_FILE_ANALYSIS_TIME:
                issues.extend(self._analyze_impact(file_path))

            # 5. Find missing type hints
            if time.time() - analysis_start < MAX_FILE_ANALYSIS_TIME:
                issues.extend(self._find_missing_type_hints(file_path))
        except Exception as e:
            print(f"⚠️ Error in codebase analysis for {file_path}: {e}")
            return []

        # 6. Find high complexity
        issues.extend(self._find_high_complexity(file_path))

        return issues

    def _find_circular_deps(self, file_path: str) -> List[CodeIssue]:
        """Find circular dependencies using DFS with timeout protection"""
        issues = []

        # Add timeout protection for large codebases
        import time
        start_time = time.time()
        MAX_ANALYSIS_TIME = 10  # 10 seconds max per file
        MAX_PATH_LENGTH = 50    # Prevent extremely deep recursion

        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node, path):
            # Timeout protection
            if time.time() - start_time > MAX_ANALYSIS_TIME:
                return
            
            # Path length protection
            if len(path) > MAX_PATH_LENGTH:
                return
                
            if node in rec_stack:
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            if node in visited:
                return
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for neighbor in self.dependency_graph.get(node, []):
                dfs(neighbor, path.copy())
            rec_stack.remove(node)

        # Run DFS from all nodes with timeout protection
        try:
            for node in self.dependency_graph:
                if node not in visited:
                    if time.time() - start_time > MAX_ANALYSIS_TIME:
                        print(f"⚠️ Circular dependency analysis timed out for large codebase")
                        break
                    dfs(node, [])
        except Exception as e:
            print(f"⚠️ Error in circular dependency analysis: {e}")
            return []

        # Check if current file is in any cycle
        for cycle in cycles:
            if file_path in cycle:
                cycle_str = " → ".join([Path(f).name for f in cycle])
                issues.append(CodeIssue(
                    severity="critical",
                    line=None,
                    issue=f"Circular dependency detected: {cycle_str}",
                    suggestion="Refactor to remove circular imports. Extract shared code to a separate module or use dependency injection.",
                    category="circular_dependency",
                    evidence={
                        "cycle": cycle,
                        "cycle_length": len(cycle),
                        "detection_method": "DFS_on_dependency_graph"
                    }
                ))

        return issues

    def _find_unused_imports(self, file_path: str) -> List[CodeIssue]:
        """Find unused imports using call graph"""
        issues = []
        file_info = self.all_files[file_path]

        # Get all imported function names
        imported_functions = set()
        for module, items in file_info["from_imports"].items():
            imported_functions.update(items)

        # Get all function calls in this file
        all_calls = set()
        for func_info in file_info["functions"].values():
            for call in func_info.calls:
                base_name = call.split('.')[-1]
                all_calls.add(base_name)

        # Find unused
        unused = imported_functions - all_calls

        for unused_func in unused:
            issues.append(CodeIssue(
                severity="warning",
                line=None,
                issue=f"Imported function '{unused_func}' is never used in this file",
                suggestion=f"Remove unused import: {unused_func}",
                category="unused_import",
                evidence={
                    "import_name": unused_func,
                    "verified_by": "call_graph_analysis",
                    "total_calls_in_file": len(all_calls),
                    "total_imports": len(imported_functions)
                }
            ))

        return issues

    def _find_dead_code(self, file_path: str) -> List[CodeIssue]:
        """Find functions never called using call graph"""
        issues = []
        file_info = self.all_files[file_path]

        for func_name, func_info in file_info["functions"].items():
            # Skip private functions, main, etc.
            if func_name.startswith('_') or func_name in ['main', 'run', '__init__']:
                continue

            func_key = f"{file_path}::{func_name}"

            # Check if anyone calls this
            if not func_info.called_by:
                issues.append(CodeIssue(
                    severity="warning",
                    line=func_info.line_number,
                    issue=f"Function '{func_name}' is never called anywhere in the codebase",
                    suggestion="Remove dead code, or add a TODO comment if it's for future use",
                    category="dead_code",
                    evidence={
                        "function_name": func_name,
                        "verified_by": "call_graph_analysis",
                        "files_checked": len(self.all_files),
                        "is_public": func_info.is_public,
                        "complexity": func_info.complexity
                    }
                ))

        return issues

    def _analyze_impact(self, file_path: str) -> List[CodeIssue]:
        """Analyze impact of each function"""
        issues = []
        file_info = self.all_files[file_path]

        for func_name, func_info in file_info["functions"].items():
            metrics = self._calculate_impact_metrics(func_name, file_path)

            if metrics.impact_level() in ["HIGH", "CRITICAL"]:
                # Get unique files that call this
                caller_files = set()
                for caller_key in func_info.called_by:
                    caller_file = caller_key.split("::")[0]
                    caller_files.add(Path(caller_file).name)

                issues.append(CodeIssue(
                    severity="warning",
                    line=func_info.line_number,
                    issue=f"Function '{func_name}' has {metrics.impact_level()} impact: "
                          f"called by {metrics.called_by_count} functions across {len(metrics.called_by_files)} files",
                    suggestion=f"Be extremely careful when modifying this function. "
                               f"Changes will affect {metrics.downstream_functions} downstream functions. "
                               f"Consider adding comprehensive tests before making changes.",
                    category="high_impact",
                    evidence={
                        "impact_level": metrics.impact_level(),
                        "called_by_count": metrics.called_by_count,
                        "called_by_files": list(caller_files)[:5],  # Show top 5
                        "downstream_functions": metrics.downstream_functions,
                        "downstream_files": metrics.downstream_files,
                        "complexity": metrics.complexity,
                        "calculation_method": "BFS_through_call_graph"
                    }
                ))

        return issues

    def _calculate_impact_metrics(self, function_name: str, file_path: str) -> ImpactMetrics:
        """Calculate impact metrics using BFS"""
        func_key = f"{file_path}::{function_name}"

        if func_key not in self.all_functions:
            return ImpactMetrics(function_name, file_path, 0, [], 0, 0, 0)

        func_info = self.all_functions[func_key]

        # Get files that call this
        caller_files = set()
        for caller_key in func_info.called_by:
            caller_file = caller_key.split("::")[0]
            caller_files.add(caller_file)

        # BFS to calculate downstream impact
        visited = set()
        queue = [func_key]
        downstream_files = set()

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            current_file = current.split("::")[0]
            downstream_files.add(current_file)

            # Add all callers
            if current in self.all_functions:
                for caller in self.all_functions[current].called_by:
                    if caller not in visited:
                        queue.append(caller)

        return ImpactMetrics(
            function_name=function_name,
            file_path=file_path,
            called_by_count=len(func_info.called_by),
            called_by_files=list(caller_files),
            downstream_functions=len(visited) - 1,
            downstream_files=len(downstream_files) - 1,
            complexity=func_info.complexity
        )

    def _find_missing_type_hints(self, file_path: str) -> List[CodeIssue]:
        """Find functions missing type hints"""
        issues = []
        file_info = self.all_files[file_path]

        for func_name, func_info in file_info["functions"].items():
            # Skip private and special methods
            if func_name.startswith('_'):
                continue

            # Check for missing parameter type hints
            missing_params = [
                param[0] for param in func_info.parameters
                if param[1] is None and param[0] not in ['self', 'cls']
            ]

            # Check for missing return type
            missing_return = func_info.return_type is None

            if missing_params or missing_return:
                missing_str = []
                if missing_params:
                    missing_str.append(f"parameters: {', '.join(missing_params)}")
                if missing_return:
                    missing_str.append("return type")

                issues.append(CodeIssue(
                    severity="suggestion",
                    line=func_info.line_number,
                    issue=f"Function '{func_name}' is missing type hints for {' and '.join(missing_str)}",
                    suggestion="Add type hints to improve code documentation and enable static type checking",
                    category="type_hints",
                    evidence={
                        "function_name": func_name,
                        "missing_param_types": missing_params,
                        "missing_return_type": missing_return,
                        "total_params": len(func_info.parameters)
                    }
                ))

        return issues

    def _find_high_complexity(self, file_path: str) -> List[CodeIssue]:
        """Find overly complex functions"""
        issues = []
        file_info = self.all_files[file_path]

        for func_name, func_info in file_info["functions"].items():
            if func_info.complexity > 10:
                issues.append(CodeIssue(
                    severity="warning",
                    line=func_info.line_number,
                    issue=f"Function '{func_name}' has high cyclomatic complexity: {func_info.complexity}",
                    suggestion=f"Refactor this function into smaller functions. "
                               f"High complexity makes code harder to test and maintain. "
                               f"Target complexity: < 10",
                    category="complexity",
                    evidence={
                        "function_name": func_name,
                        "complexity": func_info.complexity,
                        "complexity_threshold": 10,
                        "recommended_max": 10
                    }
                ))

        return issues

    def get_file_summary(self, file_path: str) -> Dict:
        """Get summary info about a file"""
        if not self.is_analyzed:
            return {}

        if Path(file_path).is_absolute():
            file_path = self._safe_relative_to(Path(file_path))

        if file_path not in self.all_files:
            return {}

        file_info = self.all_files[file_path]

        # Get dependencies and dependents
        dependencies = list(self.dependency_graph.get(file_path, set()))
        dependents = [f for f, deps in self.dependency_graph.items() if file_path in deps]

        return {
            "dependencies": dependencies,
            "dependents": dependents,
            "function_count": len(file_info["functions"]),
            "class_count": len(file_info["classes"]),
            "import_count": len(file_info["imports"])
        }

    # ==================== DOWNSTREAM/UPSTREAM CALL ANALYSIS ====================

    def get_transitive_callees(self, func_key: str, max_depth: int = 10) -> Set[str]:
        """
        Get all functions called downstream from this function (BFS)
        
        Args:
            func_key: Function key in format "file_path::function_name"
            max_depth: Maximum traversal depth to prevent infinite loops
            
        Returns:
            Set of function keys that are called downstream
        """
        if not self.is_analyzed or func_key not in self.all_functions:
            return set()
            
        visited = set()
        queue = [(func_key, 0)]  # (function_key, depth)
        
        while queue:
            current_func, depth = queue.pop(0)
            
            if current_func in visited or depth >= max_depth:
                continue
                
            visited.add(current_func)
            
            # Add all functions this one calls
            for callee in self.function_call_graph.get(current_func, set()):
                if callee not in visited:
                    queue.append((callee, depth + 1))
                    
        # Remove the starting function from results
        visited.discard(func_key)
        return visited

    def get_transitive_callers(self, func_key: str, max_depth: int = 10) -> Set[str]:
        """
        Get all functions that call this function upstream (BFS)
        
        Args:
            func_key: Function key in format "file_path::function_name"
            max_depth: Maximum traversal depth to prevent infinite loops
            
        Returns:
            Set of function keys that call this function upstream
        """
        if not self.is_analyzed or func_key not in self.all_functions:
            return set()
            
        visited = set()
        queue = [(func_key, 0)]  # (function_key, depth)
        
        while queue:
            current_func, depth = queue.pop(0)
            
            if current_func in visited or depth >= max_depth:
                continue
                
            visited.add(current_func)
            
            # Add all functions that call this one
            if current_func in self.all_functions:
                for caller in self.all_functions[current_func].called_by:
                    if caller not in visited:
                        queue.append((caller, depth + 1))
                        
        # Remove the starting function from results
        visited.discard(func_key)
        return visited

    def get_affected_files_on_change(self, func_key: str) -> Set[str]:
        """
        Get all files that would be affected if this function changes
        
        Args:
            func_key: Function key in format "file_path::function_name"
            
        Returns:
            Set of file paths that would be affected
        """
        affected_files = set()
        
        # Get all upstream callers
        upstream_funcs = self.get_transitive_callers(func_key)
        
        # Extract file paths from function keys
        for caller_key in upstream_funcs:
            file_path = caller_key.split("::")[0]
            affected_files.add(file_path)
            
        # Also include files that directly import the file containing this function
        if func_key in self.all_functions:
            func_file = func_key.split("::")[0]
            for file_path, deps in self.dependency_graph.items():
                if func_file in deps:
                    affected_files.add(file_path)
                    
        return affected_files

    def get_function_impact_chain(self, func_key: str, max_depth: int = 5) -> Dict[str, Any]:
        """
        Get detailed impact chain analysis for a function
        
        Args:
            func_key: Function key in format "file_path::function_name"
            max_depth: Maximum chain depth to analyze
            
        Returns:
            Dictionary with impact chain details
        """
        if not self.is_analyzed or func_key not in self.all_functions:
            return {}
            
        func_info = self.all_functions[func_key]
        
        # Get downstream and upstream chains
        downstream = self.get_transitive_callees(func_key, max_depth)
        upstream = self.get_transitive_callers(func_key, max_depth)
        
        # Group by file
        downstream_files = defaultdict(list)
        upstream_files = defaultdict(list)
        
        for callee_key in downstream:
            file_path = callee_key.split("::")[0]
            func_name = callee_key.split("::")[-1]
            downstream_files[file_path].append(func_name)
            
        for caller_key in upstream:
            file_path = caller_key.split("::")[0] 
            func_name = caller_key.split("::")[-1]
            upstream_files[file_path].append(func_name)
            
        # Calculate risk metrics
        risk_score = self._calculate_risk_score(len(upstream), len(downstream), func_info.complexity)
        
        return {
            "function_name": func_info.name,
            "file_path": func_info.file_path,
            "line_number": func_info.line_number,
            "risk_level": self._get_risk_level(risk_score),
            "risk_score": risk_score,
            "direct_callers": len(func_info.called_by),
            "total_upstream_functions": len(upstream),
            "total_downstream_functions": len(downstream),
            "affected_files": len(self.get_affected_files_on_change(func_key)),
            "downstream_by_file": dict(downstream_files),
            "upstream_by_file": dict(upstream_files),
            "complexity": func_info.complexity,
            "is_public": func_info.is_public,
            "has_docstring": func_info.docstring is not None,
            "change_impact_summary": self._generate_impact_summary(upstream, downstream, func_info)
        }

    def _calculate_risk_score(self, upstream_count: int, downstream_count: int, complexity: int) -> float:
        """Calculate risk score for function changes"""
        # Weighted scoring: upstream callers are riskier than downstream calls
        upstream_weight = 3.0
        downstream_weight = 1.5 
        complexity_weight = 2.0
        
        score = (
            upstream_count * upstream_weight + 
            downstream_count * downstream_weight +
            complexity * complexity_weight
        )
        
        # Normalize to 0-100 scale
        return min(score / 2.0, 100.0)

    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level"""
        if risk_score >= 50:
            return "CRITICAL"
        elif risk_score >= 25:
            return "HIGH" 
        elif risk_score >= 10:
            return "MEDIUM"
        else:
            return "LOW"

    def _generate_impact_summary(self, upstream: Set[str], downstream: Set[str], func_info) -> str:
        """Generate human-readable impact summary"""
        upstream_files = len(set(key.split("::")[0] for key in upstream))
        downstream_files = len(set(key.split("::")[0] for key in downstream))
        
        summary_parts = []
        
        if upstream:
            summary_parts.append(f"Called by {len(upstream)} functions across {upstream_files} files")
        else:
            summary_parts.append("No upstream callers detected")
            
        if downstream:
            summary_parts.append(f"calls {len(downstream)} functions across {downstream_files} files")
        else:
            summary_parts.append("makes no downstream calls")
            
        if func_info.complexity > 10:
            summary_parts.append(f"has high complexity ({func_info.complexity})")
            
        return "; ".join(summary_parts)

    def find_critical_path_functions(self, threshold: int = 5) -> List[Dict[str, Any]]:
        """
        Find functions that are on critical paths (high upstream + downstream impact)
        
        Args:
            threshold: Minimum combined upstream+downstream count to be considered critical
            
        Returns:
            List of critical path function analyses, sorted by impact
        """
        critical_functions = []
        
        for func_key, func_info in self.all_functions.items():
            # Skip private functions for this analysis
            if func_info.name.startswith('_'):
                continue
                
            upstream = self.get_transitive_callers(func_key, max_depth=8)
            downstream = self.get_transitive_callees(func_key, max_depth=8)
            
            total_impact = len(upstream) + len(downstream)
            
            if total_impact >= threshold:
                impact_chain = self.get_function_impact_chain(func_key)
                critical_functions.append(impact_chain)
                
        # Sort by risk score descending
        return sorted(critical_functions, key=lambda x: x['risk_score'], reverse=True)

    def analyze_function_dependencies(self, func_key: str) -> Dict[str, Any]:
        """
        Comprehensive dependency analysis for a specific function
        
        Args:
            func_key: Function key in format "file_path::function_name"
            
        Returns:
            Detailed dependency analysis
        """
        if not self.is_analyzed or func_key not in self.all_functions:
            return {"error": "Function not found or codebase not analyzed"}
            
        func_info = self.all_functions[func_key]
        
        # Get immediate dependencies
        direct_calls = list(self.function_call_graph.get(func_key, set()))
        direct_callers = func_info.called_by.copy()
        
        # Get transitive dependencies  
        all_callees = self.get_transitive_callees(func_key)
        all_callers = self.get_transitive_callers(func_key)
        
        # Analyze dependency patterns
        external_deps = []
        internal_deps = []
        
        for callee_key in direct_calls:
            if callee_key in self.all_functions:
                callee_info = self.all_functions[callee_key]
                callee_file = callee_key.split("::")[0]
                
                if callee_file == func_info.file_path:
                    internal_deps.append({
                        "name": callee_info.name,
                        "line": callee_info.line_number,
                        "type": "internal_function"
                    })
                else:
                    external_deps.append({
                        "name": callee_info.name,
                        "file": callee_file,
                        "line": callee_info.line_number,
                        "type": "cross_file_function"
                    })
                    
        return {
            "function_name": func_info.name,
            "file_path": func_info.file_path,
            "analysis": {
                "direct_calls": len(direct_calls),
                "direct_callers": len(direct_callers), 
                "transitive_callees": len(all_callees),
                "transitive_callers": len(all_callers),
                "internal_dependencies": len(internal_deps),
                "external_dependencies": len(external_deps),
                "dependency_files": len(set(dep["file"] for dep in external_deps)),
                "is_leaf_function": len(direct_calls) == 0,
                "is_entry_point": len(direct_callers) == 0,
                "coupling_score": len(external_deps) / max(len(internal_deps), 1)
            },
            "dependencies": {
                "internal": internal_deps,
                "external": external_deps
            },
            "recommendations": self._generate_dependency_recommendations(
                len(external_deps), len(internal_deps), func_info.complexity
            )
        }

    def _generate_dependency_recommendations(self, external_deps: int, internal_deps: int, complexity: int) -> List[str]:
        """Generate recommendations based on dependency analysis"""
        recommendations = []
        
        if external_deps > 5:
            recommendations.append(f"High external coupling ({external_deps} dependencies) - consider dependency injection")
            
        if complexity > 10 and external_deps > 3:
            recommendations.append("High complexity with many dependencies - consider breaking into smaller functions")
            
        if external_deps == 0 and internal_deps == 0:
            recommendations.append("Pure function with no dependencies - excellent for testing and reuse")
            
        if external_deps > internal_deps * 2:
            recommendations.append("More external than internal dependencies - consider if this function belongs in a different module")
            
        return recommendations