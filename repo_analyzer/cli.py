# Copyright (c) 2025 John Brosnihan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Command-line interface for the repository analyzer.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from repo_analyzer.tree_report import generate_tree_report, TreeReportError
from repo_analyzer.file_summary import generate_file_summaries, FileSummaryError
from repo_analyzer.dependency_graph import generate_dependency_report, DependencyGraphError
from repo_analyzer.language_registry import get_global_registry


DEFAULT_CONFIG_FILE = "repo-analyzer.config.json"
DEFAULT_OUTPUT_DIR = "repo-analysis-output"


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


class PathValidationError(Exception):
    """Raised when path validation fails."""
    pass


def get_repository_root() -> Optional[Path]:
    """
    Get the repository root directory using git.
    
    Returns:
        Path to repository root, or None if not in a git repository
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True
        )
        return Path(result.stdout.strip()).resolve()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Not in a git repository or git not available
        return None


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from file.
    
    Args:
        config_path: Path to configuration file. If None, tries default location.
    
    Returns:
        Configuration dictionary
    
    Raises:
        ConfigurationError: If config file is invalid or user-specified file not found
    """
    user_specified = config_path is not None
    
    if config_path is None:
        # Default config should be at repository root
        repo_root = get_repository_root()
        if repo_root is not None:
            config_path = str(repo_root / DEFAULT_CONFIG_FILE)
        else:
            # Not in a git repository, use cwd
            config_path = DEFAULT_CONFIG_FILE
    
    # Check if config file exists
    if not os.path.exists(config_path):
        # If user explicitly specified a config file that doesn't exist, that's an error
        if user_specified:
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        # If default config doesn't exist, that's okay - return empty config
        return {}
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if not isinstance(config, dict):
            raise ConfigurationError(f"Configuration file must contain a JSON object")
        
        return config
    except json.JSONDecodeError as e:
        raise ConfigurationError(f"Invalid JSON in config file {config_path}: {e}")
    except IOError as e:
        raise ConfigurationError(f"Error reading config file {config_path}: {e}")


def merge_config(file_config: Dict[str, Any], cli_args: argparse.Namespace) -> Dict[str, Any]:
    """
    Merge configuration from file and CLI arguments.
    CLI arguments take precedence over file configuration.
    
    Args:
        file_config: Configuration loaded from file
        cli_args: Parsed command-line arguments
    
    Returns:
        Merged configuration dictionary
    """
    config = file_config.copy()
    
    # CLI arguments override file config
    if cli_args.output_dir is not None:
        config['output_dir'] = cli_args.output_dir
    
    # Only override dry_run if explicitly set by user (not just the default False)
    # We distinguish user-provided flag from default by checking if it's True
    if cli_args.dry_run:
        config['dry_run'] = True
    
    # Set defaults if not specified
    if 'output_dir' not in config:
        config['output_dir'] = DEFAULT_OUTPUT_DIR
    
    if 'dry_run' not in config:
        config['dry_run'] = False
    
    return config


def apply_language_config(config: Dict[str, Any]) -> None:
    """
    Apply language configuration to the global registry.
    
    This function configures the language registry based on the provided
    configuration. It supports enabling/disabling languages and setting
    language-specific overrides.
    
    Args:
        config: Configuration dictionary potentially containing 'language_config'
    """
    language_config = config.get('language_config')
    if language_config:
        registry = get_global_registry()
        registry.apply_config(language_config)


def validate_output_path(output_dir: str) -> Path:
    """
    Validate and normalize output directory path.
    Ensures path doesn't escape repository boundaries.
    
    Args:
        output_dir: Output directory path
    
    Returns:
        Validated Path object
    
    Raises:
        PathValidationError: If path is invalid
    """
    try:
        # Get repository root, fall back to current working directory if not in a git repo
        repo_root = get_repository_root()
        if repo_root is None:
            # Not in a git repository, use current working directory as boundary
            repo_root = Path.cwd().resolve()
        
        # Resolve relative paths against repository root for deterministic behavior
        # Absolute paths are used as-is
        if os.path.isabs(output_dir):
            path = Path(output_dir).resolve()
        else:
            path = (repo_root / output_dir).resolve()
        
        # Check if path is relative to repo root (i.e., inside the repository)
        try:
            path.relative_to(repo_root)
        except ValueError:
            # Path is outside repo - reject regardless of whether input was absolute or relative
            raise PathValidationError(
                f"Output path outside repository is not allowed: {output_dir}"
            )
        
        return path
    except Exception as e:
        if isinstance(e, PathValidationError):
            raise
        raise PathValidationError(f"Invalid output path: {output_dir}: {e}")


def create_output_directory(output_dir: Path, dry_run: bool = False) -> None:
    """
    Create output directory if it doesn't exist.
    
    Args:
        output_dir: Path to output directory
        dry_run: If True, only log intent without creating
    """
    if dry_run:
        print(f"[DRY RUN] Would create output directory: {output_dir}")
        return
    
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output directory ready: {output_dir}")
    except OSError as e:
        raise ConfigurationError(f"Failed to create output directory {output_dir}: {e}")


