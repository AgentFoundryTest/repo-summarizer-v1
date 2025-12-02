# Copyright (c) 2025 John Brosnihan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Repository file summary generator.

Analyzes source files to produce deterministic human- and machine-readable summaries
derived solely from filenames, extensions, and paths. No external calls or dynamic
code execution.

Schema Version: 2.0
- Version 1.0: Simple string summaries (legacy)
- Version 2.0: Structured summaries with role, metrics, structure, and dependencies
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Literal, Tuple

from repo_analyzer.language_registry import get_global_registry

# Schema version for structured summaries
SCHEMA_VERSION = "2.0"

# Detail levels for summary generation
DetailLevel = Literal["minimal", "standard", "detailed"]


# Language mapping based on file extensions
LANGUAGE_MAP = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript',
    '.jsx': 'JavaScript',
    '.java': 'Java',
    '.go': 'Go',
    '.rs': 'Rust',
    '.rb': 'Ruby',
    '.php': 'PHP',
    '.c': 'C',
    '.cpp': 'C++',
    '.cc': 'C++',
    '.cxx': 'C++',
    '.h': 'C/C++',
    '.hpp': 'C++',
    '.cs': 'C#',
    '.swift': 'Swift',
    '.kt': 'Kotlin',
    '.scala': 'Scala',
    '.sh': 'Shell',
    '.bash': 'Bash',
    '.zsh': 'Zsh',
    '.ps1': 'PowerShell',
    '.r': 'R',
    '.m': 'Objective-C',
    '.sql': 'SQL',
    '.html': 'HTML',
    '.css': 'CSS',
    '.scss': 'SCSS',
    '.sass': 'Sass',
    '.less': 'Less',
    '.vue': 'Vue',
    '.md': 'Markdown',
    '.rst': 'reStructuredText',
    '.yml': 'YAML',
    '.yaml': 'YAML',
    '.json': 'JSON',
    '.xml': 'XML',
    '.toml': 'TOML',
    '.ini': 'INI',
    '.cfg': 'Config',
    '.conf': 'Config',
}

# Compiled regex patterns for performance
_TODO_PATTERN = re.compile(r'\b(TODO|FIXME)\b', re.IGNORECASE)


class FileSummaryError(Exception):
    """Raised when file summary generation fails."""
    pass


def _count_lines_of_code(content: str) -> int:
    """
    Count non-empty, non-comment lines of code.
    
    This is a basic heuristic that counts lines that are not empty and do not
    start with common comment markers (# or //). It does not detect block comments
    (/* */, <!-- -->) or language-specific comment styles. This may slightly
    overcount LOC in files with extensive block comments.
    
    Args:
        content: File content as string
    
    Returns:
        Number of lines of code
    """
    lines = content.split('\n')
    loc = 0
    for line in lines:
        stripped = line.strip()
        # Skip empty lines and pure comment lines (basic heuristic)
        if stripped and not stripped.startswith('#') and not stripped.startswith('//'):
            loc += 1
    return loc


def _count_todos(content: str) -> int:
    """
    Count TODO and FIXME comments in file content.
    
    Args:
        content: File content as string
    
    Returns:
        Number of TODO/FIXME comments
    """
    # Use pre-compiled pattern for performance
    return len(_TODO_PATTERN.findall(content))


def _parse_python_declarations(content: str) -> Tuple[List[str], Optional[str]]:
    """
    Parse Python file to extract top-level function and class declarations.
    
    Uses Python's ast module for safe static analysis without code execution.
    
    Args:
        content: Python source code as string
    
    Returns:
        Tuple of (list of declaration names, error message if parsing failed)
    """
    declarations = []
    try:
        tree = ast.parse(content)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                declarations.append(f"function {node.name}")
            elif isinstance(node, ast.AsyncFunctionDef):
                declarations.append(f"async function {node.name}")
            elif isinstance(node, ast.ClassDef):
                declarations.append(f"class {node.name}")
        return declarations, None
    except SyntaxError as e:
        return [], f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return [], f"Parse error: {str(e)}"


