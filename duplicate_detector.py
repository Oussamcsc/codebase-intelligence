"""
Duplicate Detector - Find Exact and Semantic Code Duplicates
Detects both exact duplicate functions and similar code patterns
Uses AST normalization + hashing for exact matches, vectorization for similarity
"""

import ast
import hashlib
import difflib
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict
import re


@dataclass
class DuplicateIssue:
    """Duplicate code issue"""
    rule_id: str
    severity: str  # 'critical', 'warning', 'suggestion'
    line: int
    column: int
    message: str
    suggestion: str
    evidence: Dict[str, Any]


@dataclass
class CodeBlock:
    """Represents a code block for duplicate detection"""
    content: str
    normalized_content: str
    file_path: str
    function_name: str
    start_line: int
    end_line: int
    ast_hash: str
    token_hash: str


class ASTNormalizer(ast.NodeTransformer):
    """
    Normalizes AST by removing variable names, comments, and formatting
    This allows us to detect structurally identical code with different names
    """
    
    def __init__(self):
        self.var_counter = 0
        self.var_map = {}
        
    def visit_Name(self, node):
        # Normalize variable names to generic names
        if isinstance(node.ctx, ast.Store):
            if node.id not in self.var_map:
                self.var_map[node.id] = f"var_{self.var_counter}"
                self.var_counter += 1
            node.id = self.var_map[node.id]
        elif isinstance(node.ctx, ast.Load):
            if node.id in self.var_map:
                node.id = self.var_map[node.id]
            else:
                # Keep built-in functions as-is
                if node.id not in ['print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict']:
                    node.id = f"unknown_var"
        return node
        
    def visit_FunctionDef(self, node):
        # Normalize function names
        original_name = node.name
        node.name = "normalized_function"
        
        # Reset variable mapping for each function
        old_var_map = self.var_map.copy()
        old_counter = self.var_counter
        
        self.var_map = {}
        self.var_counter = 0
        
        result = self.generic_visit(node)
        
        # Restore for outer scope
        self.var_map = old_var_map
        self.var_counter = old_counter
        
        return result
        
    def visit_arg(self, node):
        # Normalize argument names
        if node.arg not in self.var_map:
            self.var_map[node.arg] = f"arg_{len(self.var_map)}"
        node.arg = self.var_map[node.arg]
        return node
        
    def visit_Constant(self, node):
        # Keep string and number literals as-is for now
        # Could normalize these too for more aggressive duplicate detection
        return node


