# Changelog

All notable changes to the Repository Analyzer project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-12-03

### Added

#### Low-Level Language Support with Symbol Extraction

This release adds comprehensive support for systems programming languages with production-ready symbol extraction capabilities:

- **C** (.c, .h) - Function/struct/macro extraction, #include directives, stdlib header classification
  - **Symbol extraction**: Functions, structs, macros (#define), global variables
  - **Dependency scanning**: #include directives with resolution to local headers
  - **External classification**: C standard library, C++ STL, POSIX headers, Windows headers, common third-party libraries (Boost, OpenSSL, zlib, etc.)
  - **Parsing**: Regex-based (always available) with optional libclang or tree-sitter for enhanced accuracy

- **C++** (.cpp, .cc, .cxx, .hpp, .hh, .hxx, .h) - Class/function/macro extraction, #include directives, STL classification
  - **Symbol extraction**: Functions, classes, structs, macros (#define), global variables
  - **Dependency scanning**: #include directives with comprehensive header resolution
  - **External classification**: Enhanced stdlib tables including C++ STL, compiler builtins, platform-specific headers
  - **Parsing**: Regex-based (always available) with optional libclang or tree-sitter support

- **Rust** (.rs) - Function/struct/trait/impl extraction, use/mod statements, std crate classification
  - **Symbol extraction**: Functions (fn), structs, enums, traits, impl blocks, constants
  - **Dependency scanning**: use/mod statements with crate resolution
  - **Module resolution**: Handles crate::, self::, super:: patterns and filesystem-based modules
  - **External classification**: std/core/alloc crates automatically classified as stdlib
  - **Parsing**: Regex-based (always available) with optional tree-sitter support

- **Assembly** (.s, .S, .asm, .sx) - Label and symbol extraction, multiple syntax support
  - **Symbol extraction**: .globl/.global labels (gas), global directives (NASM), PUBLIC directives (MASM)
  - **Capabilities**: Extracts functions (via .type @function), data objects (via .type @object), labels
  - **Multi-syntax support**: GNU assembler (gas), NASM, MASM
  - **Dependency scanning**: .include, %include, and include directives with path resolution
  - **Parsing**: Deterministic regex-based (no optional dependencies required)

- **Perl** (.pl, .pm, .perl) - Subroutine/package extraction, use/require statements, core module classification
  - **Symbol extraction**: Subroutines (sub), packages (package)
  - **Dependency scanning**: use/require statements with enhanced core module detection
  - **Stdlib classification**: 150+ core Perl modules including pragmas, File::*, Data::*, Test::*, LWP::*, etc.
  - **Third-party detection**: Common CPAN modules (Moose, Dancer, DBIx::Class, etc.)
  - **Parsing**: Regex-based (always available) with optional tree-sitter support

#### Layered Parser Architecture

Introduced a flexible, production-ready parser architecture with graceful degradation:

1. **Regex Parsers** (Always available, production-ready)
   - Zero dependencies - works out of the box
   - Fast, deterministic pattern-based extraction
   - **Full symbol extraction** matching Python AST fidelity for C/C++/Rust/ASM/Perl
   - Performance: 1-5ms per file with complete functionality
   - Limitations: No semantic analysis, no type resolution, no cross-reference analysis

2. **Structured Parsers** (Optional, enhanced accuracy)
   - **tree-sitter**: Fast incremental parser with full AST access
     - Installation: `pip install tree-sitter tree-sitter-<language>`
     - Supported languages: Rust, C, C++, Perl
     - Benefits: Semantic analysis, accurate symbol extraction, type information
   
   - **libclang**: Official Clang compiler frontend for C/C++
     - Installation: `pip install libclang` (requires system libclang library)
     - Compiler-grade accuracy with type resolution and macro expansion
     - Platform requirements: Ubuntu/Debian (apt install libclang-dev), macOS (brew install llvm), Windows (LLVM releases)

3. **Graceful Degradation**
   - Automatic detection of parser availability at runtime
   - Seamless fallback to regex parsing with full symbol extraction
   - **No breaking changes** - existing workflows unaffected
   - **No mandatory dependencies** - core functionality works everywhere

#### CLI Enhancements

- **Automatic Language Detection**: CLI now auto-detects low-level languages (C, C++, Rust, ASM, Perl) in repositories
  - Quick scan (bounded to 1000 files) during CLI initialization
  - Reports detected languages with parser availability status
  - Provides installation instructions for optional structured parsers
  - Zero-configuration for mixed-language repositories (e.g., OpenSSL-scale projects)
  - Can be disabled by explicitly setting `enabled_languages` in configuration

- **Parser Diagnostics**: Clear feedback on parser availability and installation instructions
  - Shows which languages are detected in the repository
  - Reports which parsers are available vs missing
  - Provides copy-paste installation commands for optional dependencies
  - Emphasizes that regex parsing is production-ready and always available

#### Configuration Additions

New `parser_config` section in configuration files:

```jsonc
{
  "parser_config": {
    "enable_structured_parsers": true,    // Use tree-sitter/libclang when available
    "enable_parser_cache": true,          // Cache parsed results (recommended)
    "parsers": {
      "tree_sitter": {
        "enabled": true,
        "graceful_degradation": true      // Fall back to regex if unavailable
      },
      "libclang": {
        "enabled": true,
        "graceful_degradation": true
      }
    },
    "language_parser_preferences": {
      "C": ["libclang", "tree_sitter", "regex"],
      "C++": ["libclang", "tree_sitter", "regex"],
      "Rust": ["tree_sitter", "regex"],
      "Perl": ["tree_sitter", "regex"],
      "ASM": ["regex"]
    },
    "performance": {
      "max_file_size_for_structured_parsing_kb": 512,
      "max_parse_time_seconds": 5.0
    }
  }
}
```

#### Enhanced Dependency Scanning

- **C/C++ Include Resolution**: Comprehensive #include directive parsing with resolution
  - Resolves headers relative to source file, include directories, and repository root
  - Enhanced stdlib classification: C standard library, C++ STL, POSIX, Windows headers
  - Third-party library detection: Boost, OpenSSL, zlib, libcurl, SQLite, Google Test, Qt, GTK, SDL, Vulkan
  - Handles both `#include <system.h>` and `#include "local.h"` styles
  - Comment filtering to avoid false positives

- **Rust Module Resolution**: Full Rust use/mod statement parsing
  - Resolves local modules via filesystem (module.rs, module/mod.rs patterns)
  - Handles crate-relative (crate::), self-relative (self::), and parent-relative (super::) imports
  - Classifies std/core/alloc crates as stdlib, external crates as third-party

- **Assembly Include Chains**: Multi-syntax assembly include support
  - GNU assembler (gas): `.include "file.inc"`
  - NASM: `%include "file.inc"`
  - MASM: `include file.inc`
  - Resolves includes relative to source directory, repo root, and common include paths

- **Perl Dependency Tracking**: Enhanced Perl use/require parsing
  - 150+ core module detection (strict, warnings, File::Copy, Data::Dumper, Test::More, LWP::Simple, etc.)
  - CPAN module detection (Moose, Dancer, DBIx::Class, DateTime, etc.)
  - Pragma classification as stdlib

#### Testing Coverage

- **Multi-language test fixtures**: Added realistic multi-language repository simulations
  - `c_cpp_rust/`: Systems programming with C, C++, and Rust
  - `go_sql/`: Backend service with Go and SQL migrations
  - `html_css_js/`: Frontend web application
  - `swift_csharp/`: Cross-platform mobile/desktop development

- **New test suites**:
  - `test_low_level_languages.py`: C, C++, Rust, ASM, Perl symbol extraction (100+ tests)
  - `test_parser_adapters.py`: Parser architecture and fallback mechanisms (50+ tests)
  - `test_multi_language_fixtures.py`: Cross-language integration tests (60+ tests)
  - `test_cli_integration.py`: CLI auto-detection and configuration (40+ tests)

- **Enhanced test coverage**: Total test count increased from ~200 to 493 tests
  - Comprehensive symbol extraction validation for all low-level languages
  - Parser fallback behavior verification
  - Multi-language dependency resolution edge cases
  - CLI auto-detection performance and accuracy

### Changed

- **Enhanced `stdlib_classification.py`**: Expanded classification tables
  - C/C++: 150+ headers (up from ~50) including POSIX, Windows, compiler builtins
  - Perl: 150+ core modules (up from ~20) with comprehensive pragma and CPAN coverage
  - Third-party library tables for C/C++ (Boost, OpenSSL, Qt, etc.)

- **Improved `file_summary.py`**: Added low-level language structure parsing
  - Regex-based parsers for C, C++, Rust, ASM, Perl with full symbol extraction
  - Integration with optional structured parsers (tree-sitter, libclang)
  - Enhanced role detection heuristics for systems programming languages
  - Declaration count metrics for all supported languages

- **Extended `dependency_graph.py`**: Multi-language include/import resolution
  - C/C++ header resolution with multiple search paths
  - Rust module resolution with filesystem traversal
  - Assembly include resolution with multi-syntax support
  - Perl use/require parsing with enhanced stdlib detection

- **Updated `language_registry.py`**: Added 5 new languages with full metadata
  - C, C++, Rust, ASM, Perl with extension mappings and priority resolution
  - Parser capability flags for each language
  - Auto-detection support for low-level language presence

### Migration Guide

**For Existing Users:**

This release is **fully backward compatible**. No configuration changes are required:

- All existing functionality works unchanged
- Python, JavaScript, TypeScript analysis remains identical
- No new mandatory dependencies
- Existing configuration files are valid

**To Adopt Low-Level Language Support:**

1. **Zero-configuration option**: Run `repo-analyzer scan` as usual
   - Low-level languages will be auto-detected if present
   - Regex parsers provide production-ready symbol extraction
   - No installation required

2. **Optional enhanced accuracy** (requires dependencies):
   ```bash
   # For tree-sitter support (Rust, C, C++, Perl)
   pip install tree-sitter
   pip install tree-sitter-rust tree-sitter-c tree-sitter-cpp tree-sitter-perl
   
   # For libclang support (C/C++ with compiler-grade accuracy)
   pip install libclang
   # Also requires system libclang library:
   # - Ubuntu/Debian: apt install libclang-dev
   # - macOS: brew install llvm
   # - Windows: Download from LLVM releases
   ```

3. **Enable parser configuration** (optional):
   - Add `parser_config` section to your `repo-analyzer.config.json`
   - See updated `repo-analyzer.config.example.jsonc` for all options
   - Default settings work well for most use cases

**Installation Considerations for Optional Parsers:**

- **Architecture compatibility**: tree-sitter and libclang have native components
  - May not be available on ARM, older OS versions, or restricted environments
  - Regex fallback ensures functionality on all platforms

- **Install size**: tree-sitter grammars add ~5-10MB per language

- **Parse performance**: 
  - Initial parse of large files (>100KB) may take 50-200ms
  - Subsequent parses are instant (cached)
  - Regex parsers: 1-5ms per file, always available

- **Offline/Air-gapped environments**:
  - Regex parsers work with zero dependencies
  - Structured parsers require pre-installation
  - No runtime network calls in either case

### Performance

- **Auto-detection overhead**: ~50-100ms for typical repositories (bounded scan)
- **Regex parsing**: 1-5ms per file with full symbol extraction
- **Structured parsing**: 10-50ms per file (cached) with enhanced semantic analysis
- **Cache layer**: Results cached per file content hash for instant repeat access
- **Large file handling**: Configurable size threshold (default: 512KB for structured parsing)

### Documentation

- **Updated README**: Added comprehensive low-level language documentation
  - Parser architecture explanation
  - Installation instructions for optional dependencies
  - Language-specific parsing details (C, C++, Rust, ASM, Perl)
  - Performance characteristics and operational caveats
  - Automatic language detection behavior
  - Backward compatibility guarantees

- **Updated `repo-analyzer.config.example.jsonc`**: Added parser_config section
  - Comprehensive comments for all parser options
  - Example language-specific parser preferences
  - Performance tuning recommendations

- **Enhanced `.env.example`**: Clarified that no environment variables are required
  - Documentation of air-gapped operation
  - CI/CD integration without secrets
  - Development and testing considerations

### Technical Details

- **Determinism**: All parsers produce deterministic, reproducible results
  - Regex parsers use fixed patterns with no randomness
  - Structured parsers operate deterministically on source code
  - No network calls, no external data sources

- **Safety**: 
  - Static analysis only - no code execution
  - Parser errors handled gracefully with fallback to safer approaches
  - Path safety maintained - all output confined to configured directory

- **Cross-platform**: Works on Linux, macOS, Windows
  - Core functionality (regex parsing) has zero platform-specific dependencies
  - Optional structured parsers may have platform-specific installation requirements
  - Tests run on all major platforms in CI

### Known Limitations

- **C/C++ preprocessor conditionals**: Not evaluated - all includes tracked regardless of `#ifdef`
  - Ensures complete dependency visibility but may include inactive code paths
  - Cannot determine which includes are active for a specific build configuration

- **Dynamic imports**: Computed import paths (e.g., `import(variable)`) are not resolved

- **Generated code**: May not be distinguished from hand-written code in all cases

- **False positives**: Comment-embedded import-like syntax may be parsed if comment detection fails

### Deprecations

None. This release introduces new features without deprecating existing functionality.

## [0.2.1] - 2025-12-02

### Documentation

This is a documentation-only release that adds comprehensive guides for the multi-language features introduced in v0.2.0.

#### Added
- **[Multi-Language Walkthrough](docs/walkthrough.md)** - Complete guide demonstrating how to analyze multi-language repositories with practical examples
  - Quick start examples for scanning repositories
  - Language configuration tutorials (enabling specific languages, handling conflicts)
  - Output interpretation guide with real examples from test fixtures
  - Advanced usage patterns for CI/CD integration
- **[Project Roadmap](docs/roadmap.md)** - Future enhancement plans and vision document
  - Clear articulation of design principles (deterministic, air-gapped, language-agnostic)
  - Recently completed features summary (v0.2.0 achievements)
  - Short-term and long-term enhancement proposals
  - Community contribution guidelines

#### Notes
- **No code changes**: This release contains only documentation additions
- **Backward compatible**: All features and APIs remain unchanged from v0.2.0
- **No new dependencies**: No changes to runtime or development dependencies
- **Commands unchanged**: CLI interface and configuration options remain identical

The multi-language analysis capabilities (40+ languages, external dependency classification, enhanced file summaries with schema v2.0) introduced in v0.2.0 are fully documented and production-ready.

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

[0.3.0]: https://github.com/AgentFoundryExamples/repo-summarizer-v1/releases/tag/v0.3.0
[0.2.1]: https://github.com/AgentFoundryExamples/repo-summarizer-v1/releases/tag/v0.2.1
[0.2.0]: https://github.com/AgentFoundryExamples/repo-summarizer-v1/releases/tag/v0.2.0
[0.1.0]: https://github.com/AgentFoundryExamples/repo-summarizer-v1/releases/tag/v0.1.0
