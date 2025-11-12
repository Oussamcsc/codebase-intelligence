"""
Pattern Matcher - AST-Based Antipattern Detection
Detects bad code patterns automatically using AST traversal
NO GUESSING - actual static analysis with concrete evidence
"""

import ast
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PatternIssue:
    """Issue detected by pattern matching"""
    rule_id: str
    severity: str  # 'critical', 'warning', 'suggestion'
    line: int
    column: int
    message: str
    suggestion: str
    evidence: Dict[str, Any]


class PatternMatcher:
    """
    AST-based pattern matcher for code antipatterns
    Each rule is a concrete detector with evidence
    """

    def __init__(self):
        self.rules = {
            'nested_loops': self._detect_nested_loops,
            'bare_except': self._detect_bare_except,
            'global_assignments': self._detect_global_assignments,
            'long_functions': self._detect_long_functions,
            'dangerous_eval': self._detect_dangerous_eval,
            'mutable_defaults': self._detect_mutable_defaults,
            'magic_numbers': self._detect_magic_numbers,
            'deep_nesting': self._detect_deep_nesting,
            'unused_variables': self._detect_unused_variables,
            'string_exceptions': self._detect_string_exceptions
        }

    def find_antipatterns(self, ast_tree: ast.AST, file_path: str, source_code: str) -> List[PatternIssue]:
        """
        Find all antipatterns in the AST tree
        
        Args:
            ast_tree: Parsed AST
            file_path: Path to the file being analyzed
            source_code: Original source code for context
            
        Returns:
            List of pattern issues with evidence
        """
        issues = []
        
        # Run all pattern detection rules
        for rule_name, rule_func in self.rules.items():
            try:
                rule_issues = rule_func(ast_tree, file_path, source_code)
                issues.extend(rule_issues)
            except Exception as e:
                # Don't let one rule failure break everything
                print(f"⚠️ Rule {rule_name} failed: {e}")
                continue
        
        return sorted(issues, key=lambda x: (x.line, x.column))

    def _detect_nested_loops(self, tree: ast.AST, file_path: str, source_code: str) -> List[PatternIssue]:
        """Detect nested loops > 3 levels"""
        issues = []
        
        class LoopNestingVisitor(ast.NodeVisitor):
            def __init__(self):
                self.loop_stack = []
                
            def visit_loop(self, node):
                self.loop_stack.append(node)
                
                if len(self.loop_stack) > 3:
                    loop_types = [type(n).__name__ for n in self.loop_stack]
                    issues.append(PatternIssue(
                        rule_id='nested_loops',
                        severity='warning',
                        line=node.lineno,
                        column=node.col_offset,
                        message=f'Deeply nested loops detected: {len(self.loop_stack)} levels',
                        suggestion='Consider extracting inner loops into separate functions or using list comprehensions',
                        evidence={
                            'nesting_level': len(self.loop_stack),
                            'loop_types': loop_types,
                            'threshold': 3,
                            'detection_method': 'AST_stack_tracking'
                        }
                    ))
                
                self.generic_visit(node)
                self.loop_stack.pop()
                
            def visit_For(self, node):
                self.visit_loop(node)
                
            def visit_While(self, node):
                self.visit_loop(node)
        
        visitor = LoopNestingVisitor()
        visitor.visit(tree)
        return issues

    def _detect_bare_except(self, tree: ast.AST, file_path: str, source_code: str) -> List[PatternIssue]:
        """Detect bare except clauses"""
        issues = []
        
        class BareExceptVisitor(ast.NodeVisitor):
            def visit_ExceptHandler(self, node):
                # Bare except: no exception type specified
                if node.type is None:
                    # Check if it's the dangerous "except: pass" pattern
                    is_pass_only = (len(node.body) == 1 and 
                                   isinstance(node.body[0], ast.Pass))
                    
                    severity = 'critical' if is_pass_only else 'warning'
                    message = 'Bare except clause' + (' with pass - silences all errors!' if is_pass_only else '')
                    
                    issues.append(PatternIssue(
                        rule_id='bare_except',
                        severity=severity,
                        line=node.lineno,
                        column=node.col_offset,
                        message=message,
                        suggestion='Specify exception types (e.g., except ValueError:) or use "except Exception:" if you must catch all',
                        evidence={
                            'is_pass_only': is_pass_only,
                            'body_statements': len(node.body),
                            'catches_system_exit': True,
                            'catches_keyboard_interrupt': True,
                            'detection_method': 'AST_except_handler_analysis'
                        }
                    ))
                
                self.generic_visit(node)
        
        visitor = BareExceptVisitor()
        visitor.visit(tree)
        return issues

    def _detect_global_assignments(self, tree: ast.AST, file_path: str, source_code: str) -> List[PatternIssue]:
        """Detect global variable assignments"""
        issues = []
        
        class GlobalAssignmentVisitor(ast.NodeVisitor):
            def __init__(self):
                self.in_function = False
                self.function_stack = []
                
            def visit_FunctionDef(self, node):
                self.in_function = True
                self.function_stack.append(node.name)
                self.generic_visit(node)
                self.function_stack.pop()
                self.in_function = len(self.function_stack) > 0
                
            def visit_Global(self, node):
                if self.in_function:
                    current_func = self.function_stack[-1] if self.function_stack else 'unknown'
                    issues.append(PatternIssue(
                        rule_id='global_assignments',
                        severity='warning',
                        line=node.lineno,
                        column=node.col_offset,
                        message=f'Global statement found in function "{current_func}": {", ".join(node.names)}',
                        suggestion='Consider passing values as parameters and returning results instead of using global variables',
                        evidence={
                            'global_variables': node.names,
                            'function_name': current_func,
                            'makes_testing_difficult': True,
                            'detection_method': 'AST_global_statement_analysis'
                        }
                    ))
                
                self.generic_visit(node)
        
        visitor = GlobalAssignmentVisitor()
        visitor.visit(tree)
        return issues

    def _detect_long_functions(self, tree: ast.AST, file_path: str, source_code: str) -> List[PatternIssue]:
        """Detect functions longer than 50 lines"""
        issues = []
        
        class LongFunctionVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                # Calculate function length
                if hasattr(node, 'end_lineno') and node.end_lineno:
                    func_length = node.end_lineno - node.lineno + 1
                else:
                    # Fallback: estimate from body
                    func_length = max((getattr(stmt, 'lineno', 0) for stmt in node.body), default=node.lineno) - node.lineno + 1
                
                if func_length > 50:
                    issues.append(PatternIssue(
                        rule_id='long_functions',
                        severity='warning',
                        line=node.lineno,
                        column=node.col_offset,
                        message=f'Function "{node.name}" is {func_length} lines long',
                        suggestion='Consider breaking this function into smaller, more focused functions',
                        evidence={
                            'function_name': node.name,
                            'line_count': func_length,
                            'threshold': 50,
                            'statement_count': len(node.body),
                            'detection_method': 'AST_line_counting'
                        }
                    ))
                
                self.generic_visit(node)
        
        visitor = LongFunctionVisitor()
        visitor.visit(tree)
        return issues

    def _detect_dangerous_eval(self, tree: ast.AST, file_path: str, source_code: str) -> List[PatternIssue]:
        """Detect eval() and exec() usage"""
        issues = []
        
        class DangerousEvalVisitor(ast.NodeVisitor):
            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ['eval', 'exec']:
                        # Check if it's using user input (very dangerous)
                        has_user_input = self._check_for_user_input(node)
                        
                        severity = 'critical' if has_user_input else 'warning'
                        
                        issues.append(PatternIssue(
                            rule_id='dangerous_eval',
                            severity=severity,
                            line=node.lineno,
                            column=node.col_offset,
                            message=f'Use of {node.func.id}() detected' + (' with potential user input!' if has_user_input else ''),
                            suggestion=f'Avoid {node.func.id}(). Use safer alternatives like ast.literal_eval() for data or proper parsing',
                            evidence={
                                'function_name': node.func.id,
                                'potential_user_input': has_user_input,
                                'security_risk': 'code_injection',
                                'detection_method': 'AST_call_analysis'
                            }
                        ))
                
                self.generic_visit(node)
                
            def _check_for_user_input(self, node):
                """Check if eval/exec might be using user input"""
                # Simple heuristic: look for input(), request data, etc.
                for arg in ast.walk(node):
                    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
                        if arg.func.id in ['input', 'raw_input']:
                            return True
                    elif isinstance(arg, ast.Attribute):
                        if arg.attr in ['form', 'args', 'json', 'data']:  # Flask/Django request data
                            return True
                return False
        
        visitor = DangerousEvalVisitor()
        visitor.visit(tree)
        return issues

    def _detect_mutable_defaults(self, tree: ast.AST, file_path: str, source_code: str) -> List[PatternIssue]:
        """Detect mutable default arguments"""
        issues = []
        
        class MutableDefaultVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                for i, default in enumerate(node.args.defaults):
                    if self._is_mutable(default):
                        # Find the parameter name
                        param_index = len(node.args.args) - len(node.args.defaults) + i
                        param_name = node.args.args[param_index].arg if param_index < len(node.args.args) else 'unknown'
                        
                        issues.append(PatternIssue(
                            rule_id='mutable_defaults',
                            severity='warning',
                            line=default.lineno,
                            column=default.col_offset,
                            message=f'Mutable default argument detected in function "{node.name}": parameter "{param_name}"',
                            suggestion=f'Use None as default and initialize inside function: def {node.name}(..., {param_name}=None): if {param_name} is None: {param_name} = []',
                            evidence={
                                'function_name': node.name,
                                'parameter_name': param_name,
                                'default_type': type(default).__name__,
                                'shared_between_calls': True,
                                'detection_method': 'AST_default_argument_analysis'
                            }
                        ))
                
                self.generic_visit(node)
                
            def _is_mutable(self, node):
                """Check if a node represents a mutable object"""
                return isinstance(node, (ast.List, ast.Dict, ast.Set))
        
        visitor = MutableDefaultVisitor()
        visitor.visit(tree)
        return issues

    def _detect_magic_numbers(self, tree: ast.AST, file_path: str, source_code: str) -> List[PatternIssue]:
        """Detect magic numbers (excluding common ones like 0, 1, 2)"""
        issues = []
        
        # Numbers that are commonly okay to use directly
        ALLOWED_NUMBERS = {0, 1, 2, -1, 10, 100}
        
        class MagicNumberVisitor(ast.NodeVisitor):
            def __init__(self):
                self.in_constant_assignment = False
                
            def visit_Assign(self, node):
                # Don't flag numbers being assigned to constants
                if (len(node.targets) == 1 and 
                    isinstance(node.targets[0], ast.Name) and
                    node.targets[0].id.isupper()):
                    self.in_constant_assignment = True
                    self.generic_visit(node)
                    self.in_constant_assignment = False
                else:
                    self.generic_visit(node)
                    
            def visit_Constant(self, node):
                if (isinstance(node.value, (int, float)) and 
                    node.value not in ALLOWED_NUMBERS and
                    not self.in_constant_assignment):
                    
                    issues.append(PatternIssue(
                        rule_id='magic_numbers',
                        severity='suggestion',
                        line=node.lineno,
                        column=node.col_offset,
                        message=f'Magic number detected: {node.value}',
                        suggestion=f'Consider defining a named constant: MEANINGFUL_NAME = {node.value}',
                        evidence={
                            'magic_number': node.value,
                            'number_type': type(node.value).__name__,
                            'makes_code_unclear': True,
                            'detection_method': 'AST_constant_analysis'
                        }
                    ))
                
                self.generic_visit(node)
        
        visitor = MagicNumberVisitor()
        visitor.visit(tree)
        return issues

    def _detect_deep_nesting(self, tree: ast.AST, file_path: str, source_code: str) -> List[PatternIssue]:
        """Detect deeply nested code blocks (> 4 levels)"""
        issues = []
        
        class NestingVisitor(ast.NodeVisitor):
            def __init__(self):
                self.nesting_level = 0
                self.nesting_stack = []
                
            def _visit_nested_block(self, node, block_type):
                self.nesting_level += 1
                self.nesting_stack.append(block_type)
                
                if self.nesting_level > 4:
                    issues.append(PatternIssue(
                        rule_id='deep_nesting',
                        severity='warning',
                        line=node.lineno,
                        column=node.col_offset,
                        message=f'Deep nesting detected: {self.nesting_level} levels ({" → ".join(self.nesting_stack)})',
                        suggestion='Consider extracting nested logic into separate functions or using early returns',
                        evidence={
                            'nesting_level': self.nesting_level,
                            'nesting_path': self.nesting_stack.copy(),
                            'threshold': 4,
                            'detection_method': 'AST_nesting_analysis'
                        }
                    ))
                
                self.generic_visit(node)
                self.nesting_level -= 1
                self.nesting_stack.pop()
                
            def visit_If(self, node):
                self._visit_nested_block(node, 'if')
                
            def visit_For(self, node):
                self._visit_nested_block(node, 'for')
                
            def visit_While(self, node):
                self._visit_nested_block(node, 'while')
                
            def visit_With(self, node):
                self._visit_nested_block(node, 'with')
                
            def visit_Try(self, node):
                self._visit_nested_block(node, 'try')
        
        visitor = NestingVisitor()
        visitor.visit(tree)
        return issues

    def _detect_unused_variables(self, tree: ast.AST, file_path: str, source_code: str) -> List[PatternIssue]:
        """Detect variables that are assigned but never used"""
        issues = []
        
        class UnusedVariableVisitor(ast.NodeVisitor):
            def __init__(self):
                self.assigned_vars = {}  # name -> line
                self.used_vars = set()
                
            def visit_FunctionDef(self, node):
                # Create new scope for function
                old_assigned = self.assigned_vars.copy()
                old_used = self.used_vars.copy()
                
                # Parameters are considered used
                for arg in node.args.args:
                    self.used_vars.add(arg.arg)
                
                self.generic_visit(node)
                
                # Check for unused variables in this scope
                for var_name, line_no in self.assigned_vars.items():
                    if (var_name not in self.used_vars and 
                        not var_name.startswith('_') and  # Skip private vars
                        var_name not in ['self', 'cls']):
                        
                        issues.append(PatternIssue(
                            rule_id='unused_variables',
                            severity='suggestion',
                            line=line_no,
                            column=0,
                            message=f'Variable "{var_name}" is assigned but never used',
                            suggestion=f'Remove unused variable "{var_name}" or prefix with underscore if intentionally unused',
                            evidence={
                                'variable_name': var_name,
                                'assigned_line': line_no,
                                'function_name': node.name,
                                'detection_method': 'AST_variable_tracking'
                            }
                        ))
                
                # Restore parent scope
                self.assigned_vars = old_assigned
                self.used_vars = old_used
                
            def visit_Assign(self, node):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.assigned_vars[target.id] = node.lineno
                self.generic_visit(node)
                
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Load):
                    self.used_vars.add(node.id)
                self.generic_visit(node)
        
        visitor = UnusedVariableVisitor()
        visitor.visit(tree)
        return issues

    def _detect_string_exceptions(self, tree: ast.AST, file_path: str, source_code: str) -> List[PatternIssue]:
        """Detect raising string exceptions (Python 2 style)"""
        issues = []
        
        class StringExceptionVisitor(ast.NodeVisitor):
            def visit_Raise(self, node):
                if (node.exc and 
                    isinstance(node.exc, ast.Constant) and 
                    isinstance(node.exc.value, str)):
                    
                    issues.append(PatternIssue(
                        rule_id='string_exceptions',
                        severity='critical',
                        line=node.lineno,
                        column=node.col_offset,
                        message=f'String exception detected: "{node.exc.value}"',
                        suggestion='Use proper exception classes: raise ValueError("message") instead of raise "message"',
                        evidence={
                            'exception_string': node.exc.value,
                            'deprecated_in_python3': True,
                            'detection_method': 'AST_raise_analysis'
                        }
                    ))
                
                self.generic_visit(node)
        
        visitor = StringExceptionVisitor()
        visitor.visit(tree)
        return issues

    def get_rule_descriptions(self) -> Dict[str, str]:
        """Get descriptions of all available rules"""
        return {
            'nested_loops': 'Detects deeply nested loops (>3 levels) that hurt readability',
            'bare_except': 'Detects bare except clauses that catch all exceptions including system exits',
            'global_assignments': 'Detects global variable usage in functions',
            'long_functions': 'Detects functions longer than 50 lines',
            'dangerous_eval': 'Detects use of eval() and exec() which can be security risks',
            'mutable_defaults': 'Detects mutable default arguments (lists, dicts) that are shared between calls',
            'magic_numbers': 'Detects magic numbers that should be named constants',
            'deep_nesting': 'Detects deeply nested code blocks (>4 levels)',
            'unused_variables': 'Detects variables that are assigned but never used',
            'string_exceptions': 'Detects string exceptions (deprecated Python 2 style)'
        }