class DuplicateDetector:
    """
    Detects duplicate and similar code blocks
    """
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
        self.code_blocks: List[CodeBlock] = []
        self.hash_groups: Dict[str, List[CodeBlock]] = defaultdict(list)
        
    def analyze_duplicates(self, all_functions: Dict[str, Any], all_files: Dict[str, Any]) -> List[DuplicateIssue]:
        """
        Main analysis method - find all types of duplicates
        
        Args:
            all_functions: Function info from codebase analyzer  
            all_files: File info from codebase analyzer
            
        Returns:
            List of duplicate issues
        """
        issues = []
        
        # Extract all code blocks
        self._extract_code_blocks(all_functions, all_files)
        
        # Find exact duplicates (same AST structure)
        issues.extend(self._find_exact_duplicates())
        
        # Find similar duplicates (fuzzy matching)
        issues.extend(self._find_similar_duplicates())
        
        # Find copy-paste duplicates (identical lines)
        issues.extend(self._find_copy_paste_duplicates())
        
        return sorted(issues, key=lambda x: (x.line, x.column))
        
    def _extract_code_blocks(self, all_functions: Dict[str, Any], all_files: Dict[str, Any]):
        """Extract code blocks from all functions"""
        self.code_blocks = []
        
        for func_key, func_info in all_functions.items():
            file_path, func_name = func_key.split("::", 1)
            
            # Read the source file to extract function code
            try:
                from pathlib import Path
                import os
                full_path = Path(file_path)
                
                # Debug logging
                print(f"🔍 Attempting to read file: {file_path}")
                print(f"🔍 Current working directory: {os.getcwd()}")
                print(f"🔍 Full path: {full_path}")
                print(f"🔍 Is absolute: {full_path.is_absolute()}")
                
                if not full_path.is_absolute():
                    # Try different path resolution strategies
                    # First try current working directory
                    full_path = Path(".") / file_path
                    if not full_path.exists():
                        # Try without any prefix if it was already relative to repo
                        full_path = Path(file_path)
                        if not full_path.exists():
                            print(f"⚠️ File not found: {file_path} (tried multiple paths)")
                            continue
                    
                with open(full_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                # Extract function lines (rough estimation)
                start_line = func_info.line_number - 1  # Convert to 0-based
                
                # Find function end by looking for the next function or class at same indentation
                end_line = len(lines)
                if start_line < len(lines):
                    func_line = lines[start_line]
                    base_indent = len(func_line) - len(func_line.lstrip())
                    
                    for i in range(start_line + 1, len(lines)):
                        line = lines[i]
                        if line.strip():  # Non-empty line
                            current_indent = len(line) - len(line.lstrip())
                            if current_indent <= base_indent and (line.strip().startswith('def ') or line.strip().startswith('class ')):
                                end_line = i
                                break
                                
                # Extract function content
                if start_line < len(lines):
                    function_lines = lines[start_line:end_line]
                    content = ''.join(function_lines)
                    
                    # Normalize the content
                    normalized_content = self._normalize_content(content, func_name)
                    
                    # Create hashes
                    ast_hash = self._compute_ast_hash(content)
                    token_hash = self._compute_token_hash(content)
                    
                    code_block = CodeBlock(
                        content=content,
                        normalized_content=normalized_content,
                        file_path=file_path,
                        function_name=func_name,
                        start_line=func_info.line_number,
                        end_line=func_info.line_number + len(function_lines) - 1,
                        ast_hash=ast_hash,
                        token_hash=token_hash
                    )
                    
                    self.code_blocks.append(code_block)
                    self.hash_groups[ast_hash].append(code_block)
                    
            except Exception as e:
                print(f"⚠️ Could not extract code from {file_path}: {e}")
                continue
                
    def _normalize_content(self, content: str, func_name: str) -> str:
        """Normalize code content for comparison"""
        try:
            # Parse and normalize AST
            tree = ast.parse(content)
            normalizer = ASTNormalizer()
            normalized_tree = normalizer.visit(tree)
            
            # Convert back to string
            import astor
            return astor.to_source(normalized_tree)
        except:
            # Fallback to simple normalization if AST fails
            return self._simple_normalize(content)
            
    def _simple_normalize(self, content: str) -> str:
        """Simple content normalization as fallback"""
        # Remove comments
        lines = content.split('\n')
        normalized_lines = []
        
        for line in lines:
            # Remove comments
            if '#' in line:
                line = line[:line.index('#')]
            
            # Remove extra whitespace
            line = line.strip()
            
            if line:  # Skip empty lines
                # Normalize variable names (basic regex replacement)
                line = re.sub(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', 'VAR', line)
                # Normalize string literals
                line = re.sub(r'"[^"]*"', '"STRING"', line)
                line = re.sub(r"'[^']*'", "'STRING'", line)
                
                normalized_lines.append(line)
                
        return '\n'.join(normalized_lines)
        
    def _compute_ast_hash(self, content: str) -> str:
        """Compute hash of normalized AST structure"""
        try:
            tree = ast.parse(content)
            normalizer = ASTNormalizer()
            normalized_tree = normalizer.visit(tree)
            
            # Create a string representation of the AST structure
            ast_str = ast.dump(normalized_tree, annotate_fields=False)
            
            return hashlib.md5(ast_str.encode()).hexdigest()
        except:
            # Fallback to content hash
            return hashlib.md5(content.encode()).hexdigest()
            
    def _compute_token_hash(self, content: str) -> str:
        """Compute hash of token sequence (ignoring names)"""
        try:
            import tokenize
            import io
            
            tokens = []
            for token in tokenize.generate_tokens(io.StringIO(content).readline):
                # Skip names and comments, keep structure tokens
                if token.type not in [tokenize.NAME, tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE]:
                    tokens.append(token.string)
                elif token.type == tokenize.NAME and token.string in ['def', 'class', 'if', 'else', 'for', 'while', 'return']:
                    tokens.append(token.string)
                    
            token_str = ''.join(tokens)
            return hashlib.md5(token_str.encode()).hexdigest()
        except:
            return hashlib.md5(content.encode()).hexdigest()
            
    def _find_exact_duplicates(self) -> List[DuplicateIssue]:
        """Find exact duplicates using AST hash matching"""
        issues = []
        
        for ast_hash, blocks in self.hash_groups.items():
            if len(blocks) > 1:
                # Group by identical content
                content_groups = defaultdict(list)
                for block in blocks:
                    content_groups[block.normalized_content].append(block)
                    
                for normalized_content, duplicate_blocks in content_groups.items():
                    if len(duplicate_blocks) > 1:
                        # Found exact duplicates
                        primary_block = duplicate_blocks[0]
                        
                        for duplicate_block in duplicate_blocks[1:]:
                            issues.append(DuplicateIssue(
                                rule_id='exact_duplicate',
                                severity='warning',
                                line=duplicate_block.start_line,
                                column=0,
                                message=f'Exact duplicate of function "{primary_block.function_name}" from {primary_block.file_path}:{primary_block.start_line}',
                                suggestion=f'Consider extracting common logic into a shared function or module',
                                evidence={
                                    'duplicate_of': primary_block.function_name,
                                    'original_file': primary_block.file_path,
                                    'original_line': primary_block.start_line,
                                    'duplicate_file': duplicate_block.file_path,
                                    'duplicate_line': duplicate_block.start_line,
                                    'ast_hash': ast_hash,
                                    'lines_count': duplicate_block.end_line - duplicate_block.start_line + 1,
                                    'detection_method': 'AST_hash_matching'
                                }
                            ))
                            
        return issues
        
    def _find_similar_duplicates(self) -> List[DuplicateIssue]:
        """Find similar duplicates using content similarity"""
        issues = []
        
        # Compare all pairs of code blocks
        for i, block1 in enumerate(self.code_blocks):
            for j, block2 in enumerate(self.code_blocks[i+1:], i+1):
                # Skip if same file and function
                if block1.file_path == block2.file_path and block1.function_name == block2.function_name:
                    continue
                    
                # Skip if already found as exact duplicate
                if block1.ast_hash == block2.ast_hash:
                    continue
                    
                # Calculate similarity
                similarity = self._calculate_similarity(block1.normalized_content, block2.normalized_content)
                
                if similarity >= self.similarity_threshold:
                    # Found similar code
                    issues.append(DuplicateIssue(
                        rule_id='similar_duplicate',
                        severity='suggestion',
                        line=block2.start_line,
                        column=0,
                        message=f'Similar code detected ({similarity:.1%} similar) to function "{block1.function_name}" from {block1.file_path}:{block1.start_line}',
                        suggestion='Consider refactoring similar code into a shared function with parameters for the differences',
                        evidence={
                            'similar_to': block1.function_name,
                            'original_file': block1.file_path,
                            'original_line': block1.start_line,
                            'similar_file': block2.file_path,
                            'similar_line': block2.start_line,
                            'similarity_score': round(similarity, 3),
                            'threshold': self.similarity_threshold,
                            'detection_method': 'content_similarity_analysis'
                        }
                    ))
                    
        return issues
        
    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two code blocks"""
        # Use difflib for similarity calculation
        sequence_matcher = difflib.SequenceMatcher(None, content1, content2)
        return sequence_matcher.ratio()
        
    def _find_copy_paste_duplicates(self) -> List[DuplicateIssue]:
        """Find copy-paste duplicates (identical consecutive lines)"""
        issues = []
        
        # Group code blocks by file for line-by-line comparison
        file_blocks = defaultdict(list)
        for block in self.code_blocks:
            file_blocks[block.file_path].append(block)
            
        # Look for identical line sequences within and across files
        for file_path, blocks in file_blocks.items():
            for i, block1 in enumerate(blocks):
                for j, block2 in enumerate(blocks[i+1:], i+1):
                    # Find common line sequences
                    lines1 = block1.content.strip().split('\n')
                    lines2 = block2.content.strip().split('\n')
                    
                    # Remove leading whitespace for comparison
                    lines1_clean = [line.strip() for line in lines1 if line.strip()]
                    lines2_clean = [line.strip() for line in lines2 if line.strip()]
                    
                    # Find longest common subsequence
                    common_lines = self._find_common_lines(lines1_clean, lines2_clean)
                    
                    if len(common_lines) >= 5:  # At least 5 identical lines
                        issues.append(DuplicateIssue(
                            rule_id='copy_paste_duplicate',
                            severity='warning',
                            line=block2.start_line,
                            column=0,
                            message=f'Copy-paste duplication detected: {len(common_lines)} identical lines with function "{block1.function_name}"',
                            suggestion='Extract common lines into a shared function or method',
                            evidence={
                                'copy_paste_from': block1.function_name,
                                'original_line': block1.start_line,
                                'duplicate_line': block2.start_line,
                                'identical_lines_count': len(common_lines),
                                'sample_lines': common_lines[:3],  # Show first 3 lines as example
                                'detection_method': 'line_sequence_matching'
                            }
                        ))
                        
        return issues
        
    def _find_common_lines(self, lines1: List[str], lines2: List[str]) -> List[str]:
        """Find common consecutive lines between two lists"""
        common = []
        
        # Simple approach: find all identical lines
        for line1 in lines1:
            if line1 in lines2 and len(line1.strip()) > 10:  # Skip very short lines
                common.append(line1)
                
        return common
        
    def get_duplicate_statistics(self) -> Dict[str, Any]:
        """Get statistics about duplicates found"""
        stats = {
            'total_functions_analyzed': len(self.code_blocks),
            'exact_duplicate_groups': 0,
            'similar_duplicate_pairs': 0,
            'copy_paste_instances': 0,
            'files_with_duplicates': set(),
            'most_duplicated_patterns': []
        }
        
        # Count exact duplicates
        for hash_group in self.hash_groups.values():
            if len(hash_group) > 1:
                stats['exact_duplicate_groups'] += 1
                for block in hash_group:
                    stats['files_with_duplicates'].add(block.file_path)
                    
        return stats


def analyze_file_duplicates(
    file_path: str, 
    all_functions: Dict[str, Any] = None, 
    all_files: Dict[str, Any] = None,
    similarity_threshold: float = 0.85
) -> List[DuplicateIssue]:
    """
    Convenience function to analyze duplicates for a single file
    """
    detector = DuplicateDetector(similarity_threshold)
    
    if all_functions and all_files:
        # Full codebase analysis
        return detector.analyze_duplicates(all_functions, all_files)
    else:
        # Single file analysis (limited)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse functions in this file
            tree = ast.parse(content)
            
            functions = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_key = f"{file_path}::{node.name}"
                    
                    # Create a mock function info object
                    class MockFuncInfo:
                        def __init__(self, name, line_number):
                            self.name = name
                            self.line_number = line_number
                            
                    functions[func_key] = MockFuncInfo(node.name, node.lineno)
                    
            files = {file_path: {"functions": {}, "path": file_path}}
            
            return detector.analyze_duplicates(functions, files)
            
        except Exception as e:
            return [DuplicateIssue(
                rule_id='analysis_error',
                severity='warning',
                line=1,
                column=0,
                message=f'Could not analyze duplicates: {e}',
                suggestion='Check file syntax and encoding',
                evidence={'error': str(e)}
            )]


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        file_to_analyze = sys.argv[1]
        threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.85
        
        print(f"Analyzing {file_to_analyze} for duplicates (threshold: {threshold})...")
        
        issues = analyze_file_duplicates(file_to_analyze, similarity_threshold=threshold)
        
        if not issues:
            print("✅ No duplicates detected!")
        else:
            print(f"🔍 Found {len(issues)} duplicate issues:")
            for issue in issues:
                print(f"\n{issue.severity.upper()} - Line {issue.line}")
                print(f"Rule: {issue.rule_id}")
                print(f"Issue: {issue.message}")
                print(f"Fix: {issue.suggestion}")
                if 'similarity_score' in issue.evidence:
                    print(f"Similarity: {issue.evidence['similarity_score']:.1%}")
    else:
        print("Usage: python duplicate_detector.py <file_to_analyze> [similarity_threshold]")