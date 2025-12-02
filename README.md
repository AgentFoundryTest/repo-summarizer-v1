# Repository Analyzer

A Python tool for analyzing repository structure, generating file summaries, and tracking dependencies. Designed for use in CI/CD pipelines with deterministic, non-interactive operation.

**Current Version**: 0.2.0 ([Changelog](CHANGELOG.md))

## Features

- **Structured file summaries**: Schema v2.0 with role classifications, metrics, and optional structure parsing
- **External dependency tracking**: Automatic classification of stdlib vs third-party dependencies
- **Non-interactive CLI**: Designed for automation and CI/CD integration
- **Deterministic output**: Generates consistent reports in a configurable output directory
- **Dry-run mode**: Preview actions without modifying the filesystem
- **Flexible configuration**: Supports both config files and CLI arguments with multiple detail levels
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

For a fully commented configuration example, see [`repo-analyzer.config.example.jsonc`](repo-analyzer.config.example.jsonc).

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
  },
  "language_config": {
    "enabled_languages": null,
    "disabled_languages": [],
    "language_overrides": {}
  }
}
```

**New File Summary Options:**
- `detail_level`: Controls output verbosity (`"minimal"`, `"standard"`, `"detailed"`)
  - Default: `"standard"` (recommended for most use cases)
- `include_legacy_summary`: Include backward-compatible summary fields (`true`/`false`)
  - Default: `true` (ensures compatibility with existing consumers)

### Language Registry

The analyzer includes a **pluggable language registry** that provides deterministic language detection and allows fine-grained control over which languages are analyzed. This enables multi-language repository analysis without modifying core code.

#### Supported Languages

The registry includes built-in support for:

**Full Support** (with structure parsing and dependency scanning):
- **Python** (.py, .pyw) - AST-based parsing, import resolution
- **JavaScript** (.js, .jsx, .mjs, .cjs) - Regex-based parsing, require/import resolution
- **TypeScript** (.ts, .tsx) - Regex-based parsing, import resolution

**Dependency Scanning** (with import/include parsing and external classification):
- **C** (.c) - #include directives, stdlib header classification
- **C++** (.cpp, .cc, .cxx, .hpp, .hh, .hxx, .h) - #include directives, STL classification
- **C#** (.cs) - using statements, System namespace classification
- **Rust** (.rs) - use/mod statements, std crate classification
- **Go** (.go) - import statements, stdlib package classification
- **Java** (.java) - import statements, java/javax classification
- **Swift** (.swift) - import statements, Foundation/UIKit classification
- **HTML** (.html, .htm) - href/src references (local files only)
- **CSS** (.css) - url() references (local files only)
- **SQL** (.sql) - vendor-specific include statements, system schema classification

**Basic Support** (file detection and metrics only):
- Ruby, PHP, Kotlin, Scala, Shell, Bash, Zsh, PowerShell, R, Objective-C, SCSS, Sass, Less, Vue
- Markdown, reStructuredText, YAML, JSON, XML, TOML, INI, Config files

#### Language Configuration Options

Configure language support through the `language_config` section:

```json
{
  "language_config": {
    "enabled_languages": null,
    "disabled_languages": [],
    "language_overrides": {}
  }
}
```

**Options:**

- **`enabled_languages`**: Explicitly enable specific languages
  - When `null` (default): All languages are enabled
  - When set to a list: ONLY those languages will be analyzed
  - Example: `["Python", "JavaScript", "TypeScript"]`

- **`disabled_languages`**: Explicitly disable specific languages
  - Languages in this list will not be analyzed
  - Useful for excluding languages you don't want to track
  - Takes precedence over `enabled_languages` if a language appears in both
  - Example: `["Ruby", "PHP"]`

- **`language_overrides`**: Fine-tune individual language settings
  - Set language-specific priority and enabled status
  - Priority determines which language wins for shared extensions (e.g., .h for C/C++)
  - Higher priority = preferred for ambiguous extensions
  - Example:
    ```json
    {
      "Python": {"priority": 15, "enabled": true},
      "Ruby": {"enabled": false}
    }
    ```

**Configuration Processing Order:**
1. `enabled_languages` is processed first (if specified, disables all other languages)
2. `disabled_languages` is processed second (disables specified languages)
3. `language_overrides` is processed last (applies individual settings)

**Note:** If a language appears in both `enabled_languages` and `disabled_languages`, it will be disabled (disabled takes precedence).

#### Extension Conflict Resolution

Some file extensions are shared across multiple languages (e.g., `.h` for C/C++). The registry uses **priority-based resolution**:

- Each language has a priority (default priorities: 2-10)
- Higher priority wins for shared extensions
- **Equal priorities**: When two languages have equal priority for a shared extension, behavior is implementation-defined (last registered typically wins)
- Default priorities favor:
  - Full-support languages (priority 10): Python, JavaScript, TypeScript
  - Primary compiled languages (priority 8-9): C++, C, C#, Rust, Go, Java, Swift
  - Markup and config languages (priority 2-5)

You can override priorities through `language_overrides` to customize conflict resolution.

#### Auto-Generated Include Patterns

If `file_summary_config.include_patterns` is empty or not specified, the analyzer automatically generates patterns from **enabled languages only**:

```json
{
  "file_summary_config": {
    "include_patterns": []  // Auto-generated from enabled languages
  },
  "language_config": {
    "enabled_languages": ["Python", "JavaScript"]
  }
}
```

This automatically analyzes `.py`, `.js`, `.jsx`, `.mjs`, `.cjs` files without manual pattern configuration.

#### Usage Examples

**Example 1: Analyze only Python and JavaScript**
```json
{
  "language_config": {
    "enabled_languages": ["Python", "JavaScript"]
  }
}
```

**Example 2: Exclude markup and config files**
```json
{
  "language_config": {
    "disabled_languages": ["Markdown", "YAML", "JSON", "TOML"]
  }
}
```

**Example 3: Prioritize C over C++ for .h files**
```json
{
  "language_config": {
    "language_overrides": {
      "C": {"priority": 100}
    }
  }
}
```

**Example 4: Mixed-language repository**
```json
{
  "language_config": {
    "enabled_languages": ["Python", "JavaScript", "TypeScript", "Go", "Rust"]
  }
}
```

#### Extending Language Support

To add support for a new language:

1. **Via Configuration** (recommended for simple cases):
   - No code changes needed
   - Use `language_overrides` to customize existing languages
   - Limited to file detection and basic metrics

2. **Via Code Extension** (for full support):
   - Add language to `language_registry.py` with parser capabilities
   - Implement structure parser in `file_summary.py`
   - Add dependency scanner in `dependency_graph.py`
   - Provides full analysis capabilities

The registry design ensures new languages can be added without breaking existing functionality or changing CLI contracts.

#### Backward Compatibility

The language registry maintains full backward compatibility:

- **Existing configs without `language_config`**: Work unchanged (all languages enabled)
- **Existing `include_patterns`**: Take precedence over auto-generated patterns
- **Legacy `LANGUAGE_MAP`**: Used as fallback for any unmapped extensions
- **CLI flags**: Unchanged behavior
- **Output formats**: Identical structure

Repositories can adopt the language registry incrementally without disrupting existing workflows.

### File Summary Heuristics

The analyzer generates intelligent, language-specific summaries for files based on naming conventions, path patterns, and language-specific idioms. This provides detailed insight without requiring code parsing.

#### Language-Specific Detection

Each supported language has tailored heuristics that recognize common patterns:

**C/C++:**
- Headers (.h, .hpp) vs implementations (.c, .cpp)
- Internal headers (`*_internal.h`, files in `internal/`)
- Type definition headers (`types.h`, `defs.h`)
- Interface headers (names starting with 'I' or containing 'interface')
- Template implementations (.tpp, .tcc)
- Main entry points (`main.c`, `main.cpp`)

**Rust:**
- Library entry points (`lib.rs`)
- Binary entry points (`main.rs`)
- Module declarations (`mod.rs`)
- Test modules (`*_test.rs`, files in `tests/`)
- Benchmarks (files in `benches/`)
- Examples (files in `examples/`)
- Binary implementations (`src/bin/`)

**Go:**
- Main packages (`main.go`)
- Test files (`*_test.go`)
- Internal packages (files in `internal/` or `*_internal.go`)
- Command-line applications (`cmd/`)
- Library packages (`pkg/`)
- Protocol buffer definitions (`.pb.go`, `*proto.go`)

**Java:**
- Interfaces (names starting with 'I' or ending with 'Interface')
- Abstract classes (`Abstract*`, `*Abstract`)
- Exception classes (`*Exception`)
- Test classes (`*Test`, `*Tests`)
- Controllers, Services, Repositories, DAOs
- Entity/Model classes
- Utility classes (`*Util`, `*Utils`, `*Helper`)

**C#:**
- Interfaces (names starting with 'I' or ending with 'Interface')
- Controllers, Services, Repositories
- ViewModels (MVVM pattern)
- Extension methods (`*Extensions`)
- Program entry point (`Program.cs`)

**Swift:**
- View controllers (`*ViewController`, `*Controller`)
- Views, ViewModels (MVVM pattern)
- Models, Services, Managers
- Delegates (`*Delegate`)
- Protocols (`*Protocol`)
- Type extensions (`*Extension`)

**HTML:**
- Main pages (`index.html`, `home.html`)
- Templates (files in `templates/` or `*template.html`)
- Components (files in `components/` or `*component.html`)
- Partials (`*partial.html`, files in `partials/`)
- Layouts (`*layout.html`)
- Email templates (files in `email/`)

**CSS:**
- Main stylesheets (`style.css`, `styles.css`, `main.css`)
- Themes (`*theme*.css`)
- Variables/constants (`variables.css`, `vars.css`)
- Reset/normalization (`reset.css`, `normalize.css`)
- Responsive design (`responsive.css`, `*media*.css`)
- Component styles (files in `components/`)
- Utility classes (`*util*.css`, `*helper*.css`)

**SQL:**
- Migrations (files in `migrations/` or `*migration*.sql`)
- Schema definitions (`schema.sql`, `ddl.sql`, `create.sql`)
- Seed data (`*seed*.sql`, `*fixture*.sql`)
- Views (`*view*.sql`, `v_*.sql`)
- Stored procedures (`*proc*.sql`, `sp_*.sql`)
- Functions (`*function*.sql`, `fn_*.sql`)
- Triggers (`*trigger*.sql`)
- Query definitions (`*query*.sql`, `*queries*.sql`)

#### Fallback Heuristics

For files that don't match language-specific patterns, the analyzer uses general heuristics:
- Configuration files (`config.*`, `settings.*`)
- Test files (`test_*`, `*_test.*`)
- Main entry points (`main.*`, `index.*`, `app.*`)
- CLI files (`cli.*`, `command.*`)
- Utility/helper files (`utils.*`, `util.*`, `helpers.*`)
- Models, Controllers, Services, Repositories
- API implementations (`*api*`)
- Database operations (`*db*`, `*database*`)

#### Limitations and Intentional Non-Support

The heuristics are designed to be **deterministic and fast**, operating only on filenames, extensions, and paths. They intentionally avoid:

- **Parsing file contents** (except for Python/JS/TS at detailed level)
- **Compiling source code**
- **External tool dependencies**
- **Non-deterministic operations**

This means:
- Generated code may not be distinguished from hand-written code
- Template files (e.g., `.go.tpl`) fall back to safe defaults
- Massive generated files (e.g., CSS bundles, SQL migrations) are handled efficiently without timeouts
- Mixed-language files (e.g., HTML with embedded CSS/JS) show per-file summaries

These trade-offs prioritize **speed, reliability, and determinism** for CI/CD use cases.

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

The `dependencies.json` and `dependencies.md` outputs provide comprehensive dependency analysis across multiple programming languages.

#### Supported Languages

The dependency scanner now supports the following languages with import/include statement parsing:

| Language | Import Syntax | Resolution | External Classification |
|----------|--------------|------------|------------------------|
| **Python** | `import`, `from...import` | ✅ Intra-repo + External | ✅ Stdlib vs 3rd-party |
| **JavaScript/TypeScript** | `import`, `require()`, `import()` | ✅ Intra-repo + External | ✅ Node core vs npm |
| **C/C++** | `#include <...>`, `#include "..."` | ✅ Intra-repo + External | ✅ System headers vs 3rd-party |
| **Rust** | `use`, `mod` | ✅ Intra-repo + External | ✅ std/core vs crates |
| **Go** | `import` | External only | ✅ stdlib vs packages |
| **Java** | `import`, `import static` | External only | ✅ java.*/javax.* vs 3rd-party |
| **C#** | `using` | External only | ✅ System.*/Microsoft.* vs 3rd-party |
| **Swift** | `import` | External only | ✅ Foundation/UIKit vs packages |
| **HTML/CSS** | `href`, `src`, `url()` | ✅ Local assets only | N/A |
| **SQL** | `\i`, `SOURCE`, `EXEC` | ✅ Intra-repo includes | ✅ System schemas vs user |

