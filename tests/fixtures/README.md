# Test Fixtures

This directory contains multi-language test fixtures for regression testing.

## Fixture Structure

Each fixture represents a realistic multi-language repository combination:

### 1. c_cpp_rust/
Simulates a systems programming project mixing C, C++, and Rust:
- **C files**: Entry point (main.c), utilities with headers
- **C++ files**: Modern C++ with STL usage
- **Rust files**: Library crate with module structure
- **Use case**: Cross-language systems development

### 2. go_sql/
Represents a backend application with database migrations:
- **Go files**: Main application, test files
- **SQL files**: Schema definitions, migrations, queries
- **Use case**: Database-backed web service

### 3. html_css_js/
Models a frontend web application:
- **HTML**: Entry point with references to assets
- **CSS**: Main stylesheet and component styles
- **JavaScript**: ES6 modules with imports/exports
- **Use case**: Single-page web application

### 4. swift_csharp/
Demonstrates mixed mobile/desktop development:
- **Swift files**: iOS app structure (AppDelegate, ViewControllers, Models)
- **C# files**: Backend services and interfaces
- **Use case**: Cross-platform application with different tech stacks

## Fixture Design Principles

1. **Minimal but Representative**: Each fixture contains the smallest set of files that demonstrates key language features
2. **Realistic Patterns**: Files follow common naming and structure conventions for each language
3. **Cross-references**: Files include imports/includes to test dependency resolution
4. **Edge Cases**: Include TODOs, FIXMEs, nested directories where applicable
5. **Path Compatibility**: Avoid excessively long paths that break Windows (kept under 260 chars)
6. **Pure Static**: No external dependencies, network access, or toolchain requirements

## Usage in Tests

These fixtures are used by:
- `test_file_summary.py` - Tests file role detection and language-specific heuristics
- `test_dependency_graph.py` - Tests cross-language dependency tracking
- `test_tree_report.py` - Tests directory tree generation with mixed file types

## Maintenance

When modifying fixtures:
1. Keep files small (< 50 LOC each)
2. Ensure deterministic content (no timestamps, random values)
3. Update this README if adding new fixtures
4. Run full test suite to verify no regressions
