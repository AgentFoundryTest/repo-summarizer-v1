"""
Repository tree report generator.

Walks the repository filesystem and produces deterministic tree reports
in both Markdown and JSON formats, excluding noise directories and
respecting configured exclude patterns.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Set


# Default directories to exclude (noise directories)
DEFAULT_EXCLUDES = {
    '.git',
    'node_modules',
    '.venv',
    'venv',
    'build',
    '__pycache__',
}


class TreeReportError(Exception):
    """Raised when tree report generation fails."""
    pass


def _should_exclude(name: str, exclude_patterns: Set[str]) -> bool:
    """
    Check if a file or directory should be excluded.
    
    Args:
        name: File or directory name
        exclude_patterns: Set of patterns to exclude
    
    Returns:
        True if should be excluded, False otherwise
    """
    # Exact name match
    if name in exclude_patterns:
        return True
    
    # Wildcard pattern matching (simple glob-style)
    for pattern in exclude_patterns:
        if '*' in pattern:
            # Simple glob matching (e.g., *.pyc)
            if pattern.startswith('*'):
                suffix = pattern[1:]
                if name.endswith(suffix):
                    return True
            elif pattern.endswith('*'):
                prefix = pattern[:-1]
                if name.startswith(prefix):
                    return True
    
    return False


def _build_tree_structure(
    root_path: Path,
    exclude_patterns: Set[str],
    max_depth: Optional[int] = None,
    current_depth: int = 0
) -> Dict[str, Any]:
    """
    Build a tree structure as a nested dictionary.
    
    Args:
        root_path: Root directory to scan
        exclude_patterns: Set of patterns to exclude
        max_depth: Maximum depth to traverse (None for unlimited)
        current_depth: Current recursion depth
    
    Returns:
        Dictionary representing the tree structure
    """
    if not root_path.is_dir():
        raise TreeReportError(f"Path is not a directory: {root_path}")
    
    # Check if we've reached max depth
    if max_depth is not None and current_depth >= max_depth:
        return {"type": "directory", "name": root_path.name, "children": []}
    
    tree = {
        "type": "directory",
        "name": root_path.name if root_path.name else root_path.as_posix(),
        "children": []
    }
    
    try:
        # Get all entries and sort them for deterministic ordering
        entries = sorted(root_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        
        for entry in entries:
            # Skip excluded items
            if _should_exclude(entry.name, exclude_patterns):
                continue
            
            # Skip symlinks to avoid escaping the repository
            if entry.is_symlink():
                continue
            
            if entry.is_dir():
                # Recursively process subdirectories
                try:
                    subtree = _build_tree_structure(
                        entry,
                        exclude_patterns,
                        max_depth,
                        current_depth + 1
                    )
                    tree["children"].append(subtree)
                except (PermissionError, OSError):
                    # Skip directories we can't access
                    continue
            elif entry.is_file():
                tree["children"].append({
                    "type": "file",
                    "name": entry.name
                })
    
    except (PermissionError, OSError) as e:
        raise TreeReportError(f"Failed to read directory {root_path}: {e}")
    
    return tree


def _tree_to_markdown(tree: Dict[str, Any], indent: int = 0, prefix: str = "") -> str:
    """
    Convert tree structure to Markdown format.
    
    Args:
        tree: Tree structure dictionary
        indent: Current indentation level
        prefix: Prefix for the current line
    
    Returns:
        Markdown formatted string
    """
    lines = []
    
    # Add current node
    if indent == 0:
        # Root node
        lines.append(f"# {tree['name']}\n")
    else:
        indent_str = "  " * (indent - 1)
        lines.append(f"{indent_str}{prefix} {tree['name']}")
    
    # Add children
    if tree.get("children"):
        children = tree["children"]
        for i, child in enumerate(children):
            is_last = (i == len(children) - 1)
            
            if child["type"] == "directory":
                child_prefix = "└──" if is_last else "├──"
                lines.append(_tree_to_markdown(child, indent + 1, child_prefix))
            else:
                indent_str = "  " * indent
                child_prefix = "└──" if is_last else "├──"
                lines.append(f"{indent_str}{child_prefix} {child['name']}")
    
    return "\n".join(lines)


def generate_tree_report(
    root_path: Path,
    output_dir: Path,
    exclude_patterns: Optional[List[str]] = None,
    max_depth: Optional[int] = None,
    generate_json: bool = True,
    dry_run: bool = False
) -> None:
    """
    Generate tree report in Markdown and optionally JSON format.
    
    Args:
        root_path: Root directory to scan
        output_dir: Directory to write output files
        exclude_patterns: List of patterns to exclude (in addition to defaults)
        max_depth: Maximum depth to traverse (None for unlimited)
        generate_json: Whether to generate JSON output
        dry_run: If True, only log intent without writing files
    
    Raises:
        TreeReportError: If tree generation fails
    """
    # Combine default excludes with user-provided patterns
    all_excludes = DEFAULT_EXCLUDES.copy()
    if exclude_patterns:
        all_excludes.update(exclude_patterns)
    
    # Build tree structure
    try:
        tree = _build_tree_structure(root_path, all_excludes, max_depth)
    except Exception as e:
        raise TreeReportError(f"Failed to build tree structure: {e}")
    
    # Generate Markdown output
    markdown_content = _tree_to_markdown(tree)
    markdown_path = output_dir / "tree.md"
    
    if dry_run:
        print(f"[DRY RUN] Would write tree.md to: {markdown_path}")
        print(f"[DRY RUN] Content length: {len(markdown_content)} bytes")
    else:
        try:
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"Tree report written: {markdown_path}")
        except IOError as e:
            raise TreeReportError(f"Failed to write tree.md: {e}")
    
    # Generate JSON output if requested
    if generate_json:
        json_path = output_dir / "tree.json"
        
        if dry_run:
            print(f"[DRY RUN] Would write tree.json to: {json_path}")
            print(f"[DRY RUN] JSON entries: {_count_nodes(tree)}")
        else:
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(tree, f, indent=2)
                print(f"Tree JSON written: {json_path}")
            except IOError as e:
                raise TreeReportError(f"Failed to write tree.json: {e}")


def _count_nodes(tree: Dict[str, Any]) -> int:
    """Count total nodes in tree structure."""
    count = 1
    if tree.get("children"):
        for child in tree["children"]:
            count += _count_nodes(child)
    return count
