# Copyright (c) 2025 John Brosnihan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Multi-language fixture tests for comprehensive regression coverage.

These tests exercise the analyzer against realistic multi-language repositories
to ensure that future changes don't regress support for language combinations.
"""

import json
from pathlib import Path

import pytest

from repo_analyzer.file_summary import generate_file_summaries
from repo_analyzer.dependency_graph import generate_dependency_report
from repo_analyzer.tree_report import generate_tree_report


# Fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
C_CPP_RUST_FIXTURE = FIXTURES_DIR / "c_cpp_rust"
GO_SQL_FIXTURE = FIXTURES_DIR / "go_sql"
HTML_CSS_JS_FIXTURE = FIXTURES_DIR / "html_css_js"
SWIFT_CSHARP_FIXTURE = FIXTURES_DIR / "swift_csharp"


# Parametrize all multi-language fixtures
FIXTURES = [
    pytest.param(
        C_CPP_RUST_FIXTURE,
        {"C", "C++", "Rust"},
        6,  # Expected file count
        id="c_cpp_rust"
    ),
    pytest.param(
        GO_SQL_FIXTURE,
        {"Go", "SQL"},
        5,  # Expected file count
        id="go_sql"
    ),
    pytest.param(
        HTML_CSS_JS_FIXTURE,
        {"HTML", "CSS", "JavaScript"},
        5,  # Expected file count
        id="html_css_js"
    ),
    pytest.param(
        SWIFT_CSHARP_FIXTURE,
        {"Swift", "C#"},
        5,  # Expected file count
        id="swift_csharp"
    ),
]


@pytest.mark.parametrize("fixture_path,expected_languages,expected_file_count", FIXTURES)
class TestMultiLanguageFileSummary:
    """Test file summary generation across multi-language fixtures."""
    
    def test_detects_all_languages(self, tmp_path, fixture_path, expected_languages, expected_file_count):
        """Test that all languages in the fixture are detected."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")
        
        output = tmp_path / "output"
        output.mkdir()
        
        # Generate file summaries
        generate_file_summaries(
            fixture_path,
            output,
            include_patterns=["*.*"],  # All files
            detail_level="standard"
        )
        
        # Read generated JSON
        json_file = output / "file-summaries.json"
        assert json_file.exists(), "file-summaries.json not generated"
        
        data = json.loads(json_file.read_text())
        
        # Check all expected languages are present
        detected_languages = {entry["language"] for entry in data["files"]}
        assert expected_languages.issubset(detected_languages), \
            f"Expected languages {expected_languages} not all detected. Found: {detected_languages}"
    
    def test_file_count_matches_expected(self, tmp_path, fixture_path, expected_languages, expected_file_count):
        """Test that the correct number of files is detected."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_file_summaries(
            fixture_path,
            output,
            include_patterns=["*.*"],
            detail_level="standard"
        )
        
        json_file = output / "file-summaries.json"
        data = json.loads(json_file.read_text())
        
        assert data["total_files"] == expected_file_count, \
            f"Expected {expected_file_count} files, got {data['total_files']}"
        assert len(data["files"]) == expected_file_count
    
    def test_schema_version_present(self, tmp_path, fixture_path, expected_languages, expected_file_count):
        """Test that schema version is present in all entries."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_file_summaries(
            fixture_path,
            output,
            include_patterns=["*.*"],
            detail_level="standard"
        )
        
        json_file = output / "file-summaries.json"
        data = json.loads(json_file.read_text())
        
        # Check top-level schema version
        assert "schema_version" in data
        assert data["schema_version"] == "2.0"
        
        # Check per-file schema version
        for entry in data["files"]:
            assert "schema_version" in entry
            assert entry["schema_version"] == "2.0"
    
    def test_roles_assigned_to_all_files(self, tmp_path, fixture_path, expected_languages, expected_file_count):
        """Test that all files have roles and justifications."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_file_summaries(
            fixture_path,
            output,
            include_patterns=["*.*"],
            detail_level="standard"
        )
        
        json_file = output / "file-summaries.json"
        data = json.loads(json_file.read_text())
        
        for entry in data["files"]:
            assert "role" in entry, f"Role missing for {entry['path']}"
            assert "role_justification" in entry, f"Role justification missing for {entry['path']}"
            assert entry["role"], f"Role empty for {entry['path']}"
            assert entry["role_justification"], f"Role justification empty for {entry['path']}"
    
    def test_metrics_present_at_standard_level(self, tmp_path, fixture_path, expected_languages, expected_file_count):
        """Test that metrics are present at standard detail level."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_file_summaries(
            fixture_path,
            output,
            include_patterns=["*.*"],
            detail_level="standard"
        )
        
        json_file = output / "file-summaries.json"
        data = json.loads(json_file.read_text())
        
        for entry in data["files"]:
            assert "metrics" in entry, f"Metrics missing for {entry['path']}"
            assert "size_bytes" in entry["metrics"]
            assert "loc" in entry["metrics"]
            assert "todo_count" in entry["metrics"]
            assert entry["metrics"]["size_bytes"] > 0, f"Size should be > 0 for {entry['path']}"
    
    def test_deterministic_ordering(self, tmp_path, fixture_path, expected_languages, expected_file_count):
        """Test that file ordering is deterministic across runs."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")
        
        output = tmp_path / "output"
        output.mkdir()
        
        # Generate twice
        generate_file_summaries(fixture_path, output, include_patterns=["*.*"], detail_level="standard")
        json_file = output / "file-summaries.json"
        data1 = json.loads(json_file.read_text())
        paths1 = [entry["path"] for entry in data1["files"]]
        
        json_file.unlink()
        
        generate_file_summaries(fixture_path, output, include_patterns=["*.*"], detail_level="standard")
        data2 = json.loads(json_file.read_text())
        paths2 = [entry["path"] for entry in data2["files"]]
        
        # Should be identical
        assert paths1 == paths2, "File ordering is not deterministic"
        
        # Should be sorted
        assert paths1 == sorted(paths1), "Files are not sorted"
    
    def test_markdown_output_generated(self, tmp_path, fixture_path, expected_languages, expected_file_count):
        """Test that markdown output is generated and contains expected content."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_file_summaries(
            fixture_path,
            output,
            include_patterns=["*.*"],
            detail_level="standard"
        )
        
        md_file = output / "file-summaries.md"
        assert md_file.exists(), "file-summaries.md not generated"
        
        content = md_file.read_text()
        
        # Should contain schema version
        assert "Schema Version: 2.0" in content
        
        # Should contain file count
        assert f"Total files: {expected_file_count}" in content
        
        # Should contain role information
        assert "**Role:**" in content