def analyze_file_patterns(file_path: str) -> List[PatternIssue]:
    """
    Convenience function to analyze a single file for antipatterns
    
    Args:
        file_path: Path to Python file to analyze
        
    Returns:
        List of pattern issues found
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        tree = ast.parse(source_code)
        matcher = PatternMatcher()
        return matcher.find_antipatterns(tree, file_path, source_code)
        
    except SyntaxError as e:
        return [PatternIssue(
            rule_id='syntax_error',
            severity='critical',
            line=e.lineno or 1,
            column=e.offset or 0,
            message=f'Syntax error: {e.msg}',
            suggestion='Fix syntax error before analysis can proceed',
            evidence={'syntax_error': str(e)}
        )]
    except Exception as e:
        return [PatternIssue(
            rule_id='analysis_error',
            severity='warning',
            line=1,
            column=0,
            message=f'Could not analyze file: {e}',
            suggestion='Check file encoding and permissions',
            evidence={'error': str(e)}
        )]


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        file_to_analyze = sys.argv[1]
        print(f"Analyzing {file_to_analyze} for antipatterns...")
        
        issues = analyze_file_patterns(file_to_analyze)
        
        if not issues:
            print("✅ No antipatterns detected!")
        else:
            print(f"🔍 Found {len(issues)} potential issues:")
            for issue in issues:
                print(f"\n{issue.severity.upper()} - Line {issue.line}")
                print(f"Rule: {issue.rule_id}")
                print(f"Issue: {issue.message}")
                print(f"Fix: {issue.suggestion}")
                if issue.evidence:
                    print(f"Evidence: {issue.evidence}")
    else:
        print("Usage: python pattern_matcher.py <file_to_analyze>")