def write_summary_template(output_dir: Path, dry_run: bool = False) -> None:
    """
    Write summary document template referencing downstream reports.
    
    Args:
        output_dir: Path to output directory
        dry_run: If True, only log intent without writing
    """
    summary_path = output_dir / "SUMMARY.md"
    
    content = """# Repository Analysis Summary

This document provides an overview of the repository analysis results, showcasing the enriched summaries and dependency classification features of the Repository Analyzer tool.

## Key Features Demonstrated

This analysis demonstrates the **Schema v2.0** capabilities:

### 🎯 Role-Based Classification
Files are automatically categorized with explanations:
- **CLI files**: Command-line interface implementations
- **Module initialization**: Package setup files (__init__.py, index.js)
- **Implementation modules**: Core logic and functionality
- **Test files**: Test suites and test utilities
- **Configuration files**: Settings and config files
- **Entry points**: Main application entry points
- And 10+ more role types

### 📊 Structured Metrics
Each file includes quantitative analysis:
- **Lines of Code (LOC)**: Non-empty, non-comment line counts
- **File size**: Byte-level sizing information
- **TODO/FIXME tracking**: Development task identification
- **Declaration counts**: Top-level functions, classes, and exports (at detailed level)

### 🔗 External Dependency Classification
Dependencies are categorized deterministically:
- **Standard Library**: Built-in modules (Python stdlib, Node.js core modules)
- **Third-Party Packages**: External dependencies from package registries
- **Per-file tracking**: Each file's external dependencies are captured
- **Aggregate statistics**: Repository-wide dependency summary

### 📁 Detailed Code Structure
At the detailed level, the tool extracts:
- Top-level function and class declarations
- Export statements (for JavaScript/TypeScript)
- Structural warnings for files with syntax issues

## Analysis Components

### Directory Tree
See [tree.md](tree.md) for the complete directory structure with excluded patterns.

### File Summaries
See [file-summaries.md](file-summaries.md) for individual file analysis with:
- Role classifications and justifications
- Code metrics (LOC, size, TODO count)
- Structural information (at detailed level)
- External dependencies (at detailed level)

Machine-readable format: [file-summaries.json](file-summaries.json) (Schema v2.0)

### Dependencies
See [dependencies.json](dependencies.json) for comprehensive dependency information:
- **Intra-repository graph**: Import/require relationships between files
- **External dependencies**: Classified as stdlib vs third-party
- **Aggregated statistics**: Repository-wide dependency summary
- **Per-file tracking**: External dependencies for each analyzed file

Human-readable format: [dependencies.md](dependencies.md)

## Generated Reports

- **tree.md**: Complete directory tree structure (human-readable)
- **tree.json**: Machine-readable tree structure
- **file-summaries.md**: Markdown report with file analysis (human-readable)
- **file-summaries.json**: Structured file summaries with Schema v2.0 (machine-readable)
- **dependencies.json**: Dependency graph with external dependency classification (machine-readable)
- **dependencies.md**: Dependency analysis report (human-readable)

## Configuration Details

This analysis was generated using the configuration in repo-analyzer.config.json:
- **Detail Level**: Configurable (minimal/standard/detailed)
- **Legacy Compatibility**: Backward-compatible with v1.0 consumers
- **Max File Size**: Configurable threshold for expensive parsing operations
- **Excluded Patterns**: Customizable exclusion rules for tree traversal

For configuration options, see repo-analyzer.config.json or the project README.

## Schema Information

**File Summaries Schema Version**: 2.0

Schema v2.0 provides backward compatibility while adding:
- Role-based classification with justifications
- Quantitative metrics (size, LOC, TODO counts)
- Optional structure parsing (detailed level)
- External dependency tracking and classification (detailed level)

For migration information and detailed schema documentation, see the project README.

## Analysis Metadata

- **Tool Version**: Repository Analyzer v0.2.0
- **Configuration**: See repo-analyzer.config.json
- **Schema Version**: 2.0 (backward compatible with v1.0 consumers)
- **Timestamp**: Generated on repository scan
"""
    
    if dry_run:
        print(f"[DRY RUN] Would write summary template to: {summary_path}")
        print(f"[DRY RUN] Content length: {len(content)} bytes")
        return
    
    try:
        with open(summary_path, 'w') as f:
            f.write(content)
        print(f"Summary template written: {summary_path}")
    except IOError as e:
        raise ConfigurationError(f"Failed to write summary template: {e}")


