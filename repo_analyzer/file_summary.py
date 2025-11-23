"""
Repository file summary generator.

Analyzes source files to produce deterministic human- and machine-readable summaries
derived solely from filenames, extensions, and paths. No external calls or dynamic
code execution.

Schema Version: 2.0
- Version 1.0: Simple string summaries (legacy)
- Version 2.0: Structured summaries with role, metrics, structure, and dependencies
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Literal

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


class FileSummaryError(Exception):
    """Raised when file summary generation fails."""
    pass


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
    Detect language from file extension.
    
    Args:
        file_path: Path to the file
    
    Returns:
        Language name or 'Unknown'
    """
    extension = file_path.suffix.lower()
    return LANGUAGE_MAP.get(extension, 'Unknown')


def _detect_file_role(file_path: Path, root_path: Path) -> str:
    """
    Detect the role/purpose of a file based on its name and path.
    
    Args:
        file_path: Path to the file
        root_path: Root path of the repository
    
    Returns:
        Role string (e.g., "entry-point", "test", "configuration", "utility", "model")
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
    if name_lower.startswith('test_') or name_lower.endswith('_test'):
        return "test"
    # Only match "test" as exact name, not as prefix to avoid false positives like "testament.py"
    if name_lower == 'test':
        return "test"
    if path_parts and path_parts[0].lower() in ['tests', 'test']:
        return "test"
    
    # Entry point files
    if name_lower in ['main', 'index', 'app', '__main__']:
        return "entry-point"
    
    # Configuration files
    if name_lower in ['config', 'configuration', 'settings']:
        return "configuration"
    if extension in ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf']:
        return "configuration"
    
    # CLI files
    if name_lower in ['cli', 'command', 'commands']:
        return "cli"
    
    # Utility files
    if name_lower in ['utils', 'util', 'utilities', 'helpers', 'helper']:
        return "utility"
    
    # Model/schema files
    if name_lower in ['model', 'models', 'schema', 'schemas']:
        return "model"
    
    # Controller/handler files
    if name_lower in ['controller', 'controllers', 'handler', 'handlers']:
        return "controller"
    
    # View/template files
    if name_lower in ['view', 'views', 'template', 'templates']:
        return "view"
    
    # Service layer files
    if name_lower in ['service', 'services']:
        return "service"
    
    # Data access layer
    if name_lower in ['repository', 'repositories', 'dao']:
        return "data-access"
    
    # API files
    if 'api' in name_lower:
        return "api"
    
    # Database files
    if 'db' in name_lower or 'database' in name_lower:
        return "database"
    
    # Router files
    if 'router' in name_lower or 'routes' in name_lower:
        return "router"
    
    # Middleware files
    if 'middleware' in name_lower:
        return "middleware"
    
    # Component files (for JS/TS frameworks)
    if extension in ['.jsx', '.tsx', '.vue'] or 'component' in name_lower:
        return "component"
    
    # Module initialization
    if name_lower in ['__init__', 'mod']:
        return "module-init"
    
    # Documentation
    if extension in ['.md', '.rst'] or (path_parts and path_parts[0].lower() in ['docs', 'documentation']):
        return "documentation"
    
    # Scripts
    if path_parts and path_parts[0].lower() in ['scripts', 'bin']:
        return "script"
    
    # Examples
    if path_parts and path_parts[0].lower() in ['examples', 'demos', 'samples']:
        return "example"
    
    # Default to "implementation"
    return "implementation"


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
    include_legacy: bool = True
) -> Dict[str, Any]:
    """
    Create a structured summary for a file with metadata.
    
    Args:
        file_path: Path to the file
        root_path: Root path of the repository
        detail_level: Level of detail ("minimal", "standard", "detailed")
        include_legacy: Whether to include legacy summary field
    
    Returns:
        Dictionary with structured summary data
    """
    try:
        rel_path = file_path.relative_to(root_path)
    except ValueError:
        rel_path = file_path
    
    language = _get_language(file_path)
    role = _detect_file_role(file_path, root_path)
    
    # Build the structured summary with deterministic key ordering
    summary = {
        "schema_version": SCHEMA_VERSION,
        "path": str(rel_path.as_posix()),
        "language": language,
        "role": role,
    }
    
    # Add legacy summary field for backward compatibility
    if include_legacy:
        summary["summary"] = _generate_heuristic_summary(file_path, root_path)
        # Also add as summary_text for additional compatibility
        summary["summary_text"] = summary["summary"]
    
    # Add metrics based on detail level
    if detail_level in ["standard", "detailed"]:
        try:
            file_size = file_path.stat().st_size
            summary["metrics"] = {
                "size_bytes": file_size,
            }
        except (OSError, IOError):
            summary["metrics"] = {
                "size_bytes": 0,
            }
    
    # Add structure field for detailed level
    if detail_level == "detailed":
        # For now, structure is placeholder - could be extended to detect
        # top-level declarations (functions, classes, exports) via static analysis
        summary["structure"] = {
            "declarations": [],  # Empty for heuristic-only implementation
        }
    
    # Add dependencies field for detailed level
    if detail_level == "detailed":
        # Placeholder for dependency information
        # This could reference the dependency graph results
        summary["dependencies"] = {
            "imports": [],  # Empty for heuristic-only implementation
            "exports": [],  # Empty for heuristic-only implementation
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
    include_legacy_summary: bool = True
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
                include_legacy=include_legacy_summary
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
            
            # Include legacy summary if present
            if 'summary' in entry:
                markdown_lines.append(f"**Summary:** {entry['summary']}  ")
            
            # Add metrics if present
            if 'metrics' in entry:
                metrics = entry['metrics']
                size_kb = metrics['size_bytes'] / 1024
                markdown_lines.append(f"**Size:** {size_kb:.2f} KB  ")
            
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
