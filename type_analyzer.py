"""
Type Analyzer - Signature Validation and Type Checking
Validates function signatures across files and detects type issues
Lightweight analysis + optional mypy integration
"""

import ast
import subprocess
import json
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
from collections import defaultdict


@dataclass
class TypeIssue:
    """Type-related issue found in code"""
    rule_id: str
    severity: str  # 'critical', 'warning', 'suggestion'
    line: int
    column: int
    message: str
    suggestion: str
    evidence: Dict[str, Any]


@dataclass
class FunctionSignature:
    """Function signature information for validation"""
    name: str
    file_path: str
    line: int
    parameters: List[Tuple[str, Optional[str]]]  # (name, type_hint)
    return_type: Optional[str]
    is_method: bool = False
    class_name: Optional[str] = None


class TypeAnalyzer:
    """
    Analyzes type usage and validates function signatures
    """

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.function_signatures: Dict[str, FunctionSignature] = {}
        self.function_calls: Dict[str, List[Dict]] = defaultdict(list)  # file -> calls
        
    def analyze_types(self, all_functions: Dict[str, Any], all_files: Dict[str, Any], target_file: str = None) -> List[TypeIssue]:
        """
        Main entry point - analyze all type-related issues
        
        Args:
            all_functions: Function info from codebase analyzer
            all_files: File info from codebase analyzer
            target_file: Specific file to analyze (if None, analyze all files)
            
        Returns:
            List of type issues
        """
        issues = []
        
        # Build signature database
        self._build_signature_database(all_functions)
        
        # Extract function calls from files
        self._extract_function_calls(all_files)
        
        # Run signature validation (filtered to target file if specified)
        issues.extend(self._validate_signatures(target_file))
        
        # Check for missing type hints (filtered to target file if specified)
        issues.extend(self._check_missing_type_hints(all_functions, target_file))
        
        # Check for type annotation consistency
        issues.extend(self._check_type_consistency())
        
        return sorted(issues, key=lambda x: (x.line, x.column))
        
    def _build_signature_database(self, all_functions: Dict[str, Any]):
        """Build database of all function signatures"""
        for func_key, func_info in all_functions.items():
            file_path, func_name = func_key.split("::", 1)
            
            # Handle class methods
            is_method = '.' in func_name
            class_name = None
            if is_method:
                class_name, method_name = func_name.split('.', 1)
                display_name = method_name
            else:
                display_name = func_name
                
            signature = FunctionSignature(
                name=display_name,
                file_path=file_path,
                line=func_info.line_number,
                parameters=func_info.parameters,
                return_type=func_info.return_type,
                is_method=is_method,
                class_name=class_name
            )
            
            self.function_signatures[func_key] = signature
            
    def _extract_function_calls(self, all_files: Dict[str, Any]):
        """Extract function calls from all files"""
        for file_path, file_info in all_files.items():
            file_path_obj = self.project_root / file_path
            
            try:
                with open(file_path_obj, 'r', encoding='utf-8') as f:
                    source = f.read()
                tree = ast.parse(source)
                
                visitor = CallExtractionVisitor(file_path, file_info)
                visitor.visit(tree)
                self.function_calls[file_path] = visitor.calls
                
            except Exception as e:
                print(f"⚠️ Could not extract calls from {file_path}: {e}")
                continue
                
    def _validate_signatures(self, target_file: str = None) -> List[TypeIssue]:
        """Validate function call signatures against definitions"""
        issues = []
        
        # Filter to target file if specified
        files_to_check = {}
        if target_file:
            # Normalize the target file path
            target_file = str(Path(target_file).as_posix())
            files_to_check = {target_file: self.function_calls.get(target_file, [])}
        else:
            files_to_check = self.function_calls
        
        for file_path, calls in files_to_check.items():
            for call_info in calls:
                func_name = call_info['function_name']
                call_line = call_info['line']
                call_column = call_info['column']
                args_passed = call_info['args_count']
                kwargs_passed = call_info['kwargs']
                
                # Find the function definition
                matching_signatures = self._find_matching_signatures(func_name, file_path)
                
                if not matching_signatures:
                    continue  # External function or not found
                    
                for sig_key, signature in matching_signatures:
                    # Validate argument count
                    required_args = len([p for p in signature.parameters if p[0] not in ['self', 'cls']])
                    
                    if signature.is_method and 'self' in [p[0] for p in signature.parameters]:
                        required_args -= 1  # Don't count self
                        
                    if args_passed < required_args:
                        issues.append(TypeIssue(
                            rule_id='signature_mismatch',
                            severity='critical',
                            line=call_line,
                            column=call_column,
                            message=f'Function "{func_name}" expects {required_args} arguments but {args_passed} were provided',
                            suggestion=f'Check function definition at {signature.file_path}:{signature.line} and provide all required arguments',
                            evidence={
                                'function_name': func_name,
                                'expected_args': required_args,
                                'provided_args': args_passed,
                                'definition_file': signature.file_path,
                                'definition_line': signature.line,
                                'parameters': [p[0] for p in signature.parameters],
                                'detection_method': 'signature_validation'
                            }
                        ))
                        
                    # Check for type hint mismatches (basic)
                    issues.extend(self._check_argument_types(call_info, signature))
                    
        return issues
        
    def _find_matching_signatures(self, func_name: str, calling_file: str) -> List[Tuple[str, FunctionSignature]]:
        """Find function signatures that match the called function name"""
        matches = []
        
        for sig_key, signature in self.function_signatures.items():
            # Exact name match
            if signature.name == func_name:
                matches.append((sig_key, signature))
            # Method call match (obj.method)
            elif '.' in func_name and signature.name == func_name.split('.')[-1]:
                matches.append((sig_key, signature))
                
        return matches
        
    def _check_argument_types(self, call_info: Dict, signature: FunctionSignature) -> List[TypeIssue]:
        """Basic type checking for function arguments"""
        issues = []
        
        # This is a simplified type checker - only catches obvious mismatches
        for i, (param_name, param_type) in enumerate(signature.parameters):
            if param_type and i < len(call_info.get('arg_types', [])):
                provided_type = call_info['arg_types'][i]
                
                # Simple type mismatch detection
                if self._are_types_incompatible(param_type, provided_type):
                    issues.append(TypeIssue(
                        rule_id='type_mismatch',
                        severity='warning',
                        line=call_info['line'],
                        column=call_info['column'],
                        message=f'Type mismatch in "{signature.name}": parameter "{param_name}" expects {param_type} but got {provided_type}',
                        suggestion=f'Check the type of argument {i+1} - it should be {param_type}',
                        evidence={
                            'function_name': signature.name,
                            'parameter_name': param_name,
                            'expected_type': param_type,
                            'provided_type': provided_type,
                            'argument_position': i + 1,
                            'detection_method': 'basic_type_checking'
                        }
                    ))
                    
        return issues
        
    def _are_types_incompatible(self, expected: str, provided: str) -> bool:
        """Check if two types are obviously incompatible"""
        # Normalize type names
        type_map = {
            'str': 'string',
            'int': 'integer', 
            'float': 'number',
            'list': 'list',
            'dict': 'dictionary',
            'bool': 'boolean'
        }
        
        expected = type_map.get(expected.lower(), expected.lower())
        provided = type_map.get(provided.lower(), provided.lower())
        
        # Basic incompatibility checks
        incompatible_pairs = [
            ('string', 'integer'),
            ('string', 'number'),
            ('integer', 'string'),
            ('list', 'dictionary'),
            ('dictionary', 'list'),
            ('boolean', 'integer')
        ]
        
        return (expected, provided) in incompatible_pairs or (provided, expected) in incompatible_pairs
        
    def _check_missing_type_hints(self, all_functions: Dict[str, Any], target_file: str = None) -> List[TypeIssue]:
        """Check for missing type hints on public functions"""
        issues = []
        
        for func_key, func_info in all_functions.items():
            # Filter to target file if specified
            if target_file:
                func_file_path = func_key.split("::")[0]
                target_file_normalized = str(Path(target_file).as_posix())
                if func_file_path != target_file_normalized:
                    continue
            
            # Skip private functions
            if func_info.name.startswith('_') and func_info.name not in ['__init__', '__str__', '__repr__']:
                continue
                
            missing_hints = []
            
            # Check parameter type hints
            for param_name, param_type in func_info.parameters:
                if param_type is None and param_name not in ['self', 'cls']:
                    missing_hints.append(f"parameter '{param_name}'")
                    
            # Check return type hint
            if func_info.return_type is None and func_info.name != '__init__':
                missing_hints.append("return type")
                
            if missing_hints:
                issues.append(TypeIssue(
                    rule_id='missing_type_hints',
                    severity='suggestion',
                    line=func_info.line_number,
                    column=0,
                    message=f'Function "{func_info.name}" is missing type hints for: {", ".join(missing_hints)}',
                    suggestion='Add type hints to improve code clarity and enable static type checking',
                    evidence={
                        'function_name': func_info.name,
                        'missing_hints': missing_hints,
                        'total_parameters': len(func_info.parameters),
                        'is_public': not func_info.name.startswith('_'),
                        'detection_method': 'type_hint_analysis'
                    }
                ))
                
        return issues
        
    def _check_type_consistency(self) -> List[TypeIssue]:
        """Check for type annotation consistency issues"""
        issues = []
        
        # Check for functions with same name but different signatures
        func_groups = defaultdict(list)
        
        for sig_key, signature in self.function_signatures.items():
            if not signature.is_method:  # Only check regular functions
                func_groups[signature.name].append((sig_key, signature))
                
        for func_name, signatures in func_groups.items():
            if len(signatures) > 1:
                # Check if signatures are consistent
                first_sig = signatures[0][1]
                
                for sig_key, signature in signatures[1:]:
                    if len(first_sig.parameters) != len(signature.parameters):
                        issues.append(TypeIssue(
                            rule_id='inconsistent_signatures',
                            severity='warning',
                            line=signature.line,
                            column=0,
                            message=f'Function "{func_name}" has inconsistent signatures across files',
                            suggestion=f'Check all definitions of "{func_name}" and ensure consistent parameter counts',
                            evidence={
                                'function_name': func_name,
                                'signature_1': f"{first_sig.file_path}:{first_sig.line}",
                                'signature_2': f"{signature.file_path}:{signature.line}",
                                'param_count_1': len(first_sig.parameters),
                                'param_count_2': len(signature.parameters),
                                'detection_method': 'signature_consistency_check'
                            }
                        ))
                        
        return issues
        
    def run_mypy_analysis(self, project_root: str) -> List[TypeIssue]:
        """
        Run mypy for deeper type analysis (optional)
        Requires mypy to be installed
        """
        issues = []
        
        try:
            # Run mypy with JSON output
            result = subprocess.run([
                'mypy', 
                str(project_root),
                '--show-error-codes',
                '--no-error-summary',
                '--output-format=json'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                return []  # No mypy errors
                
            # Parse mypy JSON output
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                try:
                    error_data = json.loads(line)
                    
                    issues.append(TypeIssue(
                        rule_id='mypy_error',
                        severity='warning',
                        line=error_data.get('line', 1),
                        column=error_data.get('column', 0),
                        message=f"MyPy: {error_data.get('message', 'Type error')}",
                        suggestion='Fix the type error according to mypy recommendations',
                        evidence={
                            'mypy_error_code': error_data.get('code'),
                            'file_path': error_data.get('file'),
                            'severity': error_data.get('severity', 'error'),
                            'detection_method': 'mypy_static_analysis'
                        }
                    ))
                    
                except json.JSONDecodeError:
                    continue
                    
        except subprocess.TimeoutExpired:
            issues.append(TypeIssue(
                rule_id='mypy_timeout',
                severity='warning',
                line=1,
                column=0,
                message='MyPy analysis timed out',
                suggestion='Consider running mypy manually on smaller subsets of code',
                evidence={'timeout': 60, 'detection_method': 'mypy_timeout'}
            ))
        except FileNotFoundError:
            # mypy not installed - skip
            pass
        except Exception as e:
            issues.append(TypeIssue(
                rule_id='mypy_error',
                severity='warning',
                line=1,
                column=0,
                message=f'MyPy analysis failed: {str(e)}',
                suggestion='Check mypy installation and configuration',
                evidence={'error': str(e), 'detection_method': 'mypy_error'}
            ))
            
        return issues


class CallExtractionVisitor(ast.NodeVisitor):
    """Extracts function calls from AST"""
    
    def __init__(self, file_path: str, file_info: Dict):
        self.file_path = file_path
        self.file_info = file_info
        self.calls = []
        
    def visit_Call(self, node):
        call_info = {
            'line': node.lineno,
            'column': node.col_offset,
            'args_count': len(node.args),
            'kwargs': [kw.arg for kw in node.keywords],
            'arg_types': []
        }
        
        # Get function name
        if isinstance(node.func, ast.Name):
            call_info['function_name'] = node.func.id
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                call_info['function_name'] = f"{node.func.value.id}.{node.func.attr}"
            else:
                call_info['function_name'] = node.func.attr
        else:
            call_info['function_name'] = 'unknown'
            
        # Try to infer argument types (basic)
        for arg in node.args:
            arg_type = self._infer_arg_type(arg)
            call_info['arg_types'].append(arg_type)
            
        self.calls.append(call_info)
        self.generic_visit(node)
        
    def _infer_arg_type(self, node) -> str:
        """Basic argument type inference"""
        if isinstance(node, ast.Constant):
            return type(node.value).__name__
        elif isinstance(node, ast.List):
            return 'list'
        elif isinstance(node, ast.Dict):
            return 'dict'
        elif isinstance(node, ast.Set):
            return 'set'
        elif isinstance(node, ast.Tuple):
            return 'tuple'
        elif isinstance(node, ast.Name):
            return 'variable'
        elif isinstance(node, ast.Call):
            return 'function_result'
        else:
            return 'unknown'


def analyze_file_types(file_path: str, all_functions: Dict = None, all_files: Dict = None) -> List[TypeIssue]:
    """
    Convenience function to analyze a single file for type issues
    """
    analyzer = TypeAnalyzer(Path(file_path).parent)
    
    if all_functions and all_files:
        return analyzer.analyze_types(all_functions, all_files)
    else:
        # Minimal analysis of just this file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source)
            
            # Basic type hint checking
            issues = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    missing_hints = []
                    
                    for arg in node.args.args:
                        if not arg.annotation and arg.arg not in ['self', 'cls']:
                            missing_hints.append(f"parameter '{arg.arg}'")
                            
                    if not node.returns and node.name != '__init__':
                        missing_hints.append("return type")
                        
                    if missing_hints and not node.name.startswith('_'):
                        issues.append(TypeIssue(
                            rule_id='missing_type_hints',
                            severity='suggestion',
                            line=node.lineno,
                            column=node.col_offset,
                            message=f'Function "{node.name}" is missing type hints for: {", ".join(missing_hints)}',
                            suggestion='Add type hints to improve code clarity',
                            evidence={'missing_hints': missing_hints}
                        ))
                        
            return issues
            
        except Exception as e:
            return [TypeIssue(
                rule_id='analysis_error',
                severity='warning',
                line=1,
                column=0,
                message=f'Could not analyze types: {e}',
                suggestion='Check file syntax and encoding',
                evidence={'error': str(e)}
            )]


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        file_to_analyze = sys.argv[1]
        print(f"Analyzing {file_to_analyze} for type issues...")
        
        issues = analyze_file_types(file_to_analyze)
        
        if not issues:
            print("✅ No type issues detected!")
        else:
            print(f"🔍 Found {len(issues)} type issues:")
            for issue in issues:
                print(f"\n{issue.severity.upper()} - Line {issue.line}")
                print(f"Rule: {issue.rule_id}")
                print(f"Issue: {issue.message}")
                print(f"Fix: {issue.suggestion}")
    else:
        print("Usage: python type_analyzer.py <file_to_analyze>")