# Multi-Language Repository Analysis Walkthrough

This guide demonstrates how to analyze a multi-language repository using the Repository Analyzer tool, configure language support, and interpret the outputs.

## Prerequisites

Install the repository analyzer:
```bash
pip install -e .
```

For development with test fixtures:
```bash
pip install -e ".[dev]"
```

## Quick Start: Analyzing a Multi-Language Repository

### Default Scan (All Languages)

By default, the analyzer supports 40+ programming languages. To analyze a repository with all languages enabled:

```bash
repo-analyzer scan
```

This generates analysis reports in the `repo-analysis-output/` directory:
- `SUMMARY.md` - Overview with links and statistics
- `tree.md` / `tree.json` - Directory structure
- `file-summaries.md` / `file-summaries.json` - Per-file analysis with role classification and metrics
- `dependencies.md` / `dependencies.json` - Dependency graph with external dependency classification

### Viewing Results

After running the scan, explore the generated outputs:

```bash
# View the summary
cat repo-analysis-output/SUMMARY.md

# View file summaries with metrics
cat repo-analysis-output/file-summaries.md

# View dependency graph
cat repo-analysis-output/dependencies.md
```

## Configuration: Enabling Specific Languages

### Example 1: Analyze Only Python and JavaScript

Create or edit `repo-analyzer.config.json`:

```json
{
  "language_config": {
    "enabled_languages": ["Python", "JavaScript", "TypeScript"]
  }
}
```

Then run the scan:
```bash
repo-analyzer scan --config repo-analyzer.config.json
```

**What happens:**
- Only `.py`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx` files are analyzed
- Other language files are ignored
- File patterns are automatically generated from enabled languages

### Example 2: Exclude Documentation and Config Files

To focus on code and exclude markup/config files:

```json
{
  "language_config": {
    "disabled_languages": ["Markdown", "YAML", "JSON", "TOML", "XML"]
  }
}
```

**What happens:**
- All programming languages remain enabled
- Documentation and configuration files are excluded from analysis

### Example 3: Full-Stack Web Application

For a typical web application with frontend and backend:

```json
{
  "language_config": {
    "enabled_languages": [
      "Python",
      "JavaScript", 
      "TypeScript",
      "HTML",
      "CSS",
      "SQL"
    ]
  }
}
```

### Example 4: Systems Programming

For a systems programming repository with C, C++, and Rust:

```json
{
  "language_config": {
    "enabled_languages": ["C", "C++", "Rust"]
  }
}
```

## Understanding the Outputs

### File Summaries Schema

The `file-summaries.json` output uses **Schema v2.0** with structured information for each file:

```json
{
  "schema_version": "2.0",
  "total_files": 5,
  "files": [
    {
      "schema_version": "2.0",
      "path": "src/main.py",
      "language": "Python",
      "role": "entry-point",
      "role_justification": "common entry point name 'main'",
      "summary": "Python main entry point (role: entry-point)",
      "metrics": {
        "size_bytes": 1024,
        "loc": 45,
        "todo_count": 2
      }
    }
  ]
}
```

**Key Fields:**
- **language**: Detected programming language
- **role**: File purpose (entry-point, test, utility, service, etc.)
- **role_justification**: Explanation of role assignment
- **metrics**: Size, lines of code, TODO count, and declaration count (at detailed level)

### Role Types

Files are automatically classified into roles:
- `entry-point` - Main entry points (main.py, index.js, app.py)
- `test` - Test files and test utilities
- `utility` - Utility and helper functions
- `service` - Service layer implementations
- `api` - API implementations
- `configuration` - Configuration files
- `documentation` - Documentation files
- And [15+ more role types](../README.md#role-types)

### Dependency Analysis

The `dependencies.json` output includes:

**Intra-repository dependencies:**
```json
{
  "edges": [
    {
      "source": "main.py",
      "target": "utils.py"
    }
  ]
}
```

**External dependencies (classified):**
```json
{
  "nodes": [
    {
      "id": "main.py",
      "external_dependencies": {
        "stdlib": ["os", "sys", "json"],
        "third-party": ["requests", "numpy"]
      }
    }
  ],
  "external_dependencies_summary": {
    "stdlib": ["json", "os", "sys"],
    "third-party": ["numpy", "requests"],
    "stdlib_count": 3,
    "third-party_count": 2
  }
}
```

**Classification is deterministic** - no network calls required. The analyzer uses comprehensive built-in tables for:
- Python stdlib (150+ modules)
- Node.js core modules (80+ modules)
- C/C++ standard headers (100+ headers)
- Rust std crates
- Go stdlib packages
- Java/C#/Swift standard libraries
- SQL system schemas

## Advanced Configuration

### Adjusting Detail Level

Control the verbosity of file summaries:

```json
{
  "file_summary_config": {
    "detail_level": "standard"
  }
}
```

**Options:**
- `"minimal"` - Basic fields only (path, language, role)
- `"standard"` - Basic fields + metrics (size, LOC, TODO count) - **default**
- `"detailed"` - All fields including structure with parsed declarations

### Handling Extension Conflicts

Some extensions are shared (e.g., `.h` for C/C++). Control priority:

```json
{
  "language_config": {
    "language_overrides": {
      "C": {"priority": 100}
    }
  }
}
```

This prioritizes C over C++ for `.h` files. Higher priority wins.

### Custom Include Patterns

Override auto-generated patterns:

```json
{
  "file_summary_config": {
    "include_patterns": ["*.py", "*.js", "*.go", "*.rs"]
  }
}
```

**Note:** If `include_patterns` is empty or not specified, patterns are auto-generated from enabled languages.

## Interpreting Results for Multi-Language Repositories

### Example: Mixed Backend and Frontend

For a repository with Python backend and JavaScript frontend:

**File Summaries:**
```
backend/
  main.py (Python, entry-point)
  api.py (Python, api)
  models.py (Python, model)

