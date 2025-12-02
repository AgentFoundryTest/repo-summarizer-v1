# Dependency Graph

Intra-repository dependency analysis for Python and JavaScript/TypeScript files.

Includes classification of external dependencies as stdlib vs third-party.

## Statistics

- **Total files**: 12
- **Intra-repo dependencies**: 13
- **External stdlib dependencies**: 19
- **External third-party dependencies**: 1

## External Dependencies

### Standard Library / Core Modules

Total: 19 unique modules

- `argparse`
- `ast`
- `dataclasses.dataclass`
- `dataclasses.field`
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

- `repo_analyzer/file_summary.py` (3 dependents)
- `repo_analyzer/dependency_graph.py` (3 dependents)
- `repo_analyzer/language_registry.py` (3 dependents)
- `repo_analyzer/tree_report.py` (2 dependents)
- `repo_analyzer/stdlib_classification.py` (2 dependents)

## Files with Most Dependencies (Intra-Repo)

- `repo_analyzer/cli.py` (4 dependencies)
- `repo_analyzer/file_summary.py` (2 dependencies)
- `tests/test_language_registry.py` (2 dependencies)
- `repo_analyzer/dependency_graph.py` (1 dependencies)
- `tests/test_dependency_graph.py` (1 dependencies)
- `tests/test_file_summary.py` (1 dependencies)
- `tests/test_stdlib_classification.py` (1 dependencies)
- `tests/test_tree_report.py` (1 dependencies)
