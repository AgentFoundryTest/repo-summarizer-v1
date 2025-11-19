"""
Tests for file_summary module.
"""

import json
import tempfile
from pathlib import Path

import pytest

from repo_analyzer.file_summary import (
    generate_file_summaries,
    FileSummaryError,
    scan_files,
    _get_language,
    _generate_heuristic_summary,
    _matches_pattern,
)


class TestMatchesPattern:
    """Tests for _matches_pattern function."""
    
    def test_suffix_pattern(self):
        """Test suffix pattern matching (*.ext)."""
        assert _matches_pattern('test.py', ['*.py']) is True
        assert _matches_pattern('test.js', ['*.py']) is False
        assert _matches_pattern('test.py', ['*.py', '*.js']) is True
    
    def test_prefix_pattern(self):
        """Test prefix pattern matching (prefix*)."""
        assert _matches_pattern('test_file.py', ['test*']) is True
        assert _matches_pattern('my_test.py', ['test*']) is False
    
    def test_exact_match(self):
        """Test exact filename matching."""
        assert _matches_pattern('config.json', ['config.json']) is True
        assert _matches_pattern('config.yaml', ['config.json']) is False
    
    def test_multiple_patterns(self):
        """Test matching against multiple patterns."""
        patterns = ['*.py', 'test*', 'config.json']
        assert _matches_pattern('main.py', patterns) is True
        assert _matches_pattern('test_runner.js', patterns) is True
        assert _matches_pattern('config.json', patterns) is True
        assert _matches_pattern('other.txt', patterns) is False
    
    def test_path_with_directory(self):
        """Test pattern matching with directory paths."""
        # Match files in specific directory (single level)
        assert _matches_pattern('tests/test_utils.py', ['tests/*.py']) is True
        assert _matches_pattern('src/utils.py', ['tests/*.py']) is False
        
        # Single * doesn't match across directory separators
        assert _matches_pattern('src/utils.py', ['src/*.py']) is True
        assert _matches_pattern('src/lib/helper.py', ['src/*.py']) is False
        
        # Double ** matches multiple directory levels
        assert _matches_pattern('src/lib/helper.py', ['src/**/*.py']) is True
        assert _matches_pattern('tests/unit/test_main.py', ['tests/**/*.py']) is True
    
    def test_single_char_wildcard(self):
        """Test single-character wildcard (?)."""
        assert _matches_pattern('foo1.js', ['foo?.js']) is True
        assert _matches_pattern('foo2.js', ['foo?.js']) is True
        assert _matches_pattern('foo.js', ['foo?.js']) is False
        assert _matches_pattern('foo12.js', ['foo?.js']) is False
    
    def test_complex_patterns(self):
        """Test more complex glob patterns."""
        # Character ranges
        assert _matches_pattern('test1.py', ['test[0-9].py']) is True
        assert _matches_pattern('testX.py', ['test[0-9].py']) is False
        
        # Multiple wildcards
        assert _matches_pattern('test_utils.py', ['test_*.py']) is True
        assert _matches_pattern('my_test.py', ['*_test.py']) is True


class TestGetLanguage:
    """Tests for _get_language function."""
    
    def test_python(self):
        """Test Python file detection."""
        assert _get_language(Path('test.py')) == 'Python'
    
    def test_javascript(self):
        """Test JavaScript file detection."""
        assert _get_language(Path('app.js')) == 'JavaScript'
        assert _get_language(Path('component.jsx')) == 'JavaScript'
    
    def test_typescript(self):
        """Test TypeScript file detection."""
        assert _get_language(Path('app.ts')) == 'TypeScript'
        assert _get_language(Path('component.tsx')) == 'TypeScript'
    
    def test_java(self):
        """Test Java file detection."""
        assert _get_language(Path('Main.java')) == 'Java'
    
    def test_go(self):
        """Test Go file detection."""
        assert _get_language(Path('main.go')) == 'Go'
    
    def test_rust(self):
        """Test Rust file detection."""
        assert _get_language(Path('main.rs')) == 'Rust'
    
    def test_unknown(self):
        """Test unknown file type."""
        assert _get_language(Path('file.xyz')) == 'Unknown'
    
    def test_case_insensitive(self):
        """Test that extension matching is case-insensitive."""
        assert _get_language(Path('test.PY')) == 'Python'
        assert _get_language(Path('test.JS')) == 'JavaScript'


