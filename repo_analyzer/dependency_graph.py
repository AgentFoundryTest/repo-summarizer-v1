"""
Repository dependency graph generator.

Analyzes import statements in Python and JavaScript/TypeScript files to build
an intra-repository dependency graph, producing both JSON and Markdown outputs.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any


class DependencyGraphError(Exception):
    """Raised when dependency graph generation fails."""
    pass


def _parse_python_imports(content: str, file_path: Path) -> List[str]:
    """
    Parse Python import statements to extract imported modules.
    
    Args:
        content: File content as string
        file_path: Path to the file being parsed
    
    Returns:
        List of imported module paths (relative or absolute)
    """
    imports = []
    
    # Helper function to filter out lines that are in strings/docstrings
    def _filter_string_content(content: str) -> List[Tuple[int, str]]:
        """
        Filter out content inside strings and return list of (line_num, line) tuples
        that contain actual code (not strings/docstrings).
        """
        lines = content.split('\n')
        filtered = []
        in_triple_single = False
        in_triple_double = False
        
        for i, line in enumerate(lines):
            # Track multi-line string state
            if '"""' in line:
                count = line.count('"""')
                # Toggle state for each triple quote
                for _ in range(count):
                    in_triple_double = not in_triple_double
            if "'''" in line:
                count = line.count("'''")
                for _ in range(count):
                    in_triple_single = not in_triple_single
            
            # Only include lines not in multi-line strings
            if not in_triple_single and not in_triple_double:
                # Additional check: skip if this line appears to be a single-line string
                stripped = line.strip()
                # Simple heuristic: if line starts with a quote, it's likely a string
                if not (stripped.startswith('"') and not stripped.startswith('"""')) and \
                   not (stripped.startswith("'") and not stripped.startswith("'''")):
                    filtered.append((i, line))
        
        return filtered
    
    # Filter out string content first
    code_lines = _filter_string_content(content)
    
    # Pre-process content to handle line continuations and parenthesized imports
    # Join lines that are part of multi-line import statements
    processed_lines = []
    i = 0
    while i < len(code_lines):
        line_num, line = code_lines[i]
        stripped = line.strip()
        
        # Skip comment lines
        if stripped.startswith('#'):
            i += 1
            continue
        
        # Check if this is an import or from statement that might continue
        if stripped.startswith('import ') or stripped.startswith('from '):
            # Accumulate lines until we find the end of the statement
            accumulated = line
            
            # Check if there's a parenthesis that needs to be closed
            if '(' in accumulated and ')' not in accumulated:
                i += 1
                while i < len(code_lines):
                    _, next_line = code_lines[i]
                    accumulated += ' ' + next_line.strip()
                    if ')' in next_line:
                        break
                    i += 1
            # Check for line continuation with backslash
            elif accumulated.rstrip().endswith('\\'):
                accumulated = accumulated.rstrip()[:-1]  # Remove the backslash
                i += 1
                while i < len(code_lines):
                    _, next_line = code_lines[i]
                    accumulated += ' ' + next_line.strip()
                    if not next_line.rstrip().endswith('\\'):
                        break
                    accumulated = accumulated.rstrip()[:-1]  # Remove the backslash
                    i += 1
            
            processed_lines.append(accumulated)
        else:
            processed_lines.append(line)
        
        i += 1
    
    # Match 'import module' statements - captures all modules in comma-separated list
    import_pattern = r'^\s*import\s+([\w.,\s]+?)(?:\s*#.*)?$'
    
    # Match 'from module import name' - captures both module and imported names
    # Updated to handle parentheses and whitespace more flexibly
    from_pattern = r'^\s*from\s+([\w.]+)\s+import\s+(?:\()?([^)#]+)(?:\))?'
    
    for line in processed_lines:
        # Skip comments
        if line.strip().startswith('#'):
            continue
        
        # Check for 'import' statement
        match = re.match(import_pattern, line)
        if match:
            # Parse comma-separated modules (e.g., "import os, sys, json")
            modules_str = match.group(1)
            # Split by comma and process each module
            for module_part in modules_str.split(','):
                module_part = module_part.strip()
                if not module_part:
                    continue
                # Handle "module as alias" - extract just the module name
                if ' as ' in module_part:
                    module = module_part.split(' as ')[0].strip()
                else:
                    module = module_part
                imports.append(module)
            continue
        
        # Check for 'from' statement
        match = re.match(from_pattern, line)
        if match:
            module = match.group(1)
            imported_names = match.group(2)
            
            # For relative imports like "from . import utils", combine module and name
            if module.startswith('.'):
                # Extract individual names from the import list
                names = [n.strip() for n in imported_names.split(',')]
                for name in names:
                    # Skip wildcard imports
                    if name == '*':
                        imports.append(module)
                        continue
                    # Remove 'as alias' part if present
                    name = name.split()[0] if ' ' in name else name
                    # Combine relative path with imported name
                    # If module has alpha (like '...parent'), add dot separator
                    # If module is only dots (like '..'), concatenate directly
                    if any(c.isalpha() for c in module):
                        imports.append(f"{module}.{name}")
                    else:
                        imports.append(f"{module}{name}")
            else:
                # For absolute imports, combine module with imported names
                # e.g., "from pkg import mod" should resolve to "pkg.mod"
                names = [n.strip() for n in imported_names.split(',')]
                for name in names:
                    # Skip wildcard imports - just use the base module
                    if name == '*':
                        imports.append(module)
                        continue
                    # Remove 'as alias' part if present
                    name = name.split()[0] if ' ' in name else name
                    # Combine module with imported name
                    imports.append(f"{module}.{name}")
    
    return imports