def _parse_js_ts_exports(content: str) -> Tuple[List[str], Optional[str]]:
    """
    Parse JavaScript/TypeScript file to extract exported symbols.
    
    Uses deterministic regex patterns as a lightweight alternative to full parsing.
    This is a best-effort approach that may miss complex export patterns.
    
    Args:
        content: JavaScript/TypeScript source code as string
    
    Returns:
        Tuple of (list of export declarations, warning message if any)
    """
    exports = []
    
    # Pattern for: export default function/class Name
    default_named_pattern = re.compile(
        r'export\s+default\s+(?:async\s+)?(?:function|class)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)',
        re.MULTILINE
    )
    
    # Pattern for: export default Identifier (with optional semicolon)
    # Captures: export default MyComponent; or export default MyComponent
    # Use negative lookahead to avoid matching keywords (function, class, etc.)
    default_identifier_pattern = re.compile(
        r'export\s+default\s+(?!(?:async|function|class|interface|type|const|let|var)\b)([a-zA-Z_$][a-zA-Z0-9_$]*)',
        re.MULTILINE
    )
    
    # Pattern for: export function name() or export const name = or export class Name
    # Also handles TypeScript: export interface Name, export type Name
    # Use negative lookbehind to avoid matching "export default function/class Name"
    export_pattern = re.compile(
        r'export\s+(?!default\s)(?:async\s+)?(?:function|const|let|var|class|interface|type)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)',
        re.MULTILINE
    )
    
    # Pattern for: export default (without a name)
    default_export_pattern = re.compile(r'export\s+default\s+', re.MULTILINE)
    
    # Pattern for: export { a, b, c }
    export_list_pattern = re.compile(r'export\s+\{([^}]+)\}', re.MULTILINE)
    
    # Find default exports with names (e.g., export default function Foo)
    for match in default_named_pattern.finditer(content):
        name = match.group(1)
        exports.append(f"export default {name}")
    
    # Find default identifier exports (e.g., export default MyComponent;)
    for match in default_identifier_pattern.finditer(content):
        name = match.group(1)
        # Only add if we haven't already captured this as a named function/class default
        if f"export default {name}" not in exports:
            exports.append(f"export default {name}")
    
    # Find named exports (including TypeScript interface/type)
    for match in export_pattern.finditer(content):
        name = match.group(1)
        exports.append(f"export {name}")
    
    # Check for anonymous default export (only if no named default found)
    # Named default exports have the format "export default Name" (3 parts)
    has_default = default_export_pattern.search(content)
    has_named_default = any(
        len(e.split()) == 3 and e.split()[0] == 'export' and e.split()[1] == 'default'
        for e in exports
    )
    if has_default and not has_named_default:
        exports.append("export default")
    
    # Find export lists - build set of existing names for efficient lookup
    # Extract just the name part from exports (skip "export default" pattern)
    existing_names = set()
    for e in exports:
        parts = e.split()
        if len(parts) > 1 and parts[1] != 'default':
            existing_names.add(parts[1])
        elif len(parts) > 2:  # "export default Name"
            existing_names.add(parts[2])
    if has_default or has_named_default:
        existing_names.add('default')
    
    for match in export_list_pattern.finditer(content):
        export_list = match.group(1)
        # Split by comma and clean up
        for item in export_list.split(','):
            stripped = item.strip()
            if not stripped:
                continue
            # Handle "name as alias" exports - use the alias (what's exported)
            parts = stripped.split()
            if parts:
                # If "as" is present, take the name after it (the alias)
                if len(parts) >= 3 and parts[1].lower() == 'as':
                    name = parts[2]
                else:
                    # No alias, use the original name
                    name = parts[0]
                # Ensure name is valid identifier and not already exported
                if name and name not in existing_names:
                    exports.append(f"export {name}")
                    existing_names.add(name)
    
    warning = None
    if not exports and ('export' in content or 'module.exports' in content):
        warning = "File contains exports but pattern matching may have missed some"
    
    return exports, warning


def _matches_pattern(path: str, patterns: List[str]) -> bool:
    """
    Check if a path matches any of the given glob patterns.
    
    Uses Path.match for proper glob semantics, supporting wildcards like:
    - *.py (files ending in .py)
    - test_* (files starting with test_)
    - tests/*.py (Python files in tests directory)
    - tests/**/*.py (Python files anywhere under tests)
    - foo?.js (single-character wildcard)
    
    Args:
        path: File path (relative or just filename) to check
        patterns: List of glob-style patterns
    
    Returns:
        True if path matches any pattern, False otherwise
    """
    from pathlib import PurePosixPath
    
    # Convert to PurePosixPath for consistent matching across platforms
    path_obj = PurePosixPath(path)
    
    for pattern in patterns:
        # Use Path.match for proper glob semantics including ** support
        if path_obj.match(pattern):
            return True
    
    return False