class TestGenerateHeuristicSummary:
    """Tests for _generate_heuristic_summary function."""
    
    def test_test_file(self, tmp_path):
        """Test summary for test files."""
        root = tmp_path
        file_path = root / 'test_main.py'
        summary = _generate_heuristic_summary(file_path, root)
        assert 'test' in summary.lower()
        assert 'Python' in summary
    
    def test_main_file(self, tmp_path):
        """Test summary for main entry point files."""
        root = tmp_path
        file_path = root / 'main.py'
        summary = _generate_heuristic_summary(file_path, root)
        assert 'main' in summary.lower() or 'entry' in summary.lower()
    
    def test_cli_file(self, tmp_path):
        """Test summary for CLI files."""
        root = tmp_path
        file_path = root / 'cli.py'
        summary = _generate_heuristic_summary(file_path, root)
        assert 'cli' in summary.lower() or 'command' in summary.lower()
    
    def test_utils_file(self, tmp_path):
        """Test summary for utility files."""
        root = tmp_path
        file_path = root / 'utils.py'
        summary = _generate_heuristic_summary(file_path, root)
        assert 'util' in summary.lower()
    
    def test_config_file(self, tmp_path):
        """Test summary for configuration files."""
        root = tmp_path
        file_path = root / 'config.py'
        summary = _generate_heuristic_summary(file_path, root)
        assert 'config' in summary.lower()
    
    def test_component_file(self, tmp_path):
        """Test summary for component files."""
        root = tmp_path
        file_path = root / 'Button.tsx'
        summary = _generate_heuristic_summary(file_path, root)
        assert 'component' in summary.lower()
    
    def test_path_based_heuristics(self, tmp_path):
        """Test path-based heuristic summaries."""
        root = tmp_path
        
        # Test file in tests directory
        tests_dir = root / 'tests'
        tests_dir.mkdir()
        file_path = tests_dir / 'test_utils.py'
        summary = _generate_heuristic_summary(file_path, root)
        assert 'test' in summary.lower()
        
        # Test file in src directory with a generic name
        src_dir = root / 'src'
        src_dir.mkdir()
        file_path = src_dir / 'custom_module.py'
        summary = _generate_heuristic_summary(file_path, root)
        assert 'core' in summary.lower() or 'implementation' in summary.lower()
    
    def test_default_summary(self, tmp_path):
        """Test default summary for generic files."""
        root = tmp_path
        file_path = root / 'my_custom_module.py'
        summary = _generate_heuristic_summary(file_path, root)
        assert 'Python' in summary
        assert 'my custom module' in summary.lower() or 'module' in summary.lower()
    
    def test_deterministic_output(self, tmp_path):
        """Test that summaries are deterministic."""
        root = tmp_path
        file_path = root / 'test.py'
        
        summary1 = _generate_heuristic_summary(file_path, root)
        summary2 = _generate_heuristic_summary(file_path, root)
        
        assert summary1 == summary2