**Note on Resolution:**
- **Intra-repo resolution**: Resolves import/include statements to actual files within the repository, creating dependency edges
- **External only**: Tracks external packages/modules but doesn't resolve to files (requires build context)
- For languages like Go, Java, C#, and Swift, intra-repo resolution would require build system integration, so only external dependencies are tracked

#### Language-Specific Parsing Details

**C/C++:**
- Parses `#include <header>` and `#include "header"` directives
- Resolves headers relative to source file, include directories, and repo root
- Classifies standard library headers (stdio.h, iostream, etc.) vs third-party (boost, etc.)
- Skips comments to avoid false positives

**Rust:**
- Parses `use crate::module`, `use std::io`, and `mod module` statements
- Resolves local modules via file system (module.rs, module/mod.rs patterns)
- Handles crate-relative (`crate::`), self-relative (`self::`), and parent-relative (`super::`) imports
- Classifies std/core/alloc crates as stdlib

**Go:**
- Parses single-line `import "package"` and multi-line `import (...)` blocks
- Supports aliased imports including dot imports (`. "package"`)
- Classifies by domain presence: packages without domains are stdlib (fmt, net/http)
- Packages with domains (github.com/...) are third-party

**Java:**
- Parses `import` and `import static` statements, including wildcards
- Classifies java.* and javax.* as stdlib
- All other packages (com.*, org.*, etc.) are third-party

