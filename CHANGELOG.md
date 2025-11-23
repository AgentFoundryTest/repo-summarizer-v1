# Changelog

All notable changes to the Repository Analyzer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-11-23

### Added

#### Structured File Summaries (Schema v2.0)
- **Role-based classification**: Automatic file categorization into 17+ role types (test, entry-point, configuration, cli, utility, model, controller, view, service, api, component, etc.)
- **Role justifications**: Each file includes an explanation of why it was assigned its role, improving transparency and trust
- **Configurable detail levels**: Three output modes to control verbosity
  - `minimal`: Basic fields only (path, language, role, role_justification, summary)
  - `standard`: Adds metrics (file size, LOC, TODO count) - **default and recommended**
  - `detailed`: Includes structure with parsed declarations and external dependencies
- **Language-aware parsing**: Static analysis for Python (AST) and JavaScript/TypeScript (regex patterns)
  - Extracts top-level functions, classes, and exports
  - No code execution - completely safe static analysis
  - Graceful handling of syntax errors with warning messages
- **Metrics tracking**: Lines of code (LOC), TODO/FIXME count, declaration count, file size
- **Backward compatibility**: `include_legacy_summary` option maintains v1.0 field compatibility

#### External Dependency Classification
- **Automatic classification**: Distinguishes between standard library and third-party packages
- **Deterministic operation**: No network calls or package manager invocations required
- **Comprehensive tables**: 100+ Python stdlib modules, 70+ Node.js core modules
- **Per-file tracking**: Each file node includes its external dependencies in the dependency graph
- **Aggregated reporting**: Summary counts and deduplicated lists of all external dependencies
- **Multi-ecosystem support**: Python and JavaScript/TypeScript dependency classification

#### Enhanced Dependency Graph
- **External dependencies**: Dependency graph now includes stdlib vs third-party classification
- **Enriched nodes**: Each file node includes `external_dependencies` with `stdlib` and `third-party` arrays
- **Summary statistics**: Top-level `external_dependencies_summary` with counts and deduplicated lists
- **Deterministic output**: Dependencies are sorted and deduplicated for consistent results

### Configuration Options

New configuration options in `file_summary_config`:
```json
{
  "detail_level": "standard",           // "minimal" | "standard" | "detailed"
  "include_legacy_summary": true,       // Include v1.0 compatible fields
  "max_file_size_kb": 1024             // Skip expensive parsing for large files
}
```

### Migration from v1.0

The v2.0 schema is **backward compatible by default**. Existing consumers of v1.0 format will continue to work:
- Core fields (`total_files`, `files`, `path`, `language`, `summary`) remain unchanged
- New fields can be safely ignored by v1.0 parsers
- Set `include_legacy_summary: false` only if you want a cleaner v2.0-only format

To leverage v2.0 features:
1. Check `schema_version` field to detect format version
2. Use `role` and `role_justification` for intelligent file filtering
3. Access `metrics` for quantitative analysis
4. Use `structure.declarations` (detailed level) for code structure insights
5. Analyze `dependencies.external` (detailed level) for dependency auditing

### Technical Details

- **Determinism**: All heuristics and classification logic is deterministic and reproducible
- **Safety**: Static analysis only - no code execution, no network calls
- **Performance**: Large files (>1024 KB) skip expensive parsing but still provide basic metrics
- **Error handling**: Syntax errors and parsing failures are gracefully handled with warnings
- **Path safety**: All output confined to configured output directory

### Documentation

- Comprehensive README updates with schema documentation, examples, and migration guide
- Detailed configuration reference for all new options
- Role detection heuristics fully documented
- External dependency classification explained
- Sample outputs provided for each detail level

## [0.1.0] - 2025-11-23

### Initial Release

- **CLI infrastructure**: Non-interactive command-line interface for CI/CD integration
- **Configuration system**: Support for config files and CLI arguments with precedence rules
- **Tree generation**: Directory structure reports in Markdown and JSON formats
- **File summaries**: Basic file analysis with language detection and summaries
- **Dependency scanning**: Intra-repository dependency graph for Python and JavaScript/TypeScript
- **Dry-run mode**: Preview operations without writing files
- **Path validation**: Safe output directory handling
- **Deterministic operation**: Consistent, reproducible results

### Core Features

- Directory tree visualization with configurable exclusions and depth limits
- File-by-file analysis with language detection
- Import/require statement parsing for dependency graphs
- JSON and Markdown output formats for all reports
- Comprehensive test coverage with pytest

[0.2.0]: https://github.com/AgentFoundryTest/repo-summarizer-v1/releases/tag/v0.2.0
[0.1.0]: https://github.com/AgentFoundryTest/repo-summarizer-v1/releases/tag/v0.1.0