class TestScanFiles:
    """Tests for scan_files function."""
    
    def test_basic_scan(self, tmp_path):
        """Test basic file scanning."""
        (tmp_path / 'file1.py').touch()
        (tmp_path / 'file2.py').touch()
        (tmp_path / 'file3.txt').touch()
        
        files = scan_files(tmp_path, include_patterns=['*.py'])
        
        assert len(files) == 2
        assert all(f.suffix == '.py' for f in files)
    
    def test_exclude_patterns(self, tmp_path):
        """Test exclude patterns."""
        (tmp_path / 'keep.py').touch()
        (tmp_path / 'exclude.pyc').touch()
        (tmp_path / 'test_file.py').touch()
        
        files = scan_files(
            tmp_path,
            include_patterns=['*.py', '*.pyc'],
            exclude_patterns=['*.pyc', 'test*']
        )
        
        assert len(files) == 1
        assert files[0].name == 'keep.py'
    
    def test_exclude_directories(self, tmp_path):
        """Test excluding directories."""
        (tmp_path / 'file.py').touch()
        
        excluded_dir = tmp_path / 'excluded'
        excluded_dir.mkdir()
        (excluded_dir / 'file.py').touch()
        
        files = scan_files(
            tmp_path,
            include_patterns=['*.py'],
            exclude_dirs={'excluded'}
        )
        
        assert len(files) == 1
        assert files[0].name == 'file.py'
        assert files[0].parent == tmp_path
    
    def test_recursive_scan(self, tmp_path):
        """Test recursive directory scanning."""
        (tmp_path / 'file1.py').touch()
        
        subdir = tmp_path / 'subdir'
        subdir.mkdir()
        (subdir / 'file2.py').touch()
        
        deep_dir = subdir / 'deep'
        deep_dir.mkdir()
        (deep_dir / 'file3.py').touch()
        
        files = scan_files(tmp_path, include_patterns=['*.py'])
        
        assert len(files) == 3
    
    def test_symlink_avoidance(self, tmp_path):
        """Test that symlinks are skipped."""
        real_file = tmp_path / 'real.py'
        real_file.touch()
        
        link_file = tmp_path / 'link.py'
        link_file.symlink_to(real_file)
        
        real_dir = tmp_path / 'realdir'
        real_dir.mkdir()
        (real_dir / 'file.py').touch()
        
        link_dir = tmp_path / 'linkdir'
        link_dir.symlink_to(real_dir)
        
        files = scan_files(tmp_path, include_patterns=['*.py'])
        
        # Should only get real.py and realdir/file.py, not symlinks
        assert len(files) == 2
        assert all(not f.is_symlink() for f in files)
    
    def test_deterministic_ordering(self, tmp_path):
        """Test that file ordering is deterministic."""
        (tmp_path / 'zebra.py').touch()
        (tmp_path / 'alpha.py').touch()
        (tmp_path / 'beta.py').touch()
        
        files1 = scan_files(tmp_path, include_patterns=['*.py'])
        files2 = scan_files(tmp_path, include_patterns=['*.py'])
        
        assert [f.name for f in files1] == [f.name for f in files2]
        assert files1[0].name == 'alpha.py'
        assert files1[1].name == 'beta.py'
        assert files1[2].name == 'zebra.py'
    
    def test_no_include_patterns(self, tmp_path):
        """Test scanning with no include patterns (should include all)."""
        (tmp_path / 'file1.py').touch()
        (tmp_path / 'file2.txt').touch()
        
        files = scan_files(tmp_path)
        
        # With no include patterns, all files are included
        assert len(files) == 2
    
    def test_empty_directory(self, tmp_path):
        """Test scanning empty directory."""
        files = scan_files(tmp_path, include_patterns=['*.py'])
        assert len(files) == 0
    
    def test_hidden_directories_skipped(self, tmp_path):
        """Test that hidden directories (starting with .) are skipped."""
        (tmp_path / 'file.py').touch()
        
        # Create hidden directories
        git_dir = tmp_path / '.git'
        git_dir.mkdir()
        (git_dir / 'config.py').touch()
        
        venv_dir = tmp_path / '.venv'
        venv_dir.mkdir()
        (venv_dir / 'activate.py').touch()
        
        files = scan_files(tmp_path, include_patterns=['*.py'])
        
        # Should only find file.py, not files in hidden directories
        assert len(files) == 1
        assert files[0].name == 'file.py'
    
    def test_path_based_patterns(self, tmp_path):
        """Test glob patterns that include directory paths."""
        # Create directory structure
        (tmp_path / 'root.py').touch()
        
        tests_dir = tmp_path / 'tests'
        tests_dir.mkdir()
        (tests_dir / 'test_main.py').touch()
        (tests_dir / 'helper.py').touch()
        
        src_dir = tmp_path / 'src'
        src_dir.mkdir()
        (src_dir / 'main.py').touch()
        (src_dir / 'utils.py').touch()
        
        # Test pattern matching specific directory
        files = scan_files(tmp_path, include_patterns=['tests/*.py'])
        assert len(files) == 2
        assert all('tests' in str(f) for f in files)
        
        # Test pattern matching just filename in any location
        files = scan_files(tmp_path, include_patterns=['*main.py'])
        assert len(files) == 2  # test_main.py and main.py
        
        # Test excluding specific directory files
        files = scan_files(
            tmp_path,
            include_patterns=['*.py'],
            exclude_patterns=['tests/*']
        )
        assert len(files) == 3  # root.py, src/main.py, src/utils.py
        assert not any('tests' in str(f) for f in files)


