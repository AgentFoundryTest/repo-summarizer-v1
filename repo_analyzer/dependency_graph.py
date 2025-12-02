# Copyright (c) 2025 John Brosnihan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Repository dependency graph generator.

Analyzes import statements across multiple languages to build an intra-repository 
dependency graph, producing both JSON and Markdown outputs. Also captures and 
classifies external dependencies (stdlib vs third-party).

Supported languages:
- Python: import/from statements
- JavaScript/TypeScript: import/require/dynamic import
- C/C++: #include directives
- Rust: use/mod statements
- Go: import statements
- Java: import statements
- C#: using statements
- Swift: import statements
- HTML/CSS: href/src/url() references (local files only)
- SQL: vendor-specific include statements
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from repo_analyzer.stdlib_classification import classify_import


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


def _parse_c_cpp_includes(content: str, file_path: Path) -> List[str]:
    """
    Parse C/C++ #include statements to extract included headers.
    
    Args:
        content: File content as string
        file_path: Path to the file being parsed
    
    Returns:
        List of included header paths
    """
    includes = []
    
    # Remove comments to avoid false positives
    # Remove multi-line comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Remove single-line comments
    lines = []
    for line in content.split('\n'):
        # Remove // comments
        if '//' in line:
            line = line.split('//')[0]
        lines.append(line)
    content = '\n'.join(lines)
    
    # Match #include "header.h" or #include <header.h>
    # Pattern captures both quoted and angle-bracket includes
    include_pattern = r'^\s*#\s*include\s*[<"]([^>"]+)[>"]'
    
    for line in content.split('\n'):
        match = re.match(include_pattern, line)
        if match:
            header = match.group(1)
            includes.append(header)
    
    return includes


def _parse_rust_imports(content: str, file_path: Path) -> List[str]:
    """
    Parse Rust use and mod statements to extract imported modules.
    
    Args:
        content: File content as string
        file_path: Path to the file being parsed
    
    Returns:
        List of imported module paths
    """
    imports = []
    
    # Remove comments
    # Remove multi-line comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Remove single-line comments
    lines = []
    for line in content.split('\n'):
        if '//' in line:
            line = line.split('//')[0]
        lines.append(line)
    content = '\n'.join(lines)
    
    # Match 'use module::path;' statements
    use_pattern = r'^\s*use\s+([\w:]+)'
    
    # Match 'mod module;' statements
    mod_pattern = r'^\s*mod\s+([\w]+)'
    
    for line in content.split('\n'):
        # Check for use statements
        match = re.match(use_pattern, line)
        if match:
            module = match.group(1)
            imports.append(module)
            continue
        
        # Check for mod statements
        match = re.match(mod_pattern, line)
        if match:
            module = match.group(1)
            imports.append(module)
    
    return imports


def _parse_go_imports(content: str, file_path: Path) -> List[str]:
    """
    Parse Go import statements to extract imported packages.
    
    Args:
        content: File content as string
        file_path: Path to the file being parsed
    
    Returns:
        List of imported package paths
    """
    imports = []
    
    # Remove comments
    # Remove multi-line comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Remove single-line comments
    lines = []
    for line in content.split('\n'):
        if '//' in line:
            line = line.split('//')[0]
        lines.append(line)
    content = '\n'.join(lines)
    
    # Match 'import "package"' or 'import alias "package"'
    # Alias can be a word or dot (.)
    single_import_pattern = r'^\s*import\s+(?:[\w.]+\s+)?"([^"]+)"'
    
    # Match multi-line imports: import ( ... )
    multi_import_start = r'^\s*import\s+\('
    import_line_pattern = r'^\s*(?:[\w.]+\s+)?"([^"]+)"'
    
    in_import_block = False
    for line in content.split('\n'):
        # Check for single-line import
        if not in_import_block:
            match = re.match(single_import_pattern, line)
            if match:
                package = match.group(1)
                imports.append(package)
                continue
            
            # Check for start of multi-line import block
            if re.match(multi_import_start, line):
                in_import_block = True
                continue
        else:
            # We're inside an import block
            if ')' in line:
                in_import_block = False
                continue
            
            match = re.match(import_line_pattern, line)
            if match:
                package = match.group(1)
                imports.append(package)
    
    return imports


