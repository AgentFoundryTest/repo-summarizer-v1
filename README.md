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
- `role_justification`: Explanation of why the file was assigned this role

**Optional Fields (based on configuration):**
- `summary`: Human-readable description (legacy field, included by default)
- `summary_text`: Alias for `summary` (for enhanced compatibility)
- `metrics`: Object containing file metrics (included at "standard" and "detailed" levels)
  - `size_bytes`: File size in bytes
  - `loc`: Lines of code (non-empty, non-comment lines)
  - `todo_count`: Number of TODO/FIXME comments found
  - `declaration_count`: Number of top-level declarations (included at "detailed" level when parsing succeeds)
- `structure`: Object with structural information (included at "detailed" level)
  - `declarations`: List of top-level declarations (functions, classes, exports)
  - `warning`: Optional warning message if parsing failed or was skipped
- `dependencies`: Object with dependency information (included at "detailed" level)
  - `imports`: List of imported modules/packages (placeholder for future enhancement)
  - `exports`: List of exported symbols (placeholder for future enhancement)

#### Language-Aware Parsing

The tool uses static analysis to extract structure information from source files:

**Python Files:**
- Uses Python's built-in `ast` module for safe parsing
- Extracts top-level functions, async functions, and classes
- No code execution - completely static analysis
- Gracefully handles syntax errors with warning messages

**JavaScript/TypeScript Files:**
- Uses deterministic regex patterns for lightweight parsing
- Detects exported functions, classes, constants, and default exports
- Handles both named and list-style exports
- Best-effort approach that covers common patterns

**All Files:**
- LOC (Lines of Code): Counts non-empty, non-comment lines
- TODO/FIXME Detection: Case-insensitive search for TODO and FIXME comments
- Large File Handling: Skips expensive parsing for files >1024KB (configurable via `max_file_size_kb`)

#### Role Detection Heuristics

Files are automatically classified using deterministic rules based on:

1. **Filename patterns**: e.g., `test_*.py`, `*_test.py`, `main.py`, `cli.py`
2. **File extensions**: e.g., `.json`, `.yaml` → configuration
3. **Directory location**: e.g., `tests/`, `docs/`, `scripts/`
4. **Content-based hints**: Component extensions like `.jsx`, `.tsx`, `.vue`

Each classification includes a `role_justification` field explaining the reasoning, such as:
- "filename starts with 'test_'"
- "common entry point name 'main'"
- "configuration file extension '.json'"
- "located in 'tests' directory"
- "general implementation file (default classification)"

This explainability helps users understand and trust automated classifications.

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
    "include_legacy_summary": true,
    "max_file_size_kb": 1024
  }
}
```

**Detail Levels:**
- `minimal`: Basic fields only (schema_version, path, language, role, role_justification, summary)
- `standard`: Basic fields + metrics (size, LOC, TODO count) - **default, recommended**
- `detailed`: All fields including structure with parsed declarations and declaration counts

**Advanced Options:**
- `include_legacy_summary`: When `true` (default), includes `summary` and `summary_text` fields for compatibility with tools expecting v1.0 format
- `max_file_size_kb`: Maximum file size in KB for expensive parsing operations (default: 1024). Larger files skip declaration parsing but still report basic metrics.

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
      "role_justification": "common entry point name 'main'",
      "summary": "Python main entry point (role: entry-point)",
      "summary_text": "Python main entry point (role: entry-point)",
      "metrics": {
        "size_bytes": 1024,
        "loc": 45,
        "todo_count": 2
      }
    },
    {
      "schema_version": "2.0",
      "path": "tests/test_main.py",
      "language": "Python",
      "role": "test",
      "role_justification": "filename starts with 'test_'",
      "summary": "Python test file (role: test)",
      "summary_text": "Python test file (role: test)",
      "metrics": {
        "size_bytes": 512,
        "loc": 30,
        "todo_count": 0
      }
    }
  ]
}
```

**Detailed Detail Level:**
```json
{
  "schema_version": "2.0",
  "path": "src/api.py",
  "language": "Python",
  "role": "api",
  "role_justification": "filename contains 'api'",
  "summary": "Python API implementation (role: api)",
  "summary_text": "Python API implementation (role: api)",
  "metrics": {
    "size_bytes": 2048,
    "loc": 85,
    "todo_count": 3,
    "declaration_count": 5
  },
  "structure": {
    "declarations": [
      "class APIClient",
      "function get_user",
      "function create_user",
      "function update_user",
      "async function delete_user"
    ]
  },
  "dependencies": {
    "imports": [],
    "exports": [],
    "external": {
      "stdlib": ["os", "sys", "pathlib.Path"],
      "third-party": ["requests", "django.http.HttpResponse"]
    }
  }
}
```

### External Dependencies (Detailed Level)

At the "detailed" level, file summaries include classifications of external dependencies:

- **Standard Library / Core Modules**: Built-in modules (Python stdlib, Node.js core modules)
- **Third-Party Packages**: External packages from PyPI, npm, etc.

Classification is performed **deterministically without network calls** using comprehensive built-in tables:
- Python: 100+ stdlib modules (os, sys, pathlib, typing, asyncio, etc.)
- Node.js: 70+ core modules (fs, path, http, crypto, etc.)

**Example:**
```json
{
  "dependencies": {
    "external": {
      "stdlib": ["os", "sys", "json"],
      "third-party": ["requests", "numpy", "django.http.HttpResponse"]
    }
  }
}
```

**Key Features:**
- Relative imports (e.g., `from . import utils`) are excluded from external dependencies
- Dependencies are deduplicated and sorted for deterministic output
- Both per-file and aggregated summaries are available
- Supports Python and JavaScript/TypeScript ecosystems

### Migration Guide

**Existing consumers (v1.0 format):**
The new schema is backward compatible by default. Your existing JSON parsers will continue to work because:
1. The `total_files` and `files` fields remain at the top level
2. Each file entry still has `path`, `language`, and `summary` fields
3. New fields (like `role`, `role_justification`, `metrics`) can be safely ignored by v1.0 parsers

**Upgrading to v2.0:**
To take advantage of new features:
1. Check for `schema_version` field to detect format version
2. Use `role` and `role_justification` fields for intelligent filtering and understanding file purposes
3. Access `metrics.size_bytes`, `metrics.loc`, and `metrics.todo_count` for file analysis
4. At "detailed" level, use `structure.declarations` to see top-level code structure
5. Check `structure.warning` for any parsing issues that occurred

**Handling missing fields:**
- Always check for field existence before accessing
- For configs lacking `detail_level`, the default is "standard"
- For configs lacking `include_legacy_summary`, the default is `true`
- For configs lacking `max_file_size_kb`, the default is `1024`

**Error Handling and Edge Cases:**
- **Syntax errors**: Files with invalid syntax will have an empty `declarations` array and a `warning` in the `structure` field
- **Large files**: Files exceeding `max_file_size_kb` will skip declaration parsing but still report basic metrics
- **Unknown languages**: Files in unsupported languages will have basic metrics but no declarations
- **Files without extensions**: Will be classified as "Unknown" language with role based on filename/path

### Dependency Graph Features

The `dependencies.json` and `dependencies.md` outputs provide comprehensive dependency analysis:

#### Intra-Repository Dependencies
- Tracks import/require statements across Python and JavaScript/TypeScript files
- Resolves relative and absolute imports to actual file paths within the repository
- Provides graph structure with nodes (files) and edges (dependencies)
- Identifies most depended-upon files and files with most dependencies

#### External Dependencies
- **Automatic Classification**: Distinguishes between stdlib/core modules and third-party packages
- **Deterministic & Offline**: No network calls or package manager invocations required
- **Per-File Tracking**: Each file node includes its external dependencies
- **Aggregated Statistics**: Summary counts and lists of all external dependencies

**Example `dependencies.json` structure:**
```json
{
  "nodes": [
    {
      "id": "main.py",
      "path": "main.py",
      "type": "file",
      "external_dependencies": {
        "stdlib": ["os", "sys", "json"],
        "third-party": ["requests", "numpy"]
      }
    }
  ],
  "edges": [
    {
      "source": "main.py",
      "target": "utils.py"
    }
  ],
  "external_dependencies_summary": {
    "stdlib": ["asyncio", "json", "os", "pathlib", "sys"],
    "third-party": ["django", "numpy", "requests"],
    "stdlib_count": 5,
    "third-party_count": 3
  }
}
```

**Classification Tables:**
- **Python**: 100+ stdlib modules (os, sys, pathlib, typing, asyncio, collections, etc.)
- **Node.js**: 70+ core modules (fs, path, http, https, crypto, stream, etc.)
- Tables are maintained in code at `repo_analyzer/stdlib_classification.py`
- Future updates can easily extend classification for additional ecosystems

## Development Status

Current implementation includes:
- ✅ CLI infrastructure and argument parsing
- ✅ Configuration loading and merging
- ✅ Output directory management with path validation
- ✅ Dry-run mode
- ✅ Summary document generation
- ✅ Tree generator (Markdown + JSON)
- ✅ File summary generator with structured schema v2.0 (Markdown + JSON)
  - ✅ Language-aware structure parsing (Python AST, JS/TS exports)
  - ✅ LOC and TODO/FIXME counting
  - ✅ Role inference with justifications
  - ✅ Graceful error handling for syntax errors
  - ✅ External dependency tracking (stdlib vs third-party) at detailed level
- ✅ Dependency scanner (Markdown + JSON, Python + JS/TS imports)
  - ✅ Intra-repository dependency graph
  - ✅ External dependency classification (stdlib vs third-party)
  - ✅ Per-file and aggregated external dependency reporting
  - ✅ Deterministic classification without network calls

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