@pytest.mark.parametrize("fixture_path,expected_languages,expected_file_count", FIXTURES)
class TestMultiLanguageDependencyGraph:
    """Test dependency graph generation across multi-language fixtures."""
    
    def test_graph_nodes_created(self, tmp_path, fixture_path, expected_languages, expected_file_count):
        """Test that all files appear as nodes in the dependency graph."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            fixture_path,
            output,
            include_patterns=["*.*"]
        )
        
        json_file = output / "dependencies.json"
        assert json_file.exists(), "dependencies.json not generated"
        
        data = json.loads(json_file.read_text())
        
        # Should have nodes for all files
        assert len(data["nodes"]) == expected_file_count, \
            f"Expected {expected_file_count} nodes, got {len(data['nodes'])}"
        
        # All nodes should have required fields
        for node in data["nodes"]:
            assert "id" in node
            assert "path" in node
            assert "type" in node
            assert node["type"] == "file"
    
    def test_external_dependencies_tracked(self, tmp_path, fixture_path, expected_languages, expected_file_count):
        """Test that external dependencies are tracked and classified."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            fixture_path,
            output,
            include_patterns=["*.*"]
        )
        
        json_file = output / "dependencies.json"
        data = json.loads(json_file.read_text())
        
        # Should have external dependencies summary
        assert "external_dependencies_summary" in data
        assert "stdlib" in data["external_dependencies_summary"]
        assert "third-party" in data["external_dependencies_summary"]
        assert "stdlib_count" in data["external_dependencies_summary"]
        assert "third-party_count" in data["external_dependencies_summary"]
        
        # Per-node external dependencies
        for node in data["nodes"]:
            assert "external_dependencies" in node
            assert "stdlib" in node["external_dependencies"]
            assert "third-party" in node["external_dependencies"]
            assert isinstance(node["external_dependencies"]["stdlib"], list)
            assert isinstance(node["external_dependencies"]["third-party"], list)
    
    def test_edges_are_deterministic(self, tmp_path, fixture_path, expected_languages, expected_file_count):
        """Test that dependency edges are deterministic."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")
        
        output = tmp_path / "output"
        output.mkdir()
        
        # Generate twice
        generate_dependency_report(fixture_path, output, include_patterns=["*.*"])
        json_file = output / "dependencies.json"
        data1 = json.loads(json_file.read_text())
        edges1 = sorted([(e["source"], e["target"]) for e in data1["edges"]])
        
        json_file.unlink()
        
        generate_dependency_report(fixture_path, output, include_patterns=["*.*"])
        data2 = json.loads(json_file.read_text())
        edges2 = sorted([(e["source"], e["target"]) for e in data2["edges"]])
        
        # Should be identical
        assert edges1 == edges2, "Dependency edges are not deterministic"
    
    def test_markdown_report_generated(self, tmp_path, fixture_path, expected_languages, expected_file_count):
        """Test that markdown dependency report is generated."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            fixture_path,
            output,
            include_patterns=["*.*"]
        )
        
        md_file = output / "dependencies.md"
        assert md_file.exists(), "dependencies.md not generated"
        
        content = md_file.read_text()
        
        # Should contain standard sections
        assert "Dependency Graph" in content
        assert "Statistics" in content
        assert "External Dependencies" in content