def _parse_java_imports(content: str, file_path: Path) -> List[str]:
    """
    Parse Java import statements to extract imported classes.
    
    Args:
        content: File content as string
        file_path: Path to the file being parsed
    
    Returns:
        List of imported class paths
    """
    imports = []
    
    # Remove comments
    # Remove multi-line comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Remove single-line comments
    lines = []
    for line in content.split('\n'):
        if '//' in line:
            line = line.split('//')[0]
        lines.append(line)
    content = '\n'.join(lines)
    
    # Match 'import package.Class;' or 'import static package.Class.method;'
    import_pattern = r'^\s*import\s+(?:static\s+)?([\w.]+)'
    
    for line in content.split('\n'):
        match = re.match(import_pattern, line)
        if match:
            class_path = match.group(1)
            imports.append(class_path)
    
    return imports


def _parse_csharp_imports(content: str, file_path: Path) -> List[str]:
    """
    Parse C# using statements to extract imported namespaces.
    
    Args:
        content: File content as string
        file_path: Path to the file being parsed
    
    Returns:
        List of imported namespace paths
    """
    imports = []
    
    # Remove comments
    # Remove multi-line comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Remove single-line comments
    lines = []
    for line in content.split('\n'):
        if '//' in line:
            line = line.split('//')[0]
        lines.append(line)
    content = '\n'.join(lines)
    
    # Match 'using Namespace;' or 'using Alias = Namespace;'
    using_pattern = r'^\s*using\s+(?:[\w]+\s*=\s*)?([\w.]+)'
    
    for line in content.split('\n'):
        match = re.match(using_pattern, line)
        if match:
            namespace = match.group(1)
            imports.append(namespace)
    
    return imports


def _parse_swift_imports(content: str, file_path: Path) -> List[str]:
    """
    Parse Swift import statements to extract imported modules.
    
    Args:
        content: File content as string
        file_path: Path to the file being parsed
    
    Returns:
        List of imported module paths
    """
    imports = []
    
    # Remove comments
    # Remove multi-line comments
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Remove single-line comments
    lines = []
    for line in content.split('\n'):
        if '//' in line:
            line = line.split('//')[0]
        lines.append(line)
    content = '\n'.join(lines)
    
    # Match 'import Module' or 'import kind Module' (e.g., 'import struct Foundation.URL')
    import_pattern = r'^\s*import\s+(?:(?:struct|class|enum|protocol|typealias|func|let|var)\s+)?([\w.]+)'
    
    for line in content.split('\n'):
        match = re.match(import_pattern, line)
        if match:
            module = match.group(1)
            imports.append(module)
    
    return imports


def _parse_html_css_references(content: str, file_path: Path) -> List[str]:
    """
    Parse HTML/CSS for local asset references (href, src attributes).
    
    Args:
        content: File content as string
        file_path: Path to the file being parsed
    
    Returns:
        List of local file references
    """
    references = []
    
    # For HTML: match href and src attributes with local paths
    # Pattern captures href="..." and src="..."
    html_ref_pattern = r'(?:href|src)\s*=\s*["\']([^"\']+)["\']'
    
    # For CSS: match url(...) references
    css_ref_pattern = r'url\s*\(\s*["\']?([^"\'()]+)["\']?\s*\)'
    
    for match in re.finditer(html_ref_pattern, content, re.IGNORECASE):
        ref = match.group(1)
        # Skip absolute URLs (http://, https://, //, etc.)
        if not ref.startswith(('http://', 'https://', '//', 'data:', 'mailto:', 'tel:', '#')):
            # Skip CDN and external references
            if not any(domain in ref for domain in ['cdn.', 'unpkg.', 'jsdelivr.', 'cloudflare.']):
                references.append(ref)
    
    for match in re.finditer(css_ref_pattern, content, re.IGNORECASE):
        ref = match.group(1)
        # Skip absolute URLs
        if not ref.startswith(('http://', 'https://', '//', 'data:')):
            if not any(domain in ref for domain in ['cdn.', 'unpkg.', 'jsdelivr.', 'cloudflare.']):
                references.append(ref)
    
    return references


