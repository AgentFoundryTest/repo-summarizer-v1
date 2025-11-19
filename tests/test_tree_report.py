"""
Tests for tree_report module.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from repo_analyzer.tree_report import (
    generate_tree_report,
    TreeReportError,
    _should_exclude,
    _build_tree_structure,
    _tree_to_markdown,
    DEFAULT_EXCLUDES,
)


class TestShouldExclude:
    """Tests for _should_exclude function."""
    
    def test_exact_match(self):
        """Test exact name matching."""
        patterns = {'.git', 'node_modules'}
        assert _should_exclude('.git', patterns) is True
        assert _should_exclude('node_modules', patterns) is True
        assert _should_exclude('src', patterns) is False
    
    def test_wildcard_suffix(self):
        """Test wildcard suffix matching (*.ext)."""
        patterns = {'*.pyc', '*.log'}
        assert _should_exclude('test.pyc', patterns) is True
        assert _should_exclude('debug.log', patterns) is True
        assert _should_exclude('test.py', patterns) is False
    
    def test_wildcard_prefix(self):
        """Test wildcard prefix matching (prefix*)."""
        patterns = {'test*', 'tmp*'}
        assert _should_exclude('test_file', patterns) is True
        assert _should_exclude('tmpdata', patterns) is True
        assert _should_exclude('mytest', patterns) is False
    
    def test_no_match(self):
        """Test when no patterns match."""
        patterns = {'.git', '*.pyc'}
        assert _should_exclude('src', patterns) is False
        assert _should_exclude('main.py', patterns) is False


class TestBuildTreeStructure:
    """Tests for _build_tree_structure function."""
    
    def test_basic_directory_structure(self, tmp_path):
        """Test building tree for basic directory structure."""
        # Create test structure
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.py").touch()
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").touch()
        
        tree = _build_tree_structure(tmp_path, set())
        
        assert tree["type"] == "directory"
        assert tree["name"] == tmp_path.name
        assert len(tree["children"]) == 3  # 2 files + 1 dir
        
        # Check that directories come before files (sorted)
        assert tree["children"][0]["type"] == "directory"
        assert tree["children"][0]["name"] == "subdir"
    
    def test_exclude_patterns(self, tmp_path):
        """Test that exclude patterns are respected."""
        # Create test structure
        (tmp_path / "keep.txt").touch()
        (tmp_path / "exclude.pyc").touch()
        (tmp_path / ".git").mkdir()
        (tmp_path / "node_modules").mkdir()
        
        excludes = {'.git', 'node_modules', '*.pyc'}
        tree = _build_tree_structure(tmp_path, excludes)
        
        # Should only have keep.txt
        assert len(tree["children"]) == 1
        assert tree["children"][0]["name"] == "keep.txt"
    
    def test_max_depth(self, tmp_path):
        """Test max_depth parameter."""
        # Create deep structure
        (tmp_path / "level1").mkdir()
        (tmp_path / "level1" / "level2").mkdir()
        (tmp_path / "level1" / "level2" / "level3").mkdir()
        (tmp_path / "level1" / "level2" / "level3" / "file.txt").touch()
        
        # Depth 0: only root
        tree = _build_tree_structure(tmp_path, set(), max_depth=0)
        assert len(tree["children"]) == 0
        
        # Depth 1: root + level1
        tree = _build_tree_structure(tmp_path, set(), max_depth=1)
        assert len(tree["children"]) == 1
        assert tree["children"][0]["name"] == "level1"
        assert len(tree["children"][0]["children"]) == 0
        
        # Depth 2: root + level1 + level2
        tree = _build_tree_structure(tmp_path, set(), max_depth=2)
        level1 = tree["children"][0]
        assert len(level1["children"]) == 1
        assert level1["children"][0]["name"] == "level2"
        assert len(level1["children"][0]["children"]) == 0
    
    def test_symlink_avoidance(self, tmp_path):
        """Test that symlinks are skipped."""
        # Create a regular file and a symlink
        real_file = tmp_path / "real.txt"
        real_file.touch()
        
        link_file = tmp_path / "link.txt"
        link_file.symlink_to(real_file)
        
        # Create a directory and a symlinked directory
        real_dir = tmp_path / "realdir"
        real_dir.mkdir()
        
        link_dir = tmp_path / "linkdir"
        link_dir.symlink_to(real_dir)
        
        tree = _build_tree_structure(tmp_path, set())
        
        # Should only have real.txt and realdir, no symlinks
        assert len(tree["children"]) == 2
        names = {child["name"] for child in tree["children"]}
        assert names == {"real.txt", "realdir"}
    
    def test_deterministic_ordering(self, tmp_path):
        """Test that entries are sorted deterministically."""
        # Create entries in random order
        (tmp_path / "zebra.txt").touch()
        (tmp_path / "Alpha").mkdir()
        (tmp_path / "beta.txt").touch()
        (tmp_path / "Gamma").mkdir()
        
        tree = _build_tree_structure(tmp_path, set())
        
        # Directories should come first, then files, case-insensitive sort
        names = [child["name"] for child in tree["children"]]
        # Directories: Alpha, Gamma (case-insensitive)
        # Files: beta.txt, zebra.txt (case-insensitive)
        assert names[0] in ["Alpha", "Gamma"]
        assert names[1] in ["Alpha", "Gamma"]
        assert names[2] == "beta.txt"
        assert names[3] == "zebra.txt"
    
    def test_error_on_non_directory(self, tmp_path):
        """Test error when path is not a directory."""
        file_path = tmp_path / "file.txt"
        file_path.touch()
        
        with pytest.raises(TreeReportError, match="not a directory"):
            _build_tree_structure(file_path, set())
    
    def test_permission_error_propagates(self, tmp_path):
        """Test that permission errors are propagated as TreeReportError."""
        import stat
        
        # Create a directory structure with a protected subdirectory
        (tmp_path / "accessible").mkdir()
        (tmp_path / "accessible" / "file.txt").touch()
        
        protected_dir = tmp_path / "protected"
        protected_dir.mkdir()
        (protected_dir / "secret.txt").touch()
        
        # Remove read permissions from protected directory
        protected_dir.chmod(0o000)
        
        try:
            # Attempting to build tree should raise TreeReportError
            with pytest.raises(TreeReportError, match="Failed to read"):
                _build_tree_structure(tmp_path, set())
        finally:
            # Restore permissions for cleanup
            protected_dir.chmod(0o755)


class TestTreeToMarkdown:
    """Tests for _tree_to_markdown function."""
    
    def test_simple_structure(self):
        """Test Markdown generation for simple structure."""
        tree = {
            "type": "directory",
            "name": "root",
            "children": [
                {"type": "file", "name": "file1.txt"},
                {"type": "file", "name": "file2.txt"},
            ]
        }
        
        markdown = _tree_to_markdown(tree)
        
        assert "# root" in markdown
        assert "├── file1.txt" in markdown
        assert "└── file2.txt" in markdown
    
    def test_nested_structure(self):
        """Test Markdown generation for nested structure."""
        tree = {
            "type": "directory",
            "name": "root",
            "children": [
                {
                    "type": "directory",
                    "name": "subdir",
                    "children": [
                        {"type": "file", "name": "nested.txt"}
                    ]
                },
                {"type": "file", "name": "file.txt"}
            ]
        }
        
        markdown = _tree_to_markdown(tree)
        
        assert "# root" in markdown
        assert "├── subdir" in markdown
        assert "└── file.txt" in markdown
        assert "└── nested.txt" in markdown


class TestGenerateTreeReport:
    """Tests for generate_tree_report function."""
    
    def test_basic_generation(self, tmp_path):
        """Test basic tree report generation."""
        # Create source structure
        source = tmp_path / "source"
        source.mkdir()
        (source / "file1.txt").touch()
        (source / "subdir").mkdir()
        (source / "subdir" / "file2.txt").touch()
        
        # Create output directory
        output = tmp_path / "output"
        output.mkdir()
        
        # Generate report
        generate_tree_report(source, output)
        
        # Check Markdown output
        markdown_file = output / "tree.md"
        assert markdown_file.exists()
        content = markdown_file.read_text()
        assert "file1.txt" in content
        assert "subdir" in content
        assert "file2.txt" in content
        
        # Check JSON output
        json_file = output / "tree.json"
        assert json_file.exists()
        tree_data = json.loads(json_file.read_text())
        assert tree_data["type"] == "directory"
        assert len(tree_data["children"]) == 2
    
    def test_default_excludes(self, tmp_path):
        """Test that default excludes are applied."""
        # Create source structure with noise directories
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").touch()
        (source / ".git").mkdir()
        (source / "node_modules").mkdir()
        (source / "__pycache__").mkdir()
        (source / ".venv").mkdir()
        (source / "build").mkdir()
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_tree_report(source, output)
        
        # Check that noise directories are excluded
        markdown_file = output / "tree.md"
        content = markdown_file.read_text()
        assert "file.txt" in content
        assert ".git" not in content
        assert "node_modules" not in content
        assert "__pycache__" not in content
        assert ".venv" not in content
        assert "build" not in content
    
    def test_custom_excludes(self, tmp_path):
        """Test custom exclude patterns."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "keep.txt").touch()
        (source / "exclude.log").touch()
        (source / "test_file").touch()
        
        output = tmp_path / "output"
        output.mkdir()
        
        # Custom excludes
        generate_tree_report(
            source,
            output,
            exclude_patterns=["*.log", "test_*"]
        )
        
        markdown_file = output / "tree.md"
        content = markdown_file.read_text()
        assert "keep.txt" in content
        assert "exclude.log" not in content
        assert "test_file" not in content
    
    def test_dry_run_mode(self, tmp_path, capsys):
        """Test dry-run mode doesn't write files."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").touch()
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_tree_report(source, output, dry_run=True)
        
        # Check that files were not created
        assert not (output / "tree.md").exists()
        assert not (output / "tree.json").exists()
        
        # Check that messages were printed
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "tree.md" in captured.out
    
    def test_json_optional(self, tmp_path):
        """Test that JSON generation can be disabled."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "file.txt").touch()
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_tree_report(source, output, generate_json=False)
        
        # Check that Markdown exists but JSON doesn't
        assert (output / "tree.md").exists()
        assert not (output / "tree.json").exists()
    
    def test_deep_directory_structure(self, tmp_path):
        """Test with deep directory nesting."""
        source = tmp_path / "source"
        source.mkdir()
        
        # Create deep structure
        current = source
        for i in range(10):
            current = current / f"level{i}"
            current.mkdir()
            (current / f"file{i}.txt").touch()
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_tree_report(source, output)
        
        markdown_file = output / "tree.md"
        assert markdown_file.exists()
        content = markdown_file.read_text()
        
        # Check that all levels are present
        for i in range(10):
            assert f"level{i}" in content
            assert f"file{i}.txt" in content
    
    def test_max_depth_parameter(self, tmp_path):
        """Test max_depth parameter limits traversal."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "level1").mkdir()
        (source / "level1" / "level2").mkdir()
        (source / "level1" / "level2" / "deep.txt").touch()
        (source / "root.txt").touch()
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_tree_report(source, output, max_depth=1)
        
        markdown_file = output / "tree.md"
        content = markdown_file.read_text()
        
        # Should have root.txt and level1, but not level2 or deep.txt
        assert "root.txt" in content
        assert "level1" in content
        assert "level2" not in content
        assert "deep.txt" not in content