@pytest.mark.parametrize("fixture_path,expected_languages,expected_file_count", FIXTURES)
class TestMultiLanguageTreeReport:
    """Test tree report generation across multi-language fixtures."""
    
    def test_tree_structure_created(self, tmp_path, fixture_path, expected_languages, expected_file_count):
        """Test that tree structure is created correctly."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_tree_report(fixture_path, output)
        
        json_file = output / "tree.json"
        assert json_file.exists(), "tree.json not generated"
        
        data = json.loads(json_file.read_text())
        
        # Should have root directory
        assert data["type"] == "directory"
        assert "children" in data
    
    def test_all_files_in_tree(self, tmp_path, fixture_path, expected_languages, expected_file_count):
        """Test that all files appear in the tree."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_tree_report(fixture_path, output)
        
        json_file = output / "tree.json"
        data = json.loads(json_file.read_text())
        
        # Count all files in tree recursively
        def count_files(node):
            if node["type"] == "file":
                return 1
            count = 0
            for child in node.get("children", []):
                count += count_files(child)
            return count
        
        file_count = count_files(data)
        assert file_count == expected_file_count, \
            f"Expected {expected_file_count} files in tree, got {file_count}"
    
    def test_tree_markdown_generated(self, tmp_path, fixture_path, expected_languages, expected_file_count):
        """Test that tree markdown is generated."""
        if not fixture_path.exists():
            pytest.skip(f"Fixture not found: {fixture_path}")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_tree_report(fixture_path, output)
        
        md_file = output / "tree.md"
        assert md_file.exists(), "tree.md not generated"
        
        content = md_file.read_text()
        
        # Should contain tree structure markers
        assert any(marker in content for marker in ["├──", "└──", "│"])