def _parse_sql_includes(content: str, file_path: Path) -> List[str]:
    """
    Parse SQL for include/import statements and schema references.
    
    Args:
        content: File content as string
        file_path: Path to the file being parsed
    
    Returns:
        List of included file paths and schema references
    """
    includes = []
    
    # Remove SQL comments
    # Remove multi-line comments /* ... */
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    # Remove single-line comments --
    lines = []
    for line in content.split('\n'):
        if '--' in line:
            line = line.split('--')[0]
        lines.append(line)
    content = '\n'.join(lines)
    
    # Match various SQL include patterns (vendor-specific)
    # PostgreSQL: \i filename or \include filename
    psql_include_pattern = r'^\s*\\(?:i|include)\s+([^\s;]+)'
    
    # MySQL: SOURCE filename or \. filename
    mysql_include_pattern = r'^\s*(?:SOURCE|\\\.)\s+([^\s;]+)'
    
    # Generic: EXEC or EXECUTE with file path (SQL Server)
    exec_pattern = r'^\s*(?:EXEC|EXECUTE)\s+.*["\']([^"\']+\.sql)["\']'
    
    for line in content.split('\n'):
        # Check PostgreSQL includes
        match = re.match(psql_include_pattern, line, re.IGNORECASE)
        if match:
            includes.append(match.group(1))
            continue
        
        # Check MySQL includes
        match = re.match(mysql_include_pattern, line, re.IGNORECASE)
        if match:
            includes.append(match.group(1))
            continue
        
        # Check SQL Server exec patterns
        match = re.match(exec_pattern, line, re.IGNORECASE)
        if match:
            includes.append(match.group(1))
    
    return includes


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


def _resolve_c_cpp_include(
    include_path: str,
    source_file: Path,
    repo_root: Path
) -> Optional[Path]:
    """
    Resolve a C/C++ include to an actual file path within the repository.
    
    Args:
        include_path: Include string (e.g., 'myheader.h', 'subdir/header.hpp')
        source_file: Path to the file containing the include
        repo_root: Repository root directory
    
    Returns:
        Resolved Path or None if not found/external
    """
    # Skip system headers (angle brackets typically indicate system headers,
    # but we only have the path here, not the bracket type)
    # System headers are typically in standard locations and won't resolve in repo
    
    # Get the directory containing the source file
    source_dir = source_file.parent
    
    # Try relative to source file directory first (most common for quoted includes)
    relative_path = source_dir / include_path
    if relative_path.exists() and relative_path.is_file():
        try:
            relative_path.relative_to(repo_root)
            return relative_path
        except ValueError:
            return None
    
    # Try relative to repo root (for project-wide includes)
    repo_path = repo_root / include_path
    if repo_path.exists() and repo_path.is_file():
        return repo_path
    
    # Try common include directories
    for include_dir in ['include', 'src', 'lib', 'inc']:
        candidate = repo_root / include_dir / include_path
        if candidate.exists() and candidate.is_file():
            return candidate
    
    return None


def _resolve_rust_import(
    import_path: str,
    source_file: Path,
    repo_root: Path
) -> Optional[Path]:
    """
    Resolve a Rust use/mod statement to an actual file path within the repository.
    
    Args:
        import_path: Import string (e.g., 'crate::utils', 'std::io', 'mod_name')
        source_file: Path to the file containing the import
        repo_root: Repository root directory
    
    Returns:
        Resolved Path or None if not found/external
    """
    # Skip standard library and external crates
    if import_path.startswith('std::') or import_path.startswith('core::') or import_path.startswith('alloc::'):
        return None
    
    # Handle crate-relative imports (crate::)
    if import_path.startswith('crate::'):
        # Remove 'crate::' prefix and resolve from src/lib.rs or src/main.rs
        module_path = import_path[7:]  # Remove 'crate::'
        parts = module_path.split('::')
        
        # Try src/lib.rs location
        for root_file in ['src/lib.rs', 'src/main.rs']:
            root_path = repo_root / root_file
            if root_path.exists():
                # Navigate through module hierarchy
                current = repo_root / 'src'
                for part in parts:
                    # Try as file
                    candidate = current / f'{part}.rs'
                    if candidate.exists():
                        return candidate
                    # Try as directory with mod.rs
                    candidate = current / part / 'mod.rs'
                    if candidate.exists():
                        return candidate
                    current = current / part
        
        return None
    
    # Handle self:: and super::
    if import_path.startswith('self::') or import_path.startswith('super::'):
        return None
    
    # Handle simple mod statements (same directory)
    if '::' not in import_path:
        source_dir = source_file.parent
        # Try as sibling file
        candidate = source_dir / f'{import_path}.rs'
        if candidate.exists():
            return candidate
        # Try as subdirectory with mod.rs
        candidate = source_dir / import_path / 'mod.rs'
        if candidate.exists():
            return candidate
    
    return None