def _get_language(file_path: Path) -> str:
    """
    Detect language from file extension using the language registry.
    
    Falls back to legacy LANGUAGE_MAP for backward compatibility.
    
    Args:
        file_path: Path to the file
    
    Returns:
        Language name or 'Unknown'
    """
    extension = file_path.suffix.lower()
    
    # Try registry first
    registry = get_global_registry()
    language = registry.get_language_by_extension(extension)
    if language:
        return language
    
    # Fall back to legacy map for any missing mappings
    return LANGUAGE_MAP.get(extension, 'Unknown')


def _detect_file_role(file_path: Path, root_path: Path) -> Tuple[str, str]:
    """
    Detect the role/purpose of a file based on its name and path.
    
    Args:
        file_path: Path to the file
        root_path: Root path of the repository
    
    Returns:
        Tuple of (role string, justification string)
    """
    name = file_path.stem
    name_lower = name.lower()
    extension = file_path.suffix.lower()
    
    # Get relative path for context
    try:
        rel_path = file_path.relative_to(root_path)
        path_parts = list(rel_path.parent.parts)
    except ValueError:
        path_parts = []
    
    # Test files
    if name_lower.startswith('test_'):
        return "test", f"filename starts with 'test_'"
    if name_lower.endswith('_test'):
        return "test", f"filename ends with '_test'"
    # Only match "test" as exact name, not as prefix to avoid false positives like "testament.py"
    if name_lower == 'test':
        return "test", f"filename is 'test'"
    if path_parts and path_parts[0].lower() in ['tests', 'test']:
        return "test", f"located in '{path_parts[0]}' directory"
    
    # Entry point files
    if name_lower in ['main', 'index', 'app', '__main__']:
        return "entry-point", f"common entry point name '{name_lower}'"
    
    # Configuration files
    if name_lower in ['config', 'configuration', 'settings']:
        return "configuration", f"configuration file name '{name_lower}'"
    if extension in ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf']:
        return "configuration", f"configuration file extension '{extension}'"
    
    # CLI files
    if name_lower in ['cli', 'command', 'commands']:
        return "cli", f"CLI-related name '{name_lower}'"
    
    # Utility files
    if name_lower in ['utils', 'util', 'utilities', 'helpers', 'helper']:
        return "utility", f"utility/helper name '{name_lower}'"
    
    # Model/schema files
    if name_lower in ['model', 'models', 'schema', 'schemas']:
        return "model", f"model/schema name '{name_lower}'"
    
    # Controller/handler files
    if name_lower in ['controller', 'controllers', 'handler', 'handlers']:
        return "controller", f"controller/handler name '{name_lower}'"
    
    # View/template files
    if name_lower in ['view', 'views', 'template', 'templates']:
        return "view", f"view/template name '{name_lower}'"
    
    # Service layer files
    if name_lower in ['service', 'services']:
        return "service", f"service layer name '{name_lower}'"
    
    # Data access layer
    if name_lower in ['repository', 'repositories', 'dao']:
        return "data-access", f"data access name '{name_lower}'"
    
    # API files
    if 'api' in name_lower:
        return "api", f"filename contains 'api'"
    
    # Database files
    if 'db' in name_lower or 'database' in name_lower:
        return "database", f"filename contains database-related term"
    
    # Router files
    if 'router' in name_lower or 'routes' in name_lower:
        return "router", f"filename contains routing term"
    
    # Middleware files
    if 'middleware' in name_lower:
        return "middleware", f"filename contains 'middleware'"
    
    # Component files (for JS/TS frameworks)
    if extension in ['.jsx', '.tsx', '.vue']:
        return "component", f"component file extension '{extension}'"
    if 'component' in name_lower:
        return "component", f"filename contains 'component'"
    
    # Module initialization
    if name_lower in ['__init__', 'mod']:
        return "module-init", f"module initialization file '{name_lower}'"
    
    # Documentation
    if extension in ['.md', '.rst']:
        return "documentation", f"documentation file extension '{extension}'"
    if path_parts and path_parts[0].lower() in ['docs', 'documentation']:
        return "documentation", f"located in '{path_parts[0]}' directory"
    
    # Scripts
    if path_parts and path_parts[0].lower() in ['scripts', 'bin']:
        return "script", f"located in '{path_parts[0]}' directory"
    
    # Examples
    if path_parts and path_parts[0].lower() in ['examples', 'demos', 'samples']:
        return "example", f"located in '{path_parts[0]}' directory"
    
    # Default to "implementation"
    return "implementation", "general implementation file (default classification)"