class TestGenerateFileSummaries:
    """Tests for generate_file_summaries function."""
    
    def test_basic_generation(self, tmp_path):
        """Test basic file summary generation."""
        source = tmp_path / 'source'
        source.mkdir()
        (source / 'main.py').touch()
        (source / 'utils.py').touch()
        
        output = tmp_path / 'output'
        output.mkdir()
        
        generate_file_summaries(
            source,
            output,
            include_patterns=['*.py']
        )
        
        # Check Markdown output
        md_file = output / 'file-summaries.md'
        assert md_file.exists()
        content = md_file.read_text()
        assert 'main.py' in content
        assert 'utils.py' in content
        assert 'Total files: 2' in content
        
        # Check JSON output
        json_file = output / 'file-summaries.json'
        assert json_file.exists()
        data = json.loads(json_file.read_text())
        assert data['total_files'] == 2
        assert len(data['files']) == 2
        
        # Verify structure
        for entry in data['files']:
            assert 'path' in entry
            assert 'language' in entry
            assert 'summary' in entry
    
    def test_multiple_languages(self, tmp_path):
        """Test with multiple language files."""
        source = tmp_path / 'source'
        source.mkdir()
        (source / 'app.py').touch()
        (source / 'script.js').touch()
        (source / 'main.go').touch()
        
        output = tmp_path / 'output'
        output.mkdir()
        
        generate_file_summaries(
            source,
            output,
            include_patterns=['*.py', '*.js', '*.go']
        )
        
        json_file = output / 'file-summaries.json'
        data = json.loads(json_file.read_text())
        
        languages = {entry['language'] for entry in data['files']}
        assert 'Python' in languages
        assert 'JavaScript' in languages
        assert 'Go' in languages
    
    def test_exclude_directories(self, tmp_path):
        """Test excluding directories."""
        source = tmp_path / 'source'
        source.mkdir()
        (source / 'main.py').touch()
        
        excluded = source / 'excluded'
        excluded.mkdir()
        (excluded / 'skip.py').touch()
        
        output = tmp_path / 'output'
        output.mkdir()
        
        generate_file_summaries(
            source,
            output,
            include_patterns=['*.py'],
            exclude_dirs={'excluded'}
        )
        
        json_file = output / 'file-summaries.json'
        data = json.loads(json_file.read_text())
        
        assert data['total_files'] == 1
        assert data['files'][0]['path'] == 'main.py'
    
    def test_dry_run_mode(self, tmp_path, capsys):
        """Test dry-run mode doesn't write files."""
        source = tmp_path / 'source'
        source.mkdir()
        (source / 'file.py').touch()
        
        output = tmp_path / 'output'
        output.mkdir()
        
        generate_file_summaries(
            source,
            output,
            include_patterns=['*.py'],
            dry_run=True
        )
        
        # Check that files were not created
        assert not (output / 'file-summaries.md').exists()
        assert not (output / 'file-summaries.json').exists()
        
        # Check that messages were printed
        captured = capsys.readouterr()
        assert '[DRY RUN]' in captured.out
        assert 'file-summaries.md' in captured.out
    
    def test_no_matching_files(self, tmp_path, capsys):
        """Test behavior when no files match."""
        source = tmp_path / 'source'
        source.mkdir()
        (source / 'file.txt').touch()
        
        output = tmp_path / 'output'
        output.mkdir()
        
        generate_file_summaries(
            source,
            output,
            include_patterns=['*.py']
        )
        
        # No output files should be created
        assert not (output / 'file-summaries.md').exists()
        assert not (output / 'file-summaries.json').exists()
        
        captured = capsys.readouterr()
        assert 'No files found' in captured.out
    
    def test_nested_directory_structure(self, tmp_path):
        """Test with nested directories."""
        source = tmp_path / 'source'
        source.mkdir()
        
        (source / 'root.py').touch()
        
        level1 = source / 'level1'
        level1.mkdir()
        (level1 / 'file1.py').touch()
        
        level2 = level1 / 'level2'
        level2.mkdir()
        (level2 / 'file2.py').touch()
        
        output = tmp_path / 'output'
        output.mkdir()
        
        generate_file_summaries(
            source,
            output,
            include_patterns=['*.py']
        )
        
        json_file = output / 'file-summaries.json'
        data = json.loads(json_file.read_text())
        
        assert data['total_files'] == 3
        
        # Check paths
        paths = [entry['path'] for entry in data['files']]
        assert 'level1/file1.py' in paths
        assert 'level1/level2/file2.py' in paths
        assert 'root.py' in paths
    
    def test_deterministic_output_ordering(self, tmp_path):
        """Test that output is deterministically ordered."""
        source = tmp_path / 'source'
        source.mkdir()
        
        (source / 'zebra.py').touch()
        (source / 'alpha.py').touch()
        (source / 'beta.py').touch()
        
        output = tmp_path / 'output'
        output.mkdir()
        
        generate_file_summaries(
            source,
            output,
            include_patterns=['*.py']
        )
        
        json_file = output / 'file-summaries.json'
        data = json.loads(json_file.read_text())
        
        paths = [entry['path'] for entry in data['files']]
        assert paths == sorted(paths)
        assert paths[0] == 'alpha.py'
        assert paths[1] == 'beta.py'
        assert paths[2] == 'zebra.py'
    
    def test_summary_content_quality(self, tmp_path):
        """Test that summaries contain useful information."""
        source = tmp_path / 'source'
        source.mkdir()
        
        (source / 'test_main.py').touch()
        (source / 'config.json').touch()
        (source / 'utils.js').touch()
        
        output = tmp_path / 'output'
        output.mkdir()
        
        generate_file_summaries(
            source,
            output,
            include_patterns=['*.py', '*.json', '*.js']
        )
        
        json_file = output / 'file-summaries.json'
        data = json.loads(json_file.read_text())
        
        # Check that all summaries are non-empty and descriptive
        for entry in data['files']:
            assert len(entry['summary']) > 0
            assert entry['language'] in entry['summary'] or 'Unknown' not in entry['language']
    
    def test_exclude_patterns(self, tmp_path):
        """Test that exclude_patterns parameter excludes matching files."""
        source = tmp_path / 'source'
        source.mkdir()
        
        (source / 'main.py').touch()
        (source / 'test_main.py').touch()
        (source / 'utils.pyc').touch()
        (source / 'config.py').touch()
        
        output = tmp_path / 'output'
        output.mkdir()
        
        # Exclude test files and compiled files
        generate_file_summaries(
            source,
            output,
            include_patterns=['*.py', '*.pyc'],
            exclude_patterns=['test_*', '*.pyc']
        )
        
        json_file = output / 'file-summaries.json'
        data = json.loads(json_file.read_text())
        
        # Should only have main.py and config.py
        paths = {entry['path'] for entry in data['files']}
        assert paths == {'main.py', 'config.py'}
        assert 'test_main.py' not in paths
        assert 'utils.pyc' not in paths
    
    def test_nested_exclude_directories(self, tmp_path):
        """Test that nested directory exclusions work correctly."""
        source = tmp_path / 'source'
        source.mkdir()
        
        (source / 'main.py').touch()
        
        # Create nested directory structure
        build_dir = source / 'docs' / '_build'
        build_dir.mkdir(parents=True)
        (build_dir / 'generated.py').touch()
        
        output = tmp_path / 'output'
        output.mkdir()
        
        # Exclude _build directory
        generate_file_summaries(
            source,
            output,
            include_patterns=['*.py'],
            exclude_dirs={'_build'}
        )
        
        json_file = output / 'file-summaries.json'
        data = json.loads(json_file.read_text())
        
        # Should only have main.py, not generated.py
        assert data['total_files'] == 1
        assert data['files'][0]['path'] == 'main.py'
    
    def test_directory_exclude_patterns_without_wildcard(self, tmp_path):
        """Test that directory patterns like 'docs/_build' exclude files during traversal."""
        source = tmp_path / 'source'
        source.mkdir()
        
        (source / 'main.py').touch()
        
        # Create nested directory structure
        build_dir = source / 'docs' / '_build'
        build_dir.mkdir(parents=True)
        (build_dir / 'generated.py').touch()
        
        output = tmp_path / 'output'
        output.mkdir()
        
        # Exclude using pattern without wildcard (the reported issue)
        generate_file_summaries(
            source,
            output,
            include_patterns=['*.py'],
            exclude_patterns=['docs/_build']
        )
        
        json_file = output / 'file-summaries.json'
        data = json.loads(json_file.read_text())
        
        # Should only have main.py, not generated.py from docs/_build
        assert data['total_files'] == 1
        assert data['files'][0]['path'] == 'main.py'
    
    def test_path_exclude_patterns_dont_over_exclude(self, tmp_path):
        """Test that path-based exclude patterns don't exclude unrelated directories with same name."""
        source = tmp_path / 'source'
        source.mkdir()
        
        (source / 'main.py').touch()
        
        # Create multiple _build directories in different locations
        docs_build = source / 'docs' / '_build'
        docs_build.mkdir(parents=True)
        (docs_build / 'docs_generated.py').touch()
        
        src_build = source / 'src' / '_build'
        src_build.mkdir(parents=True)
        (src_build / 'src_generated.py').touch()
        
        output = tmp_path / 'output'
        output.mkdir()
        
        # Exclude only docs/_build, not src/_build
        generate_file_summaries(
            source,
            output,
            include_patterns=['*.py'],
            exclude_patterns=['docs/_build']
        )
        
        json_file = output / 'file-summaries.json'
        data = json.loads(json_file.read_text())
        
        paths = [entry['path'] for entry in data['files']]
        # Should have main.py and src/_build/src_generated.py, but not docs/_build/docs_generated.py
        assert 'main.py' in paths
        assert 'src/_build/src_generated.py' in paths
        assert 'docs/_build/docs_generated.py' not in paths
        assert data['total_files'] == 2
    
    def test_output_directory_excluded(self, tmp_path):
        """Test that output directory itself is excluded from scan."""
        source = tmp_path / 'source'
        source.mkdir()
        
        (source / 'main.py').touch()
        
        # Create output directory as a subdirectory of source
        output = source / 'output'
        output.mkdir()
        
        # First, generate summaries which will create files in output
        generate_file_summaries(
            source,
            output,
            include_patterns=['*.py', '*.md'],
            exclude_patterns=['output']  # Explicitly exclude output dir
        )
        
        json_file = output / 'file-summaries.json'
        data = json.loads(json_file.read_text())
        
        paths = [entry['path'] for entry in data['files']]
        # Should only have main.py, not the generated file-summaries.md or any output files
        assert paths == ['main.py']
        assert data['total_files'] == 1
        
        # Verify file-summaries.md and file-summaries.json exist in output
        assert (output / 'file-summaries.md').exists()
        assert (output / 'file-summaries.json').exists()