def run_scan(config: Dict[str, Any]) -> int:
    """
    Execute repository scan with given configuration.
    
    Args:
        config: Merged configuration dictionary
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    output_dir_str = config['output_dir']
    dry_run = config['dry_run']
    
    try:
        # Apply language configuration to the registry
        apply_language_config(config)
        
        # Validate output path
        output_dir = validate_output_path(output_dir_str)
        
        # Create output directory
        create_output_directory(output_dir, dry_run)
        
        # Write summary template
        write_summary_template(output_dir, dry_run)
        
        # Generate tree report
        repo_root = get_repository_root()
        if repo_root is None:
            repo_root = Path.cwd()
        
        tree_config = config.get('tree_config', {})
        exclude_patterns = tree_config.get('exclude_patterns', [])
        max_depth = tree_config.get('max_depth')
        generate_json = tree_config.get('generate_json', True)
        
        generate_tree_report(
            root_path=repo_root,
            output_dir=output_dir,
            exclude_patterns=exclude_patterns,
            max_depth=max_depth,
            generate_json=generate_json,
            dry_run=dry_run
        )
        
        # Generate file summaries
        file_summary_config = config.get('file_summary_config', {})
        include_patterns = file_summary_config.get('include_patterns', [])
        
        # If no include_patterns specified, generate from enabled languages in registry
        if not include_patterns:
            registry = get_global_registry()
            enabled_languages = registry.get_enabled_languages()
            # Generate patterns like *.py, *.js from all enabled language extensions
            # Validate extensions start with a dot and contain only valid glob characters
            include_patterns = []
            for lang in enabled_languages:
                for ext in lang.extensions:
                    # Ensure extension format is valid (starts with dot)
                    if ext.startswith('.') and len(ext) > 1:
                        # Create glob pattern
                        pattern = f"*{ext}"
                        include_patterns.append(pattern)
            
            # If no valid patterns generated, fall back to empty list (scan nothing)
            # This is safer than scanning all files
            if not include_patterns:
                print("Warning: No valid file patterns generated from enabled languages")
        
        # Get exclude patterns from file_summary_config
        file_exclude_patterns = file_summary_config.get('exclude_patterns', [])
        
        # Import default excludes from tree_report
        from repo_analyzer.tree_report import DEFAULT_EXCLUDES
        
        # Start with default excludes to handle the "no config" case
        # This ensures noise directories are ignored by default
        all_exclude_patterns = list(DEFAULT_EXCLUDES)
        
        # Add tree_config exclude patterns
        all_exclude_patterns.extend(exclude_patterns)
        
        # Add file_summary_config exclude patterns
        all_exclude_patterns.extend(file_exclude_patterns)
        
        # Exclude the output directory to avoid scanning generated reports
        try:
            output_rel = output_dir.relative_to(repo_root)
            # Add as both a pattern and to exclude_dirs if it's a simple name
            all_exclude_patterns.append(str(output_rel.as_posix()))
        except ValueError:
            # output_dir is not relative to repo_root (e.g., absolute path outside repo)
            # In this case, it won't be scanned anyway
            pass
        
        # Build exclude_dirs from all exclude patterns
        # Only add patterns that are bare directory names (no path separator or wildcard)
        exclude_dirs = set()
        for pattern in all_exclude_patterns:
            if '*' not in pattern and '/' not in pattern:
                # Simple directory name like "node_modules", "__pycache__"
                exclude_dirs.add(pattern)
        
        # Get detail level and legacy summary options with safe defaults
        detail_level = file_summary_config.get('detail_level', 'standard')
        include_legacy_summary = file_summary_config.get('include_legacy_summary', True)
        
        generate_file_summaries(
            root_path=repo_root,
            output_dir=output_dir,
            include_patterns=include_patterns,
            exclude_patterns=all_exclude_patterns,
            exclude_dirs=exclude_dirs,
            dry_run=dry_run,
            detail_level=detail_level,
            include_legacy_summary=include_legacy_summary
        )
        
        # Generate dependency graph
        generate_dependency_report(
            root_path=repo_root,
            output_dir=output_dir,
            include_patterns=include_patterns,
            exclude_patterns=all_exclude_patterns,
            exclude_dirs=exclude_dirs,
            dry_run=dry_run
        )
        
        if dry_run:
            print("\n[DRY RUN] Scan complete - no files were written")
        else:
            print("\nScan complete successfully")
        
        return 0
    
    except (ConfigurationError, PathValidationError, TreeReportError, FileSummaryError, DependencyGraphError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 2


def scan_command(args: argparse.Namespace) -> int:
    """
    Handle the 'scan' subcommand.
    
    Args:
        args: Parsed command-line arguments
    
    Returns:
        Exit code
    """
    try:
        # Load configuration from file
        file_config = load_config(args.config)
        
        # Merge with CLI arguments
        config = merge_config(file_config, args)
        
        if args.dry_run:
            print("Running in DRY RUN mode - no files will be written")
            print(f"Configuration: {json.dumps(config, indent=2)}")
            print()
        
        # Execute scan
        return run_scan(config)
    
    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog='repo-analyzer',
        description='Repository analysis tool for generating comprehensive code reports'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan subcommand
    scan_parser = subparsers.add_parser(
        'scan',
        help='Scan repository and generate analysis reports'
    )
    scan_parser.add_argument(
        '-o', '--output-dir',
        type=str,
        help=f'Output directory for reports (default: {DEFAULT_OUTPUT_DIR})'
    )
    scan_parser.add_argument(
        '-c', '--config',
        type=str,
        help=f'Configuration file path (default: {DEFAULT_CONFIG_FILE})'
    )
    scan_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview actions without writing files'
    )
    
    args = parser.parse_args()
    
    # If no command specified, show help
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    if args.command == 'scan':
        exit_code = scan_command(args)
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