**C#:**
- Parses `using` directives including aliased using statements
- Classifies System.* and Microsoft.* namespaces as stdlib
- Third-party packages (Newtonsoft.Json, etc.) are detected

**Swift:**
- Parses `import` statements including typed imports (`import struct Foundation.URL`)
- Classifies Apple frameworks (Foundation, UIKit, SwiftUI) as stdlib
- Third-party modules (Alamofire, etc.) are detected

**HTML/CSS:**
- Parses `href` and `src` attributes in HTML
- Parses `url()` references in CSS
- Only tracks local/relative references within the repository
- Skips absolute URLs, CDN references, and data URLs

**SQL:**
- Parses PostgreSQL `\i` and `\include` commands
- Parses MySQL `SOURCE` and `\.` commands
- Parses SQL Server `EXEC` patterns with .sql files
- Classifies system schemas (information_schema, pg_catalog) vs user schemas

#### Intra-Repository Dependencies
- Tracks import/require/include statements across all supported languages
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

#### Standard Library Classification Tables

Classification is deterministic and based on comprehensive reference tables maintained in `repo_analyzer/stdlib_classification.py`:

- **Python**: 150+ stdlib modules (os, sys, pathlib, typing, asyncio, collections, etc.)
- **Node.js**: 80+ core modules (fs, path, http, https, crypto, stream, etc.)
- **C/C++**: 100+ standard headers (stdio.h, iostream, vector, algorithm, etc.)
- **Rust**: 40+ stdlib crates/modules (std::*, core::*, alloc::*)
- **Go**: 150+ stdlib packages (fmt, os, net/http, encoding/json, etc.)
- **Java**: 20+ stdlib packages (java.util, java.io, javax.swing, etc.)
- **C#**: 15+ stdlib namespaces (System.*, Microsoft.*)
- **Swift**: 15+ stdlib modules (Foundation, UIKit, SwiftUI, Combine, etc.)
- **SQL**: System schemas (information_schema, pg_catalog, sys, etc.)