class TestGoldenOutputs:
    """Test against golden (reference) outputs for regression detection."""
    
    def test_c_cpp_rust_matches_golden_schema(self, tmp_path):
        """Test that C/C++/Rust fixture produces schema-compatible output with golden file."""
        golden_dir = FIXTURES_DIR.parent / "golden_outputs" / "c_cpp_rust"
        
        if not golden_dir.exists():
            pytest.skip("Golden outputs not available")
        
        output = tmp_path / "output"
        output.mkdir()
        
        # Generate fresh output
        generate_file_summaries(
            C_CPP_RUST_FIXTURE,
            output,
            include_patterns=["*.*"],
            detail_level="standard"
        )
        
        # Load golden and generated outputs
        golden_json = json.loads((golden_dir / "file-summaries.json").read_text())
        generated_json = json.loads((output / "file-summaries.json").read_text())
        
        # Compare structure (not exact content, as that may legitimately change)
        assert golden_json["schema_version"] == generated_json["schema_version"]
        assert golden_json["total_files"] == generated_json["total_files"]
        
        # Verify same files are present
        golden_paths = {f["path"] for f in golden_json["files"]}
        generated_paths = {f["path"] for f in generated_json["files"]}
        assert golden_paths == generated_paths, "File paths differ from golden output"
        
        # Verify all required fields are present in generated output
        for gen_file in generated_json["files"]:
            assert "schema_version" in gen_file
            assert "path" in gen_file
            assert "language" in gen_file
            assert "role" in gen_file
            assert "role_justification" in gen_file
            assert "metrics" in gen_file
        
        # Verify language detection and role classification remain consistent
        golden_files_by_path = {f["path"]: f for f in golden_json["files"]}
        generated_files_by_path = {f["path"]: f for f in generated_json["files"]}
        
        for path in golden_paths:
            golden_file = golden_files_by_path[path]
            generated_file = generated_files_by_path[path]
            
            # Language detection should be consistent
            assert golden_file["language"] == generated_file["language"], \
                f"Language mismatch for {path}: expected {golden_file['language']}, got {generated_file['language']}"
            
            # Role classification should be consistent
            assert golden_file["role"] == generated_file["role"], \
                f"Role mismatch for {path}: expected {golden_file['role']}, got {generated_file['role']}"


class TestCrossFixtureConsistency:
    """Test consistency across all fixtures."""
    
    def test_all_fixtures_produce_valid_json(self, tmp_path):
        """Test that all fixtures produce valid JSON output."""
        for fixture_param in FIXTURES:
            fixture_path = fixture_param.values[0]
            
            if not fixture_path.exists():
                continue
            
            output = tmp_path / f"output_{fixture_path.name}"
            output.mkdir()
            
            # Generate all reports
            generate_file_summaries(fixture_path, output, include_patterns=["*.*"], detail_level="standard")
            generate_dependency_report(fixture_path, output, include_patterns=["*.*"])
            generate_tree_report(fixture_path, output)
            
            # Validate JSON files are parseable
            for json_file_name in ["file-summaries.json", "dependencies.json", "tree.json"]:
                json_file = output / json_file_name
                assert json_file.exists(), f"{json_file_name} not generated for {fixture_path.name}"
                
                try:
                    json.loads(json_file.read_text())
                except json.JSONDecodeError as e:
                    pytest.fail(f"Invalid JSON in {json_file_name} for {fixture_path.name}: {e}")
    
    def test_no_fixture_produces_errors(self, tmp_path, capsys):
        """Test that no fixture produces error messages."""
        for fixture_param in FIXTURES:
            fixture_path = fixture_param.values[0]
            
            if not fixture_path.exists():
                continue
            
            output = tmp_path / f"output_{fixture_path.name}"
            output.mkdir()
            
            # Generate all reports
            generate_file_summaries(fixture_path, output, include_patterns=["*.*"], detail_level="standard")
            generate_dependency_report(fixture_path, output, include_patterns=["*.*"])
            generate_tree_report(fixture_path, output)
            
            # Check for actual error/failure patterns (not substrings in normal output)
            captured = capsys.readouterr()
            # Look for error patterns at line start or with specific prefixes
            import re
            error_patterns = [
                r'^Error:',
                r'^ERROR:',
                r'^\[ERROR\]',
                r'Failed to',
                r'FAILED:',
                r'Traceback \(most recent call last\)',
            ]
            for pattern in error_patterns:
                if re.search(pattern, captured.out, re.MULTILINE):
                    pytest.fail(f"Error pattern '{pattern}' found in output for {fixture_path.name}: {captured.out}")
                if re.search(pattern, captured.err, re.MULTILINE):
                    pytest.fail(f"Error pattern '{pattern}' found in stderr for {fixture_path.name}: {captured.err}")


