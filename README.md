# Repository Analyzer

A Python tool for analyzing repository structure, generating file summaries, and tracking dependencies. Designed for use in CI/CD pipelines with deterministic, non-interactive operation.

## Features

- **Non-interactive CLI**: Designed for automation and CI/CD integration
- **Deterministic output**: Generates consistent reports in a configurable output directory
- **Dry-run mode**: Preview actions without modifying the filesystem
- **Flexible configuration**: Supports both config files and CLI arguments
- **Safe path handling**: Prevents writes outside designated output directory

## Installation

```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Quick Start

Scan a repository with default settings:
```bash
repo-analyzer scan
```

Specify custom output directory:
```bash
repo-analyzer scan --output-dir ./my-analysis
```

Preview actions without writing files:
```bash
repo-analyzer scan --dry-run
```

Use custom configuration file:
```bash
repo-analyzer scan --config ./my-config.json
```

## Configuration

Configuration can be provided via:
1. Configuration file (default: `repo-analyzer.config.json`)
2. Command-line arguments (takes precedence)

### Configuration File Format

```json
{
  "output_dir": "repo-analysis-output",
  "dry_run": false,
  "tree_config": {
    "max_depth": null,
    "exclude_patterns": [".git", "__pycache__", "node_modules"]
  },
  "file_summary_config": {
    "max_file_size_kb": 1024,
    "include_patterns": ["*.py", "*.js", "*.ts"]
  },
  "dependency_config": {
    "scan_package_files": true,
    "package_files": ["package.json", "requirements.txt", "pyproject.toml"]
  }
}
```

### CLI Arguments

- `-o, --output-dir DIR`: Output directory for analysis reports
- `-c, --config FILE`: Path to configuration file
- `--dry-run`: Preview actions without writing files

### Configuration Precedence

1. CLI arguments (highest priority)
2. Configuration file
3. Built-in defaults (lowest priority)

## Usage in CI/CD

The tool is designed for CI/CD integration with the following characteristics:

- **Exit codes**: Returns 0 on success, non-zero on failure
- **No interaction**: Never prompts for user input
- **Deterministic**: Produces consistent output across runs
- **Safe writes**: Only writes to specified output directory

Example GitHub Actions workflow:
```yaml
- name: Analyze repository
  run: |
    pip install -e .
    repo-analyzer scan --output-dir ./analysis-reports
    
- name: Upload analysis
  uses: actions/upload-artifact@v3
  with:
    name: repo-analysis
    path: ./analysis-reports
```

## Output Structure

The tool generates the following outputs in the specified directory:

```
repo-analysis-output/
├── SUMMARY.md              # Overview linking to all reports
├── tree.txt               # Directory tree structure
├── file-summaries/        # Per-file analysis (TODO)
└── dependencies.json      # Dependency information (TODO)
```

## Development Status

Current implementation includes:
- ✅ CLI infrastructure and argument parsing
- ✅ Configuration loading and merging
- ✅ Output directory management with path validation
- ✅ Dry-run mode
- ✅ Summary template generation
- 🚧 Tree generator (interface defined, implementation pending)
- 🚧 File summary generator (interface defined, implementation pending)
- 🚧 Dependency scanner (interface defined, implementation pending)

## Error Handling

The tool provides clear error messages and appropriate exit codes:

- **Exit 0**: Successful completion
- **Exit 1**: Configuration or validation error (with descriptive message)
- **Exit 2**: Unexpected runtime error



# Permanents (License, Contributing, Author)

Do not change any of the below sections

## License

All Agent Foundry work is licensed under the GPLv3 License - see the LICENSE file for details.

## Contributing

Feel free to submit issues and enhancement requests!

## Author

Created by Agent Foundry and John Brosnihan