#### Limitations and Troubleshooting

**False Positives:**
- Comments containing import-like syntax may be parsed if comment detection fails
- Strings containing import-like patterns are filtered but edge cases may occur

**False Negatives:**
- Dynamic/computed imports (e.g., `import(variable)`) are not resolved
- Conditional imports may not be detected
- Generated code or preprocessor directives may not be parsed correctly

**Missing Dependencies:**
- For C/C++: Generated headers or headers in non-standard locations may not resolve
- For Rust: Complex module structures or procedural macros may not resolve
- For HTML/CSS: Dynamically generated asset references won't be detected

**External Dependencies Not Classified:**
- Custom/uncommon standard library modules may be misclassified as third-party
- Vendor-specific SQL extensions may not be recognized as system objects

**Troubleshooting Tips:**
1. Check that file extensions are correctly mapped to languages
2. Verify that include paths are relative to source file or repo root
3. For missing intra-repo edges, check if files exist at expected paths
4. For misclassified external deps, check if module is in stdlib tables
5. Use verbose logging (if available) to see which imports were detected

**Performance Considerations:**
- Large monorepos (10,000+ files) may take several minutes to analyze
- Disable unused languages via `language_config` to improve performance
- Binary files and very large text files are automatically skipped

## Testing

The repository includes a comprehensive test suite with 390+ tests covering all features and edge cases.