frontend/
  index.html (HTML, entry-point)
  app.js (JavaScript, entry-point)
  utils.js (JavaScript, utility)
```

**Dependencies:**
- `api.py` → imports from `models.py` (intra-repo)
- `app.js` → imports from `utils.js` (intra-repo)
- `index.html` → references `app.js` (asset reference)
- `main.py` → uses `flask` (third-party), `os` (stdlib)
- `app.js` → uses `axios` (third-party), `fs` (core)

### Language-Specific Features

**Languages with Full Support** (structure parsing + dependency scanning):
- Python, JavaScript, TypeScript

**Languages with Dependency Scanning** (import/include parsing):
- C, C++, C#, Rust, Go, Java, Swift, HTML, CSS, SQL

**Languages with Basic Support** (file detection and metrics):
- Ruby, PHP, Kotlin, Scala, Shell, Bash, and [20+ more](../README.md#supported-languages)

## Troubleshooting

### Issue: No files detected

**Solution:** Check that file extensions are mapped to enabled languages.

```bash
# Verify your configuration
cat repo-analyzer.config.json

# Ensure include_patterns covers your file types
# Or enable the appropriate languages
```

### Issue: Imports not resolved

**Causes:**
- Generated files in non-standard locations
- Complex module structures requiring build context
- Dynamic/computed imports

**Solutions:**
- For C/C++: Ensure headers are in standard locations or specify include directories
- For Rust: Verify module structure follows standard patterns (mod.rs, module.rs)
- For missing third-party packages: This is expected - only intra-repo imports are resolved

### Issue: Wrong language detected for shared extensions

**Solution:** Adjust language priorities:

```json
{
  "language_config": {
    "language_overrides": {
      "C": {"priority": 100},
      "C++": {"priority": 90}
    }
  }
}
```

### Issue: Too many files analyzed

**Solutions:**
1. Disable unused languages:
   ```json
   {
     "language_config": {
       "disabled_languages": ["Markdown", "YAML", "JSON"]
     }
   }
   ```

2. Add exclusion patterns:
   ```json
   {
     "tree_config": {
       "exclude_patterns": [
         ".git", "__pycache__", "node_modules", 
         "dist", "build", "vendor"
       ]
     }
   }
   ```

### Issue: Analysis is slow

**Performance tips:**
1. Enable only needed languages
2. Exclude large generated directories
3. Adjust max file size for parsing:
   ```json
   {
     "file_summary_config": {
       "max_file_size_kb": 512
     }
   }
   ```

## Working in Air-Gapped Environments

The analyzer is designed for offline operation:

- ✅ No network calls required
- ✅ All language detection is deterministic
- ✅ External dependency classification uses built-in tables
- ✅ No package manager invocations

**Limitations in air-gapped environments:**
- Cannot verify if third-party packages are up-to-date
- Cannot resolve external package versions
- Cannot check for security vulnerabilities in dependencies

**Workaround:** Use the analyzer to generate dependency lists, then analyze them separately with security tools.

## Handling Repositories Without Supported Languages

If your repository doesn't contain files in any supported language:

**What happens:**
- Tree structure is still generated
- SUMMARY.md is created with metadata
- File summaries will be empty or show "Unknown" language
- No dependencies are detected

**This is not a failure** - the analyzer still provides directory structure and basic file information.

**To add support for unsupported languages:**
- For basic file detection: Add file extensions to `include_patterns`
- For full support: See [Extending Language Support](../README.md#extending-language-support)

## CI/CD Integration

### Example: GitHub Actions

```yaml
name: Repository Analysis