def _generate_heuristic_summary(file_path: Path, root_path: Path) -> str:
    """
    Generate a deterministic summary based on filename, path, and extension.
    
    Args:
        file_path: Path to the file
        root_path: Root path of the repository
    
    Returns:
        Summary string
    """
    name = file_path.stem
    extension = file_path.suffix.lower()
    language = _get_language(file_path)
    
    # Get relative path for context
    try:
        rel_path = file_path.relative_to(root_path)
        path_parts = list(rel_path.parent.parts)
    except ValueError:
        path_parts = []
    
    # Heuristics based on filename patterns
    name_lower = name.lower()
    
    # Configuration files
    if name_lower in ['config', 'configuration', 'settings']:
        return f"{language} configuration file"
    
    # Test files
    if name_lower.startswith('test_') or name_lower.endswith('_test'):
        return f"{language} test file"
    # Only match "test" as exact name to avoid false positives
    if name_lower == 'test':
        return f"{language} test file"
    
    # Main/entry point files
    if name_lower in ['main', 'index', 'app', '__main__']:
        return f"{language} main entry point"
    
    # CLI files
    if name_lower in ['cli', 'command', 'commands']:
        return f"{language} command-line interface"
    
    # Utility/helper files
    if name_lower in ['utils', 'util', 'utilities', 'helpers', 'helper']:
        return f"{language} utility functions"
    
    # Model files
    if name_lower in ['model', 'models', 'schema', 'schemas']:
        return f"{language} data models"
    
    # Controller/handler files
    if name_lower in ['controller', 'controllers', 'handler', 'handlers']:
        return f"{language} request handlers"
    
    # View/template files
    if name_lower in ['view', 'views', 'template', 'templates']:
        return f"{language} view templates"
    
    # Service files
    if name_lower in ['service', 'services']:
        return f"{language} service layer"
    
    # Repository/DAO files
    if name_lower in ['repository', 'repositories', 'dao']:
        return f"{language} data access layer"
    
    # API files
    if 'api' in name_lower:
        return f"{language} API implementation"
    
    # Database files
    if 'db' in name_lower or 'database' in name_lower:
        return f"{language} database operations"
    
    # Router files
    if 'router' in name_lower or 'routes' in name_lower:
        return f"{language} routing configuration"
    
    # Middleware files
    if 'middleware' in name_lower:
        return f"{language} middleware component"
    
    # Component files (for JS/TS frameworks)
    if extension in ['.jsx', '.tsx', '.vue'] or 'component' in name_lower:
        return f"{language} UI component"
    
    # Package/module initialization
    if name_lower in ['__init__', 'index', 'mod']:
        if 'tests' in path_parts or 'test' in path_parts:
            return f"{language} test module initialization"
        return f"{language} module initialization"
    
    # Path-based heuristics
    if path_parts:
        top_dir = path_parts[0].lower()
        
        if top_dir in ['tests', 'test']:
            return f"{language} test implementation"
        elif top_dir in ['src', 'lib', 'core']:
            return f"{language} core implementation"
        elif top_dir in ['scripts', 'bin']:
            return f"{language} utility script"
        elif top_dir in ['docs', 'documentation']:
            return f"{language} documentation file"
        elif top_dir in ['examples', 'demos', 'samples']:
            return f"{language} example code"
    
    # Default: descriptive summary based on language and name
    # Convert snake_case or kebab-case to words
    words = name.replace('_', ' ').replace('-', ' ')
    
    if language != 'Unknown':
        return f"{language} module for {words}"
    else:
        return f"Source file for {words}"


