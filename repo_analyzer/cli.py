"""
Command-line interface for the repository analyzer.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional


DEFAULT_CONFIG_FILE = "repo-analyzer.config.json"
DEFAULT_OUTPUT_DIR = "repo-analysis-output"


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


class PathValidationError(Exception):
    """Raised when path validation fails."""
    pass


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from file.
    
    Args:
        config_path: Path to configuration file. If None, tries default location.
    
    Returns:
        Configuration dictionary
    
    Raises:
        ConfigurationError: If config file is invalid
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_FILE
    
    # If config file doesn't exist, return empty config
    if not os.path.exists(config_path):
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
    
    if cli_args.dry_run is not None:
        config['dry_run'] = cli_args.dry_run
    
    # Set defaults if not specified
    if 'output_dir' not in config:
        config['output_dir'] = DEFAULT_OUTPUT_DIR
    
    if 'dry_run' not in config:
        config['dry_run'] = False
    
    return config


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
        path = Path(output_dir).resolve()
        
        # Ensure path is not absolute outside working directory
        # This prevents writing to arbitrary locations on the filesystem
        cwd = Path.cwd().resolve()
        
        # If path is not relative to cwd, it's trying to escape
        try:
            path.relative_to(cwd)
        except ValueError:
            # Path is outside cwd, check if it's a relative path specification
            if os.path.isabs(output_dir):
                raise PathValidationError(
                    f"Absolute paths outside repository are not allowed: {output_dir}"
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

This document provides an overview of the repository analysis results.

## Analysis Components

### Directory Tree
See [tree.txt](tree.txt) for the complete directory structure.

### File Summaries
See [file-summaries/](file-summaries/) for individual file analysis reports.

### Dependencies
See [dependencies.json](dependencies.json) for dependency information.

## Generated Reports

- **tree.txt**: Complete directory tree structure
- **file-summaries/**: Directory containing per-file analysis
- **dependencies.json**: Dependency graph and package information

## Analysis Metadata

- Configuration: See repo-analyzer.config.json
- Timestamp: Generated on repository scan
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
        # Validate output path
        output_dir = validate_output_path(output_dir_str)
        
        # Create output directory
        create_output_directory(output_dir, dry_run)
        
        # Write summary template
        write_summary_template(output_dir, dry_run)
        
        # TODO: Hook points for generators
        # - Tree generator: generate_tree(output_dir, dry_run)
        # - File summary generator: generate_file_summaries(output_dir, dry_run)
        # - Dependency generator: generate_dependencies(output_dir, dry_run)
        
        if dry_run:
            print("\n[DRY RUN] Scan complete - no files were written")
        else:
            print("\nScan complete successfully")
        
        return 0
    
    except (ConfigurationError, PathValidationError) as e:
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