on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install analyzer
        run: pip install -e .
      
      - name: Run analysis
        run: repo-analyzer scan --output-dir ./analysis-reports
      
      - name: Upload analysis
        uses: actions/upload-artifact@v3
        with:
          name: repo-analysis
          path: ./analysis-reports
```

### Exit Codes

- **0** - Success
- **1** - Configuration or validation error
- **2** - Unexpected runtime error

Use exit codes in CI/CD scripts:
```bash
if repo-analyzer scan; then
  echo "Analysis completed successfully"
else
  echo "Analysis failed with exit code $?"
  exit 1
fi
```

## Preview Mode (Dry Run)

To preview what will be analyzed without writing files:

```bash
repo-analyzer scan --dry-run
```

This shows:
- Which files will be analyzed
- Configuration being used
- Output directory structure

## Next Steps

- Review the [Roadmap](roadmap.md) for planned enhancements
- Check [README.md](../README.md) for detailed configuration options
- Explore [multi-language test fixtures](../tests/fixtures/) for examples
- See [MULTI_LANGUAGE_TESTING.md](../self-analysis/MULTI_LANGUAGE_TESTING.md) for testing details

## Common Workflows

### Workflow 1: Initial Repository Analysis

```bash
# 1. Install the analyzer
pip install -e .

# 2. Run with defaults
repo-analyzer scan

# 3. Review outputs
ls -la repo-analysis-output/
cat repo-analysis-output/SUMMARY.md
```

### Workflow 2: Focused Language Analysis

```bash
# 1. Create custom config
cat > my-config.json << 'EOF'
{
  "language_config": {
    "enabled_languages": ["Python", "JavaScript", "TypeScript"]
  }
}
EOF

# 2. Run with custom config
repo-analyzer scan --config my-config.json --output-dir ./focused-analysis

# 3. View results
cat focused-analysis/file-summaries.md
```

### Workflow 3: Regular Automated Scans

```bash
# Add to your CI/CD pipeline or cron job
#!/bin/bash
set -e

# Navigate to repository
cd /path/to/your/repo

# Run analysis with timestamp
OUTPUT_DIR="analysis-$(date +%Y%m%d-%H%M%S)"
repo-analyzer scan --output-dir "$OUTPUT_DIR"

# Archive results
tar -czf "${OUTPUT_DIR}.tar.gz" "$OUTPUT_DIR"

# Safely remove the directory
if [ -n "$OUTPUT_DIR" ] && [ -d "$OUTPUT_DIR" ]; then
  rm -rf "$OUTPUT_DIR"
fi

echo "Analysis complete: ${OUTPUT_DIR}.tar.gz"
```

## Summary

The Repository Analyzer provides comprehensive multi-language support with:
- 40+ languages supported
- Deterministic, offline operation
- Configurable language selection
- Automatic role classification
- External dependency classification
- CI/CD friendly design

No environment variables or secrets are required - see [.env.example](../.env.example) for details.