def _create_structured_summary(
    file_path: Path,
    root_path: Path,
    detail_level: DetailLevel = "standard",
    include_legacy: bool = True,
    max_file_size_kb: int = 1024
) -> Dict[str, Any]:
    """
    Create a structured summary for a file with metadata.
    
    Args:
        file_path: Path to the file
        root_path: Root path of the repository
        detail_level: Level of detail ("minimal", "standard", "detailed")
        include_legacy: Whether to include legacy summary field
        max_file_size_kb: Maximum file size in KB for expensive parsing (default 1024)
    
    Returns:
        Dictionary with structured summary data
    """
    try:
        rel_path = file_path.relative_to(root_path)
    except ValueError:
        rel_path = file_path
    
    language = _get_language(file_path)
    role, role_justification = _detect_file_role(file_path, root_path)
    
    # Build the structured summary with deterministic key ordering
    summary = {
        "schema_version": SCHEMA_VERSION,
        "path": str(rel_path.as_posix()),
        "language": language,
        "role": role,
        "role_justification": role_justification,
    }
    
    # Read file content for analysis (if needed)
    content = None
    file_too_large = False
    parse_error = None
    
    try:
        file_size = file_path.stat().st_size
        file_size_kb = file_size / 1024
        
        # Skip expensive parsing for large files, but still read for basic metrics
        if file_size_kb > max_file_size_kb:
            file_too_large = True
            # For large files, still read content for LOC/TODO if at standard/detailed level
            # but skip declaration parsing
            if detail_level in ["standard", "detailed"]:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except (OSError, IOError) as e:
                    parse_error = f"Failed to read file: {str(e)}"
        else:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except (OSError, IOError) as e:
                parse_error = f"Failed to read file: {str(e)}"
    except (OSError, IOError):
        file_size = 0
    
    # Parse structure first if at detailed level (needed for enhanced summaries)
    declarations = []
    structure_warning = None
    
    if detail_level == "detailed":
        if file_too_large:
            structure_warning = f"File exceeds {max_file_size_kb}KB limit, skipping expensive parsing"
        elif parse_error:
            structure_warning = parse_error
        elif content is not None:
            # Parse declarations based on language
            if language == "Python":
                declarations, error = _parse_python_declarations(content)
                if error:
                    structure_warning = error
            elif language in ["JavaScript", "TypeScript"]:
                declarations, warning = _parse_js_ts_exports(content)
                if warning:
                    structure_warning = warning
            else:
                structure_warning = f"No parser available for {language}"
    
    # Add legacy summary field for backward compatibility
    if include_legacy:
        # Generate enhanced summary that includes structure info when available
        base_summary = _generate_heuristic_summary(file_path, root_path)
        
        # Enhance summary with role and structure information
        summary_parts = [base_summary]
        
        if role != "implementation":
            summary_parts.append(f"(role: {role})")
        
        # Add structure information if available (detailed level with declarations)
        if detail_level == "detailed" and declarations:
            if len(declarations) <= 3:
                # Show all declarations if 3 or fewer
                decl_summary = ", ".join(declarations)
            else:
                # Show first 3 and indicate there are more
                decl_summary = ", ".join(declarations[:3]) + f", +{len(declarations) - 3} more"
            summary_parts.append(f"[{decl_summary}]")
        
        summary["summary"] = " ".join(summary_parts)
        # Also add as summary_text for additional compatibility
        summary["summary_text"] = summary["summary"]
    
    # Add metrics based on detail level
    if detail_level in ["standard", "detailed"]:
        metrics = {
            "size_bytes": file_size,
        }
        
        # Add LOC and TODO counts if we have content
        if content is not None:
            metrics["loc"] = _count_lines_of_code(content)
            metrics["todo_count"] = _count_todos(content)
        
        summary["metrics"] = metrics
    
    # Add structure field for detailed level
    if detail_level == "detailed":
        summary["structure"] = {
            "declarations": declarations,
        }
        
        if structure_warning:
            summary["structure"]["warning"] = structure_warning
        
        # Add declaration count to metrics if available
        if declarations and "metrics" in summary:
            summary["metrics"]["declaration_count"] = len(declarations)
    
    # Add dependencies field for detailed level
    if detail_level == "detailed":
        # Get external dependencies for this file
        from repo_analyzer.dependency_graph import _scan_file_dependencies_with_external
        
        external_deps = {'stdlib': [], 'third-party': []}
        
        # Only scan supported file types
        if language in ['Python', 'JavaScript', 'TypeScript']:
            try:
                _, external_deps = _scan_file_dependencies_with_external(file_path, root_path)
            except (IOError, OSError):
                # If we can't read the file, leave dependencies empty
                pass
        
        summary["dependencies"] = {
            "imports": [],  # Placeholder for future enhancement (would list all imports)
            "exports": [],  # Placeholder for future enhancement (would list all exports)
            "external": {
                "stdlib": sorted(external_deps.get('stdlib', [])),
                "third-party": sorted(external_deps.get('third-party', []))
            }
        }
    
    return summary


