# Dependency Graph

Intra-repository dependency analysis for Python and JavaScript/TypeScript files.

Includes classification of external dependencies as stdlib vs third-party.

## Statistics

- **Total files**: 10
- **Intra-repo dependencies**: 9
- **External stdlib dependencies**: 17
- **External third-party dependencies**: 1

## External Dependencies

### Standard Library / Core Modules

Total: 17 unique modules

- `argparse`
- `ast`
- `json`
- `os`
- `pathlib.Path`
- `pathlib.PurePosixPath`
- `re`
- `subprocess`
- `sys`
- `tempfile`
- `typing.Any`
- `typing.Dict`
- `typing.List`
- `typing.Literal`
- `typing.Optional`
- `typing.Set`
- `typing.Tuple`

### Third-Party Packages

Total: 1 unique packages

- `pytest`

## Most Depended Upon Files (Intra-Repo)

- `repo_analyzer/dependency_graph.py` (3 dependents)
- `repo_analyzer/tree_report.py` (2 dependents)
- `repo_analyzer/file_summary.py` (2 dependents)
- `repo_analyzer/stdlib_classification.py` (2 dependents)

## Files with Most Dependencies (Intra-Repo)

- `repo_analyzer/cli.py` (3 dependencies)
- `repo_analyzer/dependency_graph.py` (1 dependencies)
- `repo_analyzer/file_summary.py` (1 dependencies)
- `tests/test_dependency_graph.py` (1 dependencies)
- `tests/test_file_summary.py` (1 dependencies)
- `tests/test_stdlib_classification.py` (1 dependencies)
- `tests/test_tree_report.py` (1 dependencies)
