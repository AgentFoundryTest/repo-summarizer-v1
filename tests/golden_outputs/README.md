# Golden Outputs

This directory contains reference outputs ("golden files") for regression testing.

## Purpose

Golden outputs serve as a baseline to detect unintended changes in analyzer output. When the analyzer's output format or heuristics change intentionally, these files should be updated.

## Structure

```
golden_outputs/
├── c_cpp_rust/
│   ├── file-summaries.json
│   ├── dependencies.json
│   └── tree.json
├── go_sql/
├── html_css_js/
└── swift_csharp/
```

Each fixture has corresponding golden output files that represent the expected, stable output.

## Updating Golden Files

Golden files should be updated when:
1. **Intentional changes** are made to output formats, schemas, or heuristics
2. **New features** are added that enhance output quality
3. **Bug fixes** correct incorrect behavior

Golden files should **NOT** be updated when:
- Tests fail due to actual regressions
- Changes are accidental or unreviewed

### How to Refresh Golden Files

```bash
# Generate fresh outputs from fixtures
pytest tests/test_multi_language_fixtures.py -v

# Manually review the generated outputs in /tmp/pytest-*/
# If changes are expected and correct, copy to golden_outputs/

# Or use the update script (if implemented):
# python tests/update_golden_outputs.py
```

## Testing Against Golden Files

Golden file tests ensure output stability:
- Compare generated JSON structure against reference files
- Verify deterministic field ordering
- Check that schema versions remain compatible
- Validate that file counts and language detection are consistent

## OS Compatibility

Golden files are normalized to handle:
- **Line endings**: LF (Unix) format, automatically converted on Windows
- **Path separators**: Forward slashes (POSIX) for portability
- **Timestamps**: Not included in golden files (non-deterministic)
- **Absolute paths**: Relative to repository root

## Future Enhancements

Potential improvements to golden file testing:
1. **Automated refresh script**: Generate and update golden files with a single command
2. **Diff reporting**: Show exactly what changed when tests fail
3. **Snapshot library integration**: Use pytest-snapshot or similar for inline snapshots
4. **Semantic comparison**: Compare structure/content rather than exact byte matches