def scan_files(
    root_path: Path,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    exclude_dirs: Optional[Set[str]] = None
) -> List[Path]:
    """
    Scan directory for files matching include patterns and not matching exclude patterns.
    
    Args:
        root_path: Root directory to scan
        include_patterns: List of patterns to include (e.g., ['*.py', '*.js'])
        exclude_patterns: List of patterns to exclude (e.g., ['*.pyc', '*_test.py'])
        exclude_dirs: Set of directory names to skip
    
    Returns:
        List of file paths matching the criteria
    """
    if include_patterns is None:
        include_patterns = []
    if exclude_patterns is None:
        exclude_patterns = []
    if exclude_dirs is None:
        exclude_dirs = set()
    
    matching_files = []
    
    for dirpath, dirnames, filenames in os.walk(root_path, followlinks=False):
        # Get relative directory path for pattern matching
        try:
            rel_dirpath = Path(dirpath).relative_to(root_path).as_posix()
        except ValueError:
            rel_dirpath = ""
        
        # Check if current directory should be excluded based on patterns
        if rel_dirpath and exclude_patterns:
            # Check if the directory path itself matches any exclude pattern
            # Also check with trailing /* to catch directory-based patterns
            if (_matches_pattern(rel_dirpath, exclude_patterns) or 
                _matches_pattern(rel_dirpath + '/*', exclude_patterns)):
                # Skip this entire directory tree
                dirnames[:] = []
                continue
        
        # Filter out excluded directories (modifies dirnames in-place)
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        
        # Filter out hidden directories (starting with .)
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        
        # Also filter symlinked directories
        dirnames[:] = [d for d in dirnames if not (Path(dirpath) / d).is_symlink()]
        
        for filename in sorted(filenames):
            file_path = Path(dirpath) / filename
            
            # Skip symlinks
            if file_path.is_symlink():
                continue
            
            # Get relative path for pattern matching (use POSIX style for consistency)
            try:
                rel_path = file_path.relative_to(root_path).as_posix()
            except ValueError:
                # If file is not relative to root_path, use the filename
                rel_path = filename
            
            # Check include patterns (if any)
            # Try matching both the relative path and just the filename for flexibility
            if include_patterns:
                matches = _matches_pattern(rel_path, include_patterns) or _matches_pattern(filename, include_patterns)
                if not matches:
                    continue
            
            # Check exclude patterns
            if exclude_patterns:
                excludes = _matches_pattern(rel_path, exclude_patterns) or _matches_pattern(filename, exclude_patterns)
                if excludes:
                    continue
            
            matching_files.append(file_path)
    
    # Sort for deterministic ordering
    return sorted(matching_files)