def _parse_js_imports(content: str, file_path: Path) -> List[str]:
    """
    Parse JavaScript/TypeScript import statements to extract imported modules.
    
    Args:
        content: File content as string
        file_path: Path to the file being parsed
    
    Returns:
        List of imported module paths (relative or absolute)
    """
    imports = []
    
    # Remove comments more carefully to avoid removing // in strings
    # Remove multi-line comments first
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Remove single-line comments, but only actual comments (not // in strings)
    # This is a simplified approach: remove // comments only when they appear after code
    # More sophisticated parsing would require a full tokenizer
    lines = []
    for line in content.split('\n'):
        # Simple heuristic: if line has quotes before //, keep the whole line
        # If // appears outside quotes, remove the comment part
        # This isn't perfect but handles common cases
        if '//' in line:
            # Check if // is in a string by looking for quotes
            before_comment = line.split('//')[0]
            # Count quotes to determine if // is in a string
            single_quotes = before_comment.count("'") - before_comment.count("\\'")
            double_quotes = before_comment.count('"') - before_comment.count('\\"')
            # If odd number of quotes, // is likely in a string
            if single_quotes % 2 == 1 or double_quotes % 2 == 1:
                lines.append(line)
            else:
                # Remove the comment part
                lines.append(before_comment)
        else:
            lines.append(line)
    content = '\n'.join(lines)
    
    # Match ES6 imports: import ... from 'module' or import ... from "module"
    # This handles multi-line imports by matching across newlines
    es6_pattern = r'''import\s+(?:[\w\s{},*\n]+\s+from\s+)?['"]([^'"]+)['"]'''
    
    # Match CommonJS require: require('module') or require("module")
    require_pattern = r'''require\s*\(['"]([^'"]+)['"]\)'''
    
    # Match dynamic imports: import('module') or import("module")
    dynamic_pattern = r'''import\s*\(['"]([^'"]+)['"]\)'''
    
    # Helper function to check if a position is inside a string literal
    def is_in_string(text: str, pos: int) -> bool:
        """Check if position is inside a string literal, handling escaped quotes."""
        # Count quotes before this position, excluding escaped ones
        before = text[:pos]
        
        # Count unescaped quotes for each type
        def count_unescaped(s: str, quote: str) -> int:
            count = 0
            i = 0
            while i < len(s):
                if s[i] == quote:
                    # Check if this quote is escaped
                    # Count preceding backslashes
                    num_backslashes = 0
                    j = i - 1
                    while j >= 0 and s[j] == '\\':
                        num_backslashes += 1
                        j -= 1
                    # If even number of backslashes (including 0), quote is not escaped
                    if num_backslashes % 2 == 0:
                        count += 1
                i += 1
            return count
        
        # Check for each type of quote
        in_single = count_unescaped(before, "'") % 2 == 1
        in_double = count_unescaped(before, '"') % 2 == 1
        in_template = count_unescaped(before, '`') % 2 == 1
        return in_single or in_double or in_template
    
    # Find ES6 imports (multi-line safe)
    for match in re.finditer(es6_pattern, content):
        # Check if this match is inside a string literal
        if not is_in_string(content, match.start()):
            module = match.group(1)
            imports.append(module)
    
    # Find CommonJS require
    for match in re.finditer(require_pattern, content):
        if not is_in_string(content, match.start()):
            module = match.group(1)
            imports.append(module)
    
    # Find dynamic imports
    for match in re.finditer(dynamic_pattern, content):
        if not is_in_string(content, match.start()):
            module = match.group(1)
            imports.append(module)
    
    return imports


def _resolve_python_import(
    import_path: str,
    source_file: Path,
    repo_root: Path
) -> Optional[Path]:
    """
    Resolve a Python import to an actual file path within the repository.
    
    Args:
        import_path: Import string (e.g., 'module.submodule', '.utils', '..config')
        source_file: Path to the file containing the import
        repo_root: Repository root directory
    
    Returns:
        Resolved Path or None if not found/external
    """
    # Skip standard library and external packages (heuristic)
    # Common standard library modules
    stdlib_modules = {
        'os', 'sys', 'json', 're', 'pathlib', 'typing', 'subprocess',
        'argparse', 'tempfile', 'collections', 'itertools', 'functools',
        'datetime', 'time', 'math', 'random', 'unittest', 'pytest'
    }
    
    first_part = import_path.split('.')[0]
    if first_part in stdlib_modules:
        return None
    
    # Relative imports start with '.'
    if import_path.startswith('.'):
        # Get the directory containing the source file
        source_dir = source_file.parent
        
        # Count leading dots for relative levels
        level = 0
        for char in import_path:
            if char == '.':
                level += 1
            else:
                break
        
        # Go up the specified number of levels (level-1 because one dot means current dir)
        current = source_dir
        for _ in range(level - 1):
            current = current.parent
            if current == repo_root or current == current.parent:
                break
        
        # Extract the module path after the dots
        module_path = import_path[level:]
        if module_path:
            parts = module_path.split('.')
        else:
            # Just dots, no module name - this is a wildcard import like "from . import *"
            # Resolve to the package's __init__.py
            if (current / '__init__.py').exists():
                return current / '__init__.py'
            return None
        
        # Try to resolve to a file or __init__.py
        target = current
        for part in parts:
            target = target / part
        
        # Try as a module file (.py)
        if (target.with_suffix('.py')).exists():
            return target.with_suffix('.py')
        
        # Try as a package (__init__.py)
        if (target / '__init__.py').exists():
            return target / '__init__.py'
        
        return None
    
    # Absolute import - try to resolve from repo root
    parts = import_path.split('.')
    
    # Try to resolve from repo root, checking common layout patterns
    # 1. Direct under repo root
    # 2. Under src/ directory (common Python layout)
    # 3. Under lib/ directory (less common but used)
    target = None
    search_paths = [
        repo_root / parts[0],
        repo_root / 'src' / parts[0],
        repo_root / 'lib' / parts[0],
    ]
    
    for potential_target in search_paths:
        # Check if it's a file at this location (e.g., util.py)
        if potential_target.with_suffix('.py').exists():
            target = potential_target
            break
        # Check if it's a directory (package) at this location
        if potential_target.exists() and potential_target.is_dir():
            target = potential_target
            break
    
    # If we didn't find the target in any common location, return None
    if target is None:
        return None
    
    # For single-part imports that are files, return the file
    if len(parts) == 1 and target.with_suffix('.py').exists():
        return target.with_suffix('.py')
    
    # Navigate through the parts
    current = target
    for i, part in enumerate(parts[1:], 1):
        next_path = current / part
        
        # Check if it's a file
        if next_path.with_suffix('.py').exists():
            return next_path.with_suffix('.py')
        
        # Check if it's a directory with __init__.py
        if (next_path / '__init__.py').exists():
            current = next_path
        else:
            # Try as file at this level
            if (current / part).with_suffix('.py').exists():
                return (current / part).with_suffix('.py')
            # If we can't find the submodule, fall back to the package's __init__.py
            # This handles cases like "from pkg import symbol" where symbol is in pkg/__init__.py
            if (current / '__init__.py').exists():
                return current / '__init__.py'
            return None
    
    # If we've navigated through all parts, check for __init__.py
    if (current / '__init__.py').exists():
        return current / '__init__.py'
    
    return None


def _resolve_js_import(
    import_path: str,
    source_file: Path,
    repo_root: Path
) -> Optional[Path]:
    """
    Resolve a JavaScript/TypeScript import to an actual file path within the repository.
    
    Args:
        import_path: Import string (e.g., './module', '../utils')
        source_file: Path to the file containing the import
        repo_root: Repository root directory
    
    Returns:
        Resolved Path or None if not found/external
    """
    # Skip node_modules and external packages
    if not import_path.startswith('.') and not import_path.startswith('/'):
        # This is a package import, not a relative file import
        return None
    
    # Get the directory containing the source file
    source_dir = source_file.parent
    
    # Resolve relative path
    if import_path.startswith('./') or import_path.startswith('../'):
        target = (source_dir / import_path).resolve()
    else:
        # Absolute path from repo root
        target = (repo_root / import_path.lstrip('/')).resolve()
    
    # Check if target is within repository
    try:
        target.relative_to(repo_root)
    except ValueError:
        # Outside repository
        return None
    
    # Try various extensions
    extensions = ['.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs']
    
    # Try as direct file
    if target.exists() and target.is_file():
        return target
    
    # Try with extensions
    for ext in extensions:
        if target.with_suffix(ext).exists():
            return target.with_suffix(ext)
    
    # Try as directory with index file
    if target.is_dir():
        for ext in extensions:
            index_file = target / f'index{ext}'
            if index_file.exists():
                return index_file
    
    return None


def _scan_file_dependencies(
    file_path: Path,
    repo_root: Path
) -> List[Path]:
    """
    Scan a single file for dependencies and resolve them to file paths.
    
    Args:
        file_path: Path to the file to scan
        repo_root: Repository root directory
    
    Returns:
        List of resolved dependency file paths
        
    Raises:
        IOError/OSError: If the file cannot be read
    """
    dependencies = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except (IOError, OSError) as e:
        # Re-raise the error so it can be caught and recorded in build_dependency_graph
        raise IOError(f"Cannot read file: {e}")
    
    # Determine file type and parse accordingly
    suffix = file_path.suffix.lower()
    
    if suffix == '.py':
        imports = _parse_python_imports(content, file_path)
        for import_path in imports:
            resolved = _resolve_python_import(import_path, file_path, repo_root)
            if resolved:
                dependencies.append(resolved)
    
    elif suffix in ['.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs']:
        imports = _parse_js_imports(content, file_path)
        for import_path in imports:
            resolved = _resolve_js_import(import_path, file_path, repo_root)
            if resolved:
                dependencies.append(resolved)
    
    return dependencies


def build_dependency_graph(
    root_path: Path,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    exclude_dirs: Optional[Set[str]] = None
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Build a dependency graph for files in the repository.
    
    Args:
        root_path: Root directory to scan
        include_patterns: List of patterns to include (e.g., ['*.py', '*.js'])
        exclude_patterns: List of patterns to exclude
        exclude_dirs: Set of directory names to skip
    
    Returns:
        Tuple of (graph_data, errors) where graph_data contains nodes and edges,
        and errors is a list of error messages
    """
    from repo_analyzer.file_summary import scan_files
    
    errors = []
    
    # Scan for files
    try:
        files = scan_files(root_path, include_patterns, exclude_patterns, exclude_dirs)
    except Exception as e:
        raise DependencyGraphError(f"Failed to scan files: {e}")
    
    # Normalize root_path to absolute for consistent comparisons
    root_path = root_path.resolve()
    
    # Build dependency map - normalize all file paths to absolute
    dependency_map: Dict[Path, List[Path]] = {}
    # Normalize all files to absolute paths for consistent comparisons
    all_files: Set[Path] = {f.resolve() for f in files}
    
    for file_path in files:
        try:
            # Normalize file_path to absolute
            file_path_abs = file_path.resolve()
            deps = _scan_file_dependencies(file_path_abs, root_path)
            dependency_map[file_path_abs] = deps
        except Exception as e:
            try:
                rel = file_path.relative_to(root_path)
            except ValueError:
                rel = file_path
            errors.append(f"Error scanning {rel}: {e}")
            dependency_map[file_path.resolve()] = []
    
    # Build graph structure
    nodes = []
    edges = []
    
    for file_path in sorted(all_files):
        try:
            rel_path = file_path.relative_to(root_path).as_posix()
        except ValueError:
            rel_path = str(file_path)
        
        nodes.append({
            'id': rel_path,
            'path': rel_path,
            'type': 'file'
        })
    
    # Create edges (deduplicate by source-target pair)
    edge_set = set()  # Track unique (source, target) pairs
    for source_file, dependencies in dependency_map.items():
        try:
            source_rel = source_file.relative_to(root_path).as_posix()
        except ValueError:
            source_rel = str(source_file)
        
        for dep_file in dependencies:
            try:
                target_rel = dep_file.relative_to(root_path).as_posix()
            except ValueError:
                target_rel = str(dep_file)
            
            # Only create edge if target is in our scanned files
            if dep_file in all_files:
                edge_pair = (source_rel, target_rel)
                if edge_pair not in edge_set:
                    edge_set.add(edge_pair)
                    edges.append({
                        'source': source_rel,
                        'target': target_rel
                    })
    
    graph_data = {
        'nodes': nodes,
        'edges': edges
    }
    
    return graph_data, errors


def generate_dependency_report(
    root_path: Path,
    output_dir: Path,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    exclude_dirs: Optional[Set[str]] = None,
    dry_run: bool = False
) -> None:
    """
    Generate dependency graph report in JSON and Markdown formats.
    
    Args:
        root_path: Root directory to scan
        output_dir: Directory to write output files
        include_patterns: List of patterns to include (e.g., ['*.py', '*.js'])
        exclude_patterns: List of patterns to exclude
        exclude_dirs: Set of directory names to skip
        dry_run: If True, only log intent without writing files
    
    Raises:
        DependencyGraphError: If dependency graph generation fails
    """
    try:
        # Build dependency graph
        graph_data, errors = build_dependency_graph(
            root_path, include_patterns, exclude_patterns, exclude_dirs
        )
        
        # Generate JSON output
        json_path = output_dir / "dependencies.json"
        json_content = json.dumps(graph_data, indent=2)
        
        if dry_run:
            print(f"[DRY RUN] Would write dependencies.json to: {json_path}")
            print(f"[DRY RUN] Nodes: {len(graph_data['nodes'])}, Edges: {len(graph_data['edges'])}")
            if errors:
                print(f"[DRY RUN] Errors: {len(errors)}")
        else:
            with open(json_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
            print(f"Dependency graph JSON written: {json_path}")
        
        # Generate Markdown output
        markdown_lines = ["# Dependency Graph\n"]
        markdown_lines.append("Intra-repository dependency analysis for Python and JavaScript/TypeScript files.\n")
        
        # Statistics
        markdown_lines.append("## Statistics\n")
        markdown_lines.append(f"- **Total files**: {len(graph_data['nodes'])}")
        markdown_lines.append(f"- **Total dependencies**: {len(graph_data['edges'])}\n")
        
        # Calculate some interesting metrics
        dependents_count: Dict[str, int] = {}
        dependencies_count: Dict[str, int] = {}
        
        for edge in graph_data['edges']:
            source = edge['source']
            target = edge['target']
            
            dependencies_count[source] = dependencies_count.get(source, 0) + 1
            dependents_count[target] = dependents_count.get(target, 0) + 1
        
        # Most depended upon files
        if dependents_count:
            markdown_lines.append("## Most Depended Upon Files\n")
            sorted_dependents = sorted(
                dependents_count.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            for file_path, count in sorted_dependents:
                markdown_lines.append(f"- `{file_path}` ({count} dependents)")
            markdown_lines.append("")
        
        # Files with most dependencies
        if dependencies_count:
            markdown_lines.append("## Files with Most Dependencies\n")
            sorted_dependencies = sorted(
                dependencies_count.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            
            for file_path, count in sorted_dependencies:
                markdown_lines.append(f"- `{file_path}` ({count} dependencies)")
            markdown_lines.append("")
        
        # Errors section
        if errors:
            markdown_lines.append("## Errors\n")
            markdown_lines.append(f"The following errors occurred during dependency analysis:\n")
            for error in errors:
                markdown_lines.append(f"- {error}")
            markdown_lines.append("")
        
        markdown_content = "\n".join(markdown_lines)
        markdown_path = output_dir / "dependencies.md"
        
        if dry_run:
            print(f"[DRY RUN] Would write dependencies.md to: {markdown_path}")
            print(f"[DRY RUN] Content length: {len(markdown_content)} bytes")
        else:
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"Dependency graph Markdown written: {markdown_path}")
        
        # Report errors to console and raise exception if any errors occurred
        if errors:
            if not dry_run:
                print(f"\nError: {len(errors)} error(s) occurred during dependency analysis")
                for error in errors[:5]:  # Show first 5 errors
                    print(f"  - {error}")
                if len(errors) > 5:
                    print(f"  ... and {len(errors) - 5} more")
            # Raise exception to ensure non-zero exit code
            raise DependencyGraphError(
                f"Dependency graph generation failed with {len(errors)} error(s). "
                f"See dependencies.md for details."
            )
    
    except DependencyGraphError:
        # Re-raise DependencyGraphError as-is
        raise
    except Exception as e:
        raise DependencyGraphError(f"Failed to generate dependency report: {e}")