class TestLanguageSpecificBehavior:
    """Test language-specific behavior in multi-language contexts."""
    
    def test_c_cpp_rust_header_detection(self, tmp_path):
        """Test that C/C++ headers are correctly identified in mixed fixture."""
        if not C_CPP_RUST_FIXTURE.exists():
            pytest.skip("C/C++/Rust fixture not found")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_file_summaries(
            C_CPP_RUST_FIXTURE,
            output,
            include_patterns=["*.*"],
            detail_level="standard"
        )
        
        json_file = output / "file-summaries.json"
        data = json.loads(json_file.read_text())
        
        # Find utils.h
        utils_h = next((e for e in data["files"] if e["path"] == "utils.h"), None)
        assert utils_h is not None, "utils.h not found"
        assert "header" in utils_h["summary"].lower(), "utils.h not identified as header"
    
    def test_go_test_file_detection(self, tmp_path):
        """Test that Go test files are correctly identified."""
        if not GO_SQL_FIXTURE.exists():
            pytest.skip("Go/SQL fixture not found")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_file_summaries(
            GO_SQL_FIXTURE,
            output,
            include_patterns=["*.*"],
            detail_level="standard"
        )
        
        json_file = output / "file-summaries.json"
        data = json.loads(json_file.read_text())
        
        # Find test file
        test_file = next((e for e in data["files"] if "_test.go" in e["path"]), None)
        assert test_file is not None, "Go test file not found"
        assert test_file["role"] == "test", "Go test file not identified with test role"
    
    def test_html_css_js_dependencies(self, tmp_path):
        """Test that HTML references CSS/JS files correctly."""
        if not HTML_CSS_JS_FIXTURE.exists():
            pytest.skip("HTML/CSS/JS fixture not found")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            HTML_CSS_JS_FIXTURE,
            output,
            include_patterns=["*.*"]
        )
        
        json_file = output / "dependencies.json"
        data = json.loads(json_file.read_text())
        
        # Find index.html node (exact match)
        index_html = next((n for n in data["nodes"] if n["path"] == "index.html"), None)
        assert index_html is not None, "index.html not found in dependency graph"
        
        # Check for edges from index.html to CSS/JS files
        html_edges = [e for e in data["edges"] if e["source"] == "index.html"]
        assert len(html_edges) == 4, f"Expected 4 dependencies from index.html, got {len(html_edges)}"
        
        # Verify specific expected dependencies
        targets = {e["target"] for e in html_edges}
        expected_targets = {
            "styles/main.css",
            "styles/components.css",
            "js/utils.js",
            "js/app.js"
        }
        assert targets == expected_targets, f"Unexpected dependency targets for index.html. Expected {expected_targets}, got {targets}"
    
    def test_swift_csharp_interface_detection(self, tmp_path):
        """Test that C# interfaces are correctly identified."""
        if not SWIFT_CSHARP_FIXTURE.exists():
            pytest.skip("Swift/C# fixture not found")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_file_summaries(
            SWIFT_CSHARP_FIXTURE,
            output,
            include_patterns=["*.*"],
            detail_level="standard"
        )
        
        json_file = output / "file-summaries.json"
        data = json.loads(json_file.read_text())
        
        # Find UserService.cs which contains interface
        user_service = next((e for e in data["files"] if "UserService.cs" in e["path"]), None)
        assert user_service is not None, "UserService.cs not found"
        # Should be identified as service (not just interface, since it has implementation too)
        assert user_service["role"] in ["service", "implementation"], \
            f"UserService.cs has unexpected role: {user_service['role']}"