def generate_file_summaries(
    root_path: Path,
    output_dir: Path,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    exclude_dirs: Optional[Set[str]] = None,
    dry_run: bool = False,
    detail_level: DetailLevel = "standard",
    include_legacy_summary: bool = True,
    max_file_size_kb: int = 1024
) -> None:
    """
    Generate file summaries in Markdown and JSON formats.
    
    Args:
        root_path: Root directory to scan
        output_dir: Directory to write output files
        include_patterns: List of patterns to include (e.g., ['*.py', '*.js'])
        exclude_patterns: List of patterns to exclude (e.g., ['*.pyc', 'test_*'])
        exclude_dirs: Set of directory names to skip
        dry_run: If True, only log intent without writing files
        detail_level: Level of detail ("minimal", "standard", "detailed")
        include_legacy_summary: Whether to include legacy summary field for backward compatibility
        max_file_size_kb: Maximum file size in KB for expensive parsing (default 1024)
    
    Raises:
        FileSummaryError: If file summary generation fails
    """
    try:
        # Scan for matching files
        files = scan_files(root_path, include_patterns, exclude_patterns, exclude_dirs)
        
        if not files:
            if dry_run:
                print("[DRY RUN] No files found matching criteria")
            else:
                print("No files found matching criteria")
            return
        
        # Generate structured summaries for each file
        summaries = []
        for file_path in files:
            structured_summary = _create_structured_summary(
                file_path,
                root_path,
                detail_level=detail_level,
                include_legacy=include_legacy_summary,
                max_file_size_kb=max_file_size_kb
            )
            summaries.append(structured_summary)
        
        # Generate Markdown output
        markdown_lines = ["# File Summaries\n"]
        markdown_lines.append("Heuristic summaries of source files based on filenames, extensions, and paths.\n")
        markdown_lines.append(f"Schema Version: {SCHEMA_VERSION}\n")
        markdown_lines.append(f"Total files: {len(summaries)}\n")
        
        for entry in summaries:
            markdown_lines.append(f"## {entry['path']}")
            markdown_lines.append(f"**Language:** {entry['language']}  ")
            markdown_lines.append(f"**Role:** {entry['role']}  ")
            markdown_lines.append(f"**Role Justification:** {entry['role_justification']}  ")
            
            # Include legacy summary if present
            if 'summary' in entry:
                markdown_lines.append(f"**Summary:** {entry['summary']}  ")
            
            # Add metrics if present
            if 'metrics' in entry:
                metrics = entry['metrics']
                size_kb = metrics['size_bytes'] / 1024
                markdown_lines.append(f"**Size:** {size_kb:.2f} KB  ")
                
                if 'loc' in metrics:
                    markdown_lines.append(f"**LOC:** {metrics['loc']}  ")
                
                if 'todo_count' in metrics:
                    markdown_lines.append(f"**TODOs/FIXMEs:** {metrics['todo_count']}  ")
                
                if 'declaration_count' in metrics:
                    markdown_lines.append(f"**Declarations:** {metrics['declaration_count']}  ")
            
            # Add structure information if present
            if 'structure' in entry:
                # Show declarations if present
                if entry['structure'].get('declarations'):
                    markdown_lines.append(f"**Top-level declarations:**")
                    for decl in entry['structure']['declarations'][:10]:  # Limit to 10
                        markdown_lines.append(f"  - {decl}")
                    if len(entry['structure']['declarations']) > 10:
                        markdown_lines.append(f"  - ... and {len(entry['structure']['declarations']) - 10} more")
                
                # Always show warning if present, even without declarations
                if 'warning' in entry['structure']:
                    markdown_lines.append(f"**Warning:** {entry['structure']['warning']}  ")
            
            # Add external dependencies if present
            if 'dependencies' in entry and 'external' in entry['dependencies']:
                external = entry['dependencies']['external']
                stdlib_deps = external.get('stdlib', [])
                third_party_deps = external.get('third-party', [])
                
                if stdlib_deps or third_party_deps:
                    markdown_lines.append(f"**External Dependencies:**")
                    
                    if stdlib_deps:
                        markdown_lines.append(f"  - **Stdlib:** {', '.join(f'`{d}`' for d in stdlib_deps[:5])}")
                        if len(stdlib_deps) > 5:
                            markdown_lines.append(f"    _(and {len(stdlib_deps) - 5} more)_")
                    
                    if third_party_deps:
                        markdown_lines.append(f"  - **Third-party:** {', '.join(f'`{d}`' for d in third_party_deps[:5])}")
                        if len(third_party_deps) > 5:
                            markdown_lines.append(f"    _(and {len(third_party_deps) - 5} more)_")
            
            markdown_lines.append("")  # Empty line between entries
        
        markdown_content = "\n".join(markdown_lines)
        markdown_path = output_dir / "file-summaries.md"
        
        if dry_run:
            print(f"[DRY RUN] Would write file-summaries.md to: {markdown_path}")
            print(f"[DRY RUN] Content length: {len(markdown_content)} bytes")
            print(f"[DRY RUN] Total files: {len(summaries)}")
        else:
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"File summaries written: {markdown_path}")
        
        # Generate JSON output with stable ordering
        json_data = {
            'schema_version': SCHEMA_VERSION,
            'total_files': len(summaries),
            'files': summaries
        }
        json_path = output_dir / "file-summaries.json"
        
        if dry_run:
            print(f"[DRY RUN] Would write file-summaries.json to: {json_path}")
            print(f"[DRY RUN] JSON entries: {len(summaries)}")
        else:
            with open(json_path, 'w', encoding='utf-8') as f:
                # Use indent=2 for readability and sort_keys=False to maintain insertion order
                json.dump(json_data, f, indent=2, sort_keys=False)
            print(f"File summaries JSON written: {json_path}")
    
    except Exception as e:
        raise FileSummaryError(f"Failed to generate file summaries: {e}")