### Running Tests

Install development dependencies:
```bash
pip install -e ".[dev]"
```

Run all tests:
```bash
pytest tests/
```

Run specific test files:
```bash
pytest tests/test_file_summary.py
pytest tests/test_dependency_graph.py
pytest tests/test_tree_report.py
```

Run tests with coverage:
```bash
pytest tests/ --cov=repo_analyzer --cov-report=html
```

### Multi-Language Fixtures

The test suite includes representative multi-language fixtures in `tests/fixtures/` that simulate realistic repository combinations:

1. **c_cpp_rust/** - Systems programming with C, C++, and Rust
2. **go_sql/** - Backend service with Go and SQL migrations
3. **html_css_js/** - Frontend web application
4. **swift_csharp/** - Cross-platform mobile/desktop development

These fixtures are used for regression testing to ensure that:
- All language combinations are correctly detected
- Cross-language dependencies are properly tracked
- Schema output remains stable and deterministic
- CLI flows work consistently across language ecosystems

### Running Focused Test Suites

Run only multi-language fixture tests:
```bash
pytest tests/test_multi_language_fixtures.py
```

Run tests for a specific fixture:
```bash
pytest tests/test_multi_language_fixtures.py -k "c_cpp_rust"
pytest tests/test_multi_language_fixtures.py -k "go_sql"
```

Run with verbose output to see individual test details:
```bash
pytest tests/test_multi_language_fixtures.py -v
```

### Test Organization

- **test_file_summary.py** - File detection, language recognition, role classification, metrics
- **test_dependency_graph.py** - Import parsing, dependency resolution, external classification
- **test_tree_report.py** - Directory traversal, tree generation, exclusion patterns
- **test_language_registry.py** - Language registry, extension mapping, priority resolution
- **test_stdlib_classification.py** - Standard library detection across all languages
- **test_multi_language_fixtures.py** - Multi-language combinations, cross-language scenarios

### Contributing Tests

When adding new features:
1. Add fixtures if testing multi-language scenarios
2. Follow existing test patterns (pytest parametrization, tmp_path fixtures)
3. Ensure deterministic output (sorted lists, consistent ordering)
4. Test both success and error paths
5. Run the full test suite before committing

### Edge Cases Covered

The test suite explicitly covers:
- Windows path compatibility (paths under 260 characters)
- OS-specific newline differences (normalized in assertions)
- Parallel test execution (no shared state mutation)
- Missing files and permission errors
- Malformed syntax in source files
- Large files and deep directory structures
- Symlink handling (skipped to avoid infinite loops)

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
- ✅ Multi-language dependency scanner (Markdown + JSON)
  - ✅ Intra-repository dependency graph for Python, JS/TS, C/C++, Rust, HTML/CSS, SQL
  - ✅ External dependency classification for all languages (10+ languages)
  - ✅ Per-file and aggregated external dependency reporting
  - ✅ Deterministic classification without network calls
  - ✅ Comprehensive stdlib/standard library tables for each language
  - ✅ Edge case handling (comments, strings, missing files)

## Error Handling

The tool provides clear error messages and appropriate exit codes:

- **Exit 0**: Successful completion
- **Exit 1**: Configuration or validation error (with descriptive message)
- **Exit 2**: Unexpected runtime error



# Permanents (License, Contributing, Author)

Do not change any of the below sections

## License

This is Licensed under the MIT License - see the LICENSE file for details.

## Contributing

Feel free to submit issues and enhancement requests!

## Author

Created by Agent Foundry and John Brosnihan