def _resolve_generic_import(
    import_path: str,
    source_file: Path,
    repo_root: Path,
    extensions: List[str]
) -> Optional[Path]:
    """
    Generic import resolver for languages where imports reference file paths.
    Used for Go, Java, C#, and Swift when they reference local project files.
    
    Args:
        import_path: Import string
        source_file: Path to the file containing the import
        repo_root: Repository root directory
        extensions: List of file extensions to try
    
    Returns:
        Resolved Path or None if not found/external
    """
    # For most compiled languages, imports reference package/module names,
    # not file paths, so intra-repo resolution is limited.
    # This function is primarily a placeholder for potential future enhancements.
    return None


def _resolve_html_css_reference(
    ref_path: str,
    source_file: Path,
    repo_root: Path
) -> Optional[Path]:
    """
    Resolve an HTML/CSS asset reference to an actual file path within the repository.
    
    Args:
        ref_path: Reference string (e.g., './style.css', '../images/logo.png')
        source_file: Path to the file containing the reference
        repo_root: Repository root directory
    
    Returns:
        Resolved Path or None if not found/external
    """
    # Get the directory containing the source file
    source_dir = source_file.parent
    
    # Resolve relative path
    if ref_path.startswith('./') or ref_path.startswith('../'):
        try:
            resolved = (source_dir / ref_path).resolve()
            # Check if it's within the repository
            resolved.relative_to(repo_root)
            if resolved.exists() and resolved.is_file():
                return resolved
        except (ValueError, OSError):
            return None
    elif not ref_path.startswith('/'):
        # Relative path without ./ prefix
        try:
            resolved = (source_dir / ref_path).resolve()
            resolved.relative_to(repo_root)
            if resolved.exists() and resolved.is_file():
                return resolved
        except (ValueError, OSError):
            return None
    elif ref_path.startswith('/'):
        # Absolute path from repo root
        try:
            resolved = (repo_root / ref_path.lstrip('/')).resolve()
            resolved.relative_to(repo_root)
            if resolved.exists() and resolved.is_file():
                return resolved
        except (ValueError, OSError):
            return None
    
    return None


def _resolve_sql_include(
    include_path: str,
    source_file: Path,
    repo_root: Path
) -> Optional[Path]:
    """
    Resolve a SQL include/import to an actual file path within the repository.
    
    Args:
        include_path: Include string (e.g., 'schema.sql', 'migrations/001.sql')
        source_file: Path to the file containing the include
        repo_root: Repository root directory
    
    Returns:
        Resolved Path or None if not found/external
    """
    # Get the directory containing the source file
    source_dir = source_file.parent
    
    # Try relative to source file directory
    relative_path = source_dir / include_path
    if relative_path.exists() and relative_path.is_file():
        try:
            relative_path.relative_to(repo_root)
            return relative_path
        except ValueError:
            return None
    
    # Try relative to repo root
    repo_path = repo_root / include_path
    if repo_path.exists() and repo_path.is_file():
        return repo_path
    
    # Try common SQL directories
    for sql_dir in ['sql', 'migrations', 'schemas', 'db']:
        candidate = repo_root / sql_dir / include_path
        if candidate.exists() and candidate.is_file():
            return candidate
    
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
    dependencies, _ = _scan_file_dependencies_with_external(file_path, repo_root)
    return dependencies


