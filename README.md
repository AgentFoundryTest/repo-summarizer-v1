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
    "include_patterns": ["*.py", "*.js", "*.ts"],
    "detail_level": "standard",
    "include_legacy_summary": true
  },
  "dependency_config": {
    "scan_package_files": true,
    "package_files": ["package.json", "requirements.txt", "pyproject.toml"]
  }
}
```

**New File Summary Options:**
- `detail_level`: Controls output verbosity (`"minimal"`, `"standard"`, `"detailed"`)
  - Default: `"standard"` (recommended for most use cases)
- `include_legacy_summary`: Include backward-compatible summary fields (`true`/`false`)
  - Default: `true` (ensures compatibility with existing consumers)

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
├── SUMMARY.md              # Top-level overview with links and stats
├── tree.md                 # Human-readable directory tree
├── tree.json               # Machine-readable directory structure
├── file-summaries.md       # Per-file heuristic summaries (human-readable)
├── file-summaries.json     # Per-file summaries (machine-readable, structured schema v2.0)
├── dependencies.md         # Human-readable dependency graph report
└── dependencies.json       # Machine-readable dependency graph
```

### File Summaries Schema (v2.0)

The `file-summaries.json` output uses a structured schema that provides rich metadata about each file:

#### Top-Level Structure
```json
{
  "schema_version": "2.0",
  "total_files": 5,
  "files": [...]
}
```

#### Per-File Structure

Each file entry includes the following fields (deterministic ordering):

**Required Fields:**
- `schema_version`: Schema version for the entry (e.g., "2.0")
- `path`: Relative path from repository root (POSIX format)
- `language`: Detected programming language (e.g., "Python", "JavaScript")
- `role`: File purpose/role (see Role Types below)

**Optional Fields (based on configuration):**
- `summary`: Human-readable description (legacy field, included by default)
- `summary_text`: Alias for `summary` (for enhanced compatibility)
- `metrics`: Object containing file metrics (included at "standard" and "detailed" levels)
  - `size_bytes`: File size in bytes
- `structure`: Object with structural information (included at "detailed" level)
  - `declarations`: List of top-level declarations (placeholder for future enhancement)
- `dependencies`: Object with dependency information (included at "detailed" level)
  - `imports`: List of imported modules/packages (placeholder for future enhancement)
  - `exports`: List of exported symbols (placeholder for future enhancement)

#### Role Types

Files are automatically classified into the following roles:
- `test`: Test files and test-related code
- `entry-point`: Main entry points (main.py, index.js, app.py)
- `configuration`: Configuration files (config.json, settings.py)
- `cli`: Command-line interface implementations
- `utility`: Utility and helper functions
- `model`: Data models and schemas
- `controller`: Request handlers and controllers
- `view`: View templates and presentation logic
- `service`: Service layer implementations
- `data-access`: Data access layer (repositories, DAOs)
- `api`: API implementations
- `database`: Database operations
- `router`: Routing configuration
- `middleware`: Middleware components
- `component`: UI components (React, Vue, etc.)
- `module-init`: Module initialization files (__init__.py, index.js)
- `documentation`: Documentation files
- `script`: Utility scripts
- `example`: Example code
- `implementation`: General implementation files (default)

#### Configuration Options

Control the output format via `file_summary_config` in your configuration file:

```json
{
  "file_summary_config": {
    "detail_level": "standard",
    "include_legacy_summary": true
  }
}
```

**Detail Levels:**
- `minimal`: Basic fields only (schema_version, path, language, role, summary)
- `standard`: Basic fields + metrics (default, recommended)
- `detailed`: All fields including structure and dependencies placeholders

**Backward Compatibility:**
- `include_legacy_summary`: When `true` (default), includes `summary` and `summary_text` fields for compatibility with tools expecting v1.0 format
- Setting to `false` produces a cleaner output without legacy fields

#### Example Output

**Standard Detail Level (default):**
```json
{
  "schema_version": "2.0",
  "total_files": 2,
  "files": [
    {
      "schema_version": "2.0",
      "path": "src/main.py",
      "language": "Python",
      "role": "entry-point",
      "summary": "Python main entry point",
      "summary_text": "Python main entry point",
      "metrics": {
        "size_bytes": 1024
      }
    },
    {
      "schema_version": "2.0",
      "path": "tests/test_main.py",
      "language": "Python",
      "role": "test",
      "summary": "Python test file",
      "summary_text": "Python test file",
      "metrics": {
        "size_bytes": 512
      }
    }
  ]
}
```

### Migration Guide

**Existing consumers (v1.0 format):**
The new schema is backward compatible by default. Your existing JSON parsers will continue to work because:
1. The `total_files` and `files` fields remain at the top level
2. Each file entry still has `path`, `language`, and `summary` fields
3. New fields (like `role`, `metrics`) can be safely ignored by v1.0 parsers

**Upgrading to v2.0:**
To take advantage of new features:
1. Check for `schema_version` field to detect format version
2. Use `role` field for intelligent filtering and categorization
3. Access `metrics.size_bytes` for file size information
4. Future versions may populate `structure` and `dependencies` with rich data

**Handling missing fields:**
- Always check for field existence before accessing
- For configs lacking `detail_level`, the default is "standard"
- For configs lacking `include_legacy_summary`, the default is `true`

## Development Status

Current implementation includes:
- ✅ CLI infrastructure and argument parsing
- ✅ Configuration loading and merging
- ✅ Output directory management with path validation
- ✅ Dry-run mode
- ✅ Summary document generation
- ✅ Tree generator (Markdown + JSON)
- ✅ File summary generator with structured schema v2.0 (Markdown + JSON, heuristic/path-based)
- ✅ Dependency scanner (Markdown + JSON, Python + JS/TS imports)

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