def _scan_file_dependencies_with_external(
    file_path: Path,
    repo_root: Path
) -> Tuple[List[Path], Dict[str, List[str]]]:
    """
    Scan a single file for dependencies and resolve them to file paths.
    Also categorize external (non-repo) imports as stdlib or third-party.
    
    Args:
        file_path: Path to the file to scan
        repo_root: Repository root directory
    
    Returns:
        Tuple of (resolved_dependencies, external_dependencies) where:
        - resolved_dependencies: List of resolved dependency file paths within the repo
        - external_dependencies: Dict with keys 'stdlib' and 'third-party', values are lists of module names
        
    Raises:
        IOError/OSError: If the file cannot be read
    """
    dependencies = []
    external_deps: Dict[str, List[str]] = {
        'stdlib': [],
        'third-party': []
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except (IOError, OSError) as e:
        # Re-raise the error so it can be caught and recorded in build_dependency_graph
        raise IOError(f"Cannot read file: {e}")
    
    # Determine file type and parse accordingly
    suffix = file_path.suffix.lower()
    language = None
    
    if suffix == '.py':
        language = 'Python'
        imports = _parse_python_imports(content, file_path)
        for import_path in imports:
            resolved = _resolve_python_import(import_path, file_path, repo_root)
            if resolved:
                # This is an intra-repo dependency
                dependencies.append(resolved)
            else:
                # This is an external dependency - classify it
                # Skip relative imports (they failed to resolve, but are internal references)
                if not import_path.startswith('.'):
                    dep_type = classify_import(import_path, language)
                    if dep_type == 'stdlib':
                        # Only add if not already present
                        if import_path not in external_deps['stdlib']:
                            external_deps['stdlib'].append(import_path)
                    elif dep_type == 'third-party':
                        if import_path not in external_deps['third-party']:
                            external_deps['third-party'].append(import_path)
    
    elif suffix in ['.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs']:
        # Determine language more precisely
        if suffix in ['.ts', '.tsx']:
            language = 'TypeScript'
        else:
            language = 'JavaScript'
        
        imports = _parse_js_imports(content, file_path)
        for import_path in imports:
            resolved = _resolve_js_import(import_path, file_path, repo_root)
            if resolved:
                # This is an intra-repo dependency
                dependencies.append(resolved)
            else:
                # This is an external dependency - classify it
                # Skip relative/absolute imports (they failed to resolve, but are file paths)
                if not import_path.startswith('.') and not import_path.startswith('/'):
                    dep_type = classify_import(import_path, language)
                    if dep_type == 'stdlib':
                        if import_path not in external_deps['stdlib']:
                            external_deps['stdlib'].append(import_path)
                    elif dep_type == 'third-party':
                        if import_path not in external_deps['third-party']:
                            external_deps['third-party'].append(import_path)
    
    elif suffix in ['.c', '.h']:
        language = 'C'
        includes = _parse_c_cpp_includes(content, file_path)
        for include_path in includes:
            resolved = _resolve_c_cpp_include(include_path, file_path, repo_root)
            if resolved:
                dependencies.append(resolved)
            else:
                # Classify as external
                dep_type = classify_import(include_path, language)
                if dep_type == 'stdlib':
                    if include_path not in external_deps['stdlib']:
                        external_deps['stdlib'].append(include_path)
                elif dep_type == 'third-party':
                    if include_path not in external_deps['third-party']:
                        external_deps['third-party'].append(include_path)
    
    elif suffix in ['.cpp', '.cc', '.cxx', '.hpp', '.hh', '.hxx']:
        language = 'C++'
        includes = _parse_c_cpp_includes(content, file_path)
        for include_path in includes:
            resolved = _resolve_c_cpp_include(include_path, file_path, repo_root)
            if resolved:
                dependencies.append(resolved)
            else:
                # Classify as external
                dep_type = classify_import(include_path, language)
                if dep_type == 'stdlib':
                    if include_path not in external_deps['stdlib']:
                        external_deps['stdlib'].append(include_path)
                elif dep_type == 'third-party':
                    if include_path not in external_deps['third-party']:
                        external_deps['third-party'].append(include_path)
    
    elif suffix == '.rs':
        language = 'Rust'
        imports = _parse_rust_imports(content, file_path)
        for import_path in imports:
            resolved = _resolve_rust_import(import_path, file_path, repo_root)
            if resolved:
                dependencies.append(resolved)
            else:
                # Classify as external (skip crate-relative imports)
                if not import_path.startswith('crate::') and not import_path.startswith('self::') and not import_path.startswith('super::'):
                    dep_type = classify_import(import_path, language)
                    if dep_type == 'stdlib':
                        if import_path not in external_deps['stdlib']:
                            external_deps['stdlib'].append(import_path)
                    elif dep_type == 'third-party':
                        if import_path not in external_deps['third-party']:
                            external_deps['third-party'].append(import_path)
    
    elif suffix == '.go':
        language = 'Go'
        imports = _parse_go_imports(content, file_path)
        for import_path in imports:
            # Go imports are package paths, not file paths
            # Intra-repo resolution is not straightforward without build context
            # For now, classify all as external
            dep_type = classify_import(import_path, language)
            if dep_type == 'stdlib':
                if import_path not in external_deps['stdlib']:
                    external_deps['stdlib'].append(import_path)
            elif dep_type == 'third-party':
                if import_path not in external_deps['third-party']:
                    external_deps['third-party'].append(import_path)
    
    elif suffix == '.java':
        language = 'Java'
        imports = _parse_java_imports(content, file_path)
        for import_path in imports:
            # Java imports are class paths, not file paths
            # Intra-repo resolution would require mapping packages to directories
            # For now, classify all as external
            dep_type = classify_import(import_path, language)
            if dep_type == 'stdlib':
                if import_path not in external_deps['stdlib']:
                    external_deps['stdlib'].append(import_path)
            elif dep_type == 'third-party':
                if import_path not in external_deps['third-party']:
                    external_deps['third-party'].append(import_path)
    
    elif suffix == '.cs':
        language = 'C#'
        imports = _parse_csharp_imports(content, file_path)
        for import_path in imports:
            # C# using statements reference namespaces, not file paths
            # Intra-repo resolution is not straightforward
            # For now, classify all as external
            dep_type = classify_import(import_path, language)
            if dep_type == 'stdlib':
                if import_path not in external_deps['stdlib']:
                    external_deps['stdlib'].append(import_path)
            elif dep_type == 'third-party':
                if import_path not in external_deps['third-party']:
                    external_deps['third-party'].append(import_path)
    
    elif suffix == '.swift':
        language = 'Swift'
        imports = _parse_swift_imports(content, file_path)
        for import_path in imports:
            # Swift imports are module names, not file paths
            # Intra-repo resolution would require understanding module structure
            # For now, classify all as external
            dep_type = classify_import(import_path, language)
            if dep_type == 'stdlib':
                if import_path not in external_deps['stdlib']:
                    external_deps['stdlib'].append(import_path)
            elif dep_type == 'third-party':
                if import_path not in external_deps['third-party']:
                    external_deps['third-party'].append(import_path)
    
    elif suffix in ['.html', '.htm']:
        language = 'HTML'
        references = _parse_html_css_references(content, file_path)
        for ref_path in references:
            resolved = _resolve_html_css_reference(ref_path, file_path, repo_root)
            if resolved:
                dependencies.append(resolved)
            # HTML/CSS references don't have external package dependencies to classify
    
    elif suffix == '.css':
        language = 'CSS'
        references = _parse_html_css_references(content, file_path)
        for ref_path in references:
            resolved = _resolve_html_css_reference(ref_path, file_path, repo_root)
            if resolved:
                dependencies.append(resolved)
            # CSS references don't have external package dependencies to classify
    
    elif suffix == '.sql':
        language = 'SQL'
        includes = _parse_sql_includes(content, file_path)
        for include_path in includes:
            resolved = _resolve_sql_include(include_path, file_path, repo_root)
            if resolved:
                dependencies.append(resolved)
            else:
                # Classify schema references
                dep_type = classify_import(include_path, language)
                if dep_type == 'stdlib':
                    if include_path not in external_deps['stdlib']:
                        external_deps['stdlib'].append(include_path)
                elif dep_type == 'third-party':
                    if include_path not in external_deps['third-party']:
                        external_deps['third-party'].append(include_path)
    
    return dependencies, external_deps


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
        Tuple of (graph_data, errors) where graph_data contains nodes, edges,
        and external dependencies, and errors is a list of error messages
    """
    from repo_analyzer.file_summary import scan_files, _get_language
    
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
    # Track external dependencies per file
    external_deps_map: Dict[Path, Dict[str, List[str]]] = {}
    # Normalize all files to absolute paths for consistent comparisons
    all_files: Set[Path] = {f.resolve() for f in files}
    
    for file_path in files:
        try:
            # Normalize file_path to absolute
            file_path_abs = file_path.resolve()
            deps, external_deps = _scan_file_dependencies_with_external(file_path_abs, root_path)
            dependency_map[file_path_abs] = deps
            external_deps_map[file_path_abs] = external_deps
        except Exception as e:
            try:
                rel = file_path.relative_to(root_path)
            except ValueError:
                rel = file_path
            errors.append(f"Error scanning {rel}: {e}")
            dependency_map[file_path.resolve()] = []
            external_deps_map[file_path.resolve()] = {'stdlib': [], 'third-party': []}
    
    # Build graph structure
    nodes = []
    edges = []
    
    # Aggregate external dependencies for summary
    all_stdlib_deps: Set[str] = set()
    all_third_party_deps: Set[str] = set()
    
    for file_path in sorted(all_files):
        try:
            rel_path = file_path.relative_to(root_path).as_posix()
        except ValueError:
            rel_path = str(file_path)
        
        # Get external dependencies for this file
        ext_deps = external_deps_map.get(file_path, {'stdlib': [], 'third-party': []})
        
        # Aggregate for summary stats
        all_stdlib_deps.update(ext_deps['stdlib'])
        all_third_party_deps.update(ext_deps['third-party'])
        
        # Add node with external dependency info
        node = {
            'id': rel_path,
            'path': rel_path,
            'type': 'file',
            'external_dependencies': {
                'stdlib': sorted(ext_deps['stdlib']),
                'third-party': sorted(ext_deps['third-party'])
            }
        }
        nodes.append(node)
    
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
        'edges': edges,
        'external_dependencies_summary': {
            'stdlib': sorted(list(all_stdlib_deps)),
            'third-party': sorted(list(all_third_party_deps)),
            'stdlib_count': len(all_stdlib_deps),
            'third-party_count': len(all_third_party_deps)
        }
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
        markdown_lines.append("Includes classification of external dependencies as stdlib vs third-party.\n")
        
        # Statistics
        markdown_lines.append("## Statistics\n")
        markdown_lines.append(f"- **Total files**: {len(graph_data['nodes'])}")
        markdown_lines.append(f"- **Intra-repo dependencies**: {len(graph_data['edges'])}")
        
        # External dependencies summary
        ext_summary = graph_data.get('external_dependencies_summary', {})
        if ext_summary:
            markdown_lines.append(f"- **External stdlib dependencies**: {ext_summary.get('stdlib_count', 0)}")
            markdown_lines.append(f"- **External third-party dependencies**: {ext_summary.get('third-party_count', 0)}")
        markdown_lines.append("")
        
        # External dependencies section
        if ext_summary:
            markdown_lines.append("## External Dependencies\n")
            
            stdlib_deps = ext_summary.get('stdlib', [])
            if stdlib_deps:
                markdown_lines.append("### Standard Library / Core Modules\n")
                markdown_lines.append(f"Total: {len(stdlib_deps)} unique modules\n")
                # Show first 20 in markdown, note if more
                for dep in stdlib_deps[:20]:
                    markdown_lines.append(f"- `{dep}`")
                if len(stdlib_deps) > 20:
                    markdown_lines.append(f"- ... and {len(stdlib_deps) - 20} more (see JSON for full list)")
                markdown_lines.append("")
            
            third_party_deps = ext_summary.get('third-party', [])
            if third_party_deps:
                markdown_lines.append("### Third-Party Packages\n")
                markdown_lines.append(f"Total: {len(third_party_deps)} unique packages\n")
                # Show first 20 in markdown, note if more
                for dep in third_party_deps[:20]:
                    markdown_lines.append(f"- `{dep}`")
                if len(third_party_deps) > 20:
                    markdown_lines.append(f"- ... and {len(third_party_deps) - 20} more (see JSON for full list)")
                markdown_lines.append("")
        
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
            markdown_lines.append("## Most Depended Upon Files (Intra-Repo)\n")
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
            markdown_lines.append("## Files with Most Dependencies (Intra-Repo)\n")
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
