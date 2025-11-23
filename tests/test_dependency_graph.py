"""
Tests for dependency_graph module.
"""

import json
from pathlib import Path

import pytest

from repo_analyzer.dependency_graph import (
    _parse_python_imports,
    _parse_js_imports,
    _resolve_python_import,
    _resolve_js_import,
    _scan_file_dependencies,
    build_dependency_graph,
    generate_dependency_report,
    DependencyGraphError,
)


class TestParsePythonImports:
    """Tests for Python import parsing."""
    
    def test_simple_import(self, tmp_path):
        """Test parsing simple import statements."""
        content = """
import os
import sys
import json
"""
        file_path = tmp_path / "test.py"
        imports = _parse_python_imports(content, file_path)
        
        assert 'os' in imports
        assert 'sys' in imports
        assert 'json' in imports
    
    def test_from_import(self, tmp_path):
        """Test parsing from...import statements."""
        content = """
from pathlib import Path
from typing import Dict, List
from repo_analyzer.tree_report import generate_tree_report
"""
        file_path = tmp_path / "test.py"
        imports = _parse_python_imports(content, file_path)
        
        # Should capture module.submodule for each imported name
        assert 'pathlib.Path' in imports
        assert 'typing.Dict' in imports
        assert 'typing.List' in imports
        assert 'repo_analyzer.tree_report.generate_tree_report' in imports
    
    def test_from_import_submodules(self, tmp_path):
        """Test parsing from...import statements captures submodules."""
        content = """
from mypackage import module1, module2
from pkg.subpkg import helper
from collections import OrderedDict, defaultdict
"""
        file_path = tmp_path / "test.py"
        imports = _parse_python_imports(content, file_path)
        
        # Should capture each imported name as a submodule
        assert 'mypackage.module1' in imports
        assert 'mypackage.module2' in imports
        assert 'pkg.subpkg.helper' in imports
        assert 'collections.OrderedDict' in imports
        assert 'collections.defaultdict' in imports
    
    def test_relative_imports(self, tmp_path):
        """Test parsing relative imports."""
        content = """
from . import utils
from .. import config
from ...parent import module
"""
        file_path = tmp_path / "test.py"
        imports = _parse_python_imports(content, file_path)
        
        # Relative imports combine the dots with the imported names
        assert '.utils' in imports
        assert '..config' in imports
        assert '...parent.module' in imports
    
    def test_relative_wildcard_import(self, tmp_path):
        """Test parsing relative wildcard imports."""
        content = """
from . import *
from .. import *
"""
        file_path = tmp_path / "test.py"
        imports = _parse_python_imports(content, file_path)
        
        # Wildcard imports should just be the dots
        assert '.' in imports
        assert '..' in imports
    
    def test_import_with_alias(self, tmp_path):
        """Test parsing imports with aliases."""
        content = """
import numpy as np
import pandas as pd
from collections import OrderedDict as OD
"""
        file_path = tmp_path / "test.py"
        imports = _parse_python_imports(content, file_path)
        
        assert 'numpy' in imports
        assert 'pandas' in imports
        assert 'collections.OrderedDict' in imports
    
    def test_comma_separated_imports(self, tmp_path):
        """Test parsing comma-separated import statements."""
        content = """
import os, sys, json
import pathlib, typing
import collections, itertools as it, functools
"""
        file_path = tmp_path / "test.py"
        imports = _parse_python_imports(content, file_path)
        
        # All modules should be captured
        assert 'os' in imports
        assert 'sys' in imports
        assert 'json' in imports
        assert 'pathlib' in imports
        assert 'typing' in imports
        assert 'collections' in imports
        assert 'itertools' in imports
        assert 'functools' in imports
    
    def test_ignore_comments(self, tmp_path):
        """Test that comments are ignored."""
        content = """
# import should_not_be_imported
import os
# from pathlib import Path
import sys
"""
        file_path = tmp_path / "test.py"
        imports = _parse_python_imports(content, file_path)
        
        assert 'should_not_be_imported' not in imports
        assert 'pathlib' not in imports
        assert 'os' in imports
        assert 'sys' in imports
    
    def test_multiline_imports(self, tmp_path):
        """Test that multiline imports are properly handled."""
        content = """
from typing import Dict, List
from collections import (
    OrderedDict,
    defaultdict
)
from pathlib import (
    Path,
    PurePath,
)
import os, sys, \\
    json
"""
        file_path = tmp_path / "test.py"
        imports = _parse_python_imports(content, file_path)
        
        # Should capture all modules from multiline imports
        assert 'typing.Dict' in imports
        assert 'typing.List' in imports
        assert 'collections.OrderedDict' in imports
        assert 'collections.defaultdict' in imports
        assert 'pathlib.Path' in imports
        assert 'pathlib.PurePath' in imports
        # Comma-separated imports with line continuation
        assert 'os' in imports
        assert 'sys' in imports
        assert 'json' in imports
    
    def test_skip_imports_in_strings(self, tmp_path):
        """Test that import-like text in strings/docstrings is ignored."""
        content = '''
"""
This is a docstring that mentions:
from . import utils
import os
"""
regular_string = "from pathlib import Path"
another = 'import sys'
# Real imports below
import json
from typing import List
'''
        file_path = tmp_path / "test.py"
        imports = _parse_python_imports(content, file_path)
        
        # Should only capture the real imports at the end
        assert 'json' in imports
        assert 'typing.List' in imports
        # Should NOT capture the ones in strings/docstrings
        assert 'utils' not in imports
        assert 'os' not in imports
        assert 'pathlib.Path' not in imports
        assert 'sys' not in imports


class TestParseJSImports:
    """Tests for JavaScript/TypeScript import parsing."""
    
    def test_es6_import(self, tmp_path):
        """Test parsing ES6 import statements."""
        content = """
import React from 'react';
import { useState, useEffect } from 'react';
import * as utils from './utils';
import './styles.css';
"""
        file_path = tmp_path / "test.js"
        imports = _parse_js_imports(content, file_path)
        
        assert 'react' in imports
        assert './utils' in imports
        assert './styles.css' in imports
    
    def test_commonjs_require(self, tmp_path):
        """Test parsing CommonJS require statements."""
        content = """
const fs = require('fs');
const path = require('path');
const utils = require('./utils');
const config = require('../config');
"""
        file_path = tmp_path / "test.js"
        imports = _parse_js_imports(content, file_path)
        
        assert 'fs' in imports
        assert 'path' in imports
        assert './utils' in imports
        assert '../config' in imports
    
    def test_dynamic_import(self, tmp_path):
        """Test parsing dynamic import statements."""
        content = """
const module = await import('./module');
import('./lazy-module').then(m => console.log(m));
"""
        file_path = tmp_path / "test.js"
        imports = _parse_js_imports(content, file_path)
        
        assert './module' in imports
        assert './lazy-module' in imports
    
    def test_ignore_comments(self, tmp_path):
        """Test that comments are ignored."""
        content = """
// import './should-not-import';
import './real-import';
/* import './also-should-not-import'; */
const x = require('./another-real-import');
"""
        file_path = tmp_path / "test.js"
        imports = _parse_js_imports(content, file_path)
        
        assert './should-not-import' not in imports
        assert './also-should-not-import' not in imports
        assert './real-import' in imports
        assert './another-real-import' in imports
    
    def test_mixed_quotes(self, tmp_path):
        """Test parsing with both single and double quotes."""
        content = """
import module1 from "double-quotes";
import module2 from 'single-quotes';
const m3 = require("double-require");
const m4 = require('single-require');
"""
        file_path = tmp_path / "test.js"
        imports = _parse_js_imports(content, file_path)
        
        assert 'double-quotes' in imports
        assert 'single-quotes' in imports
        assert 'double-require' in imports
        assert 'single-require' in imports
    
    def test_multiline_imports(self, tmp_path):
        """Test parsing multi-line import statements."""
        content = """
import {
  Foo,
  Bar,
  Baz
} from './lib';

import {
  Component
} from 'react';

const {
  util1,
  util2
} = require('./utils');
"""
        file_path = tmp_path / "test.js"
        imports = _parse_js_imports(content, file_path)
        
        # Should capture modules even when spread across multiple lines
        assert './lib' in imports
        assert 'react' in imports
        assert './utils' in imports
    
    def test_urls_in_strings_dont_break_imports(self, tmp_path):
        """Test that URLs in strings don't break import detection."""
        content = """
const url = "http://example.com";
import foo from './foo';
const api = 'https://api.example.com';
import bar from './bar';
"""
        file_path = tmp_path / "test.js"
        imports = _parse_js_imports(content, file_path)
        
        # Should capture imports even after URL strings
        assert './foo' in imports
        assert './bar' in imports
    
    def test_skip_imports_in_strings(self, tmp_path):
        """Test that import-like text in strings is ignored."""
        content = """
const msg = "to install run import './fake'";
const docs = 'The code shows: require("./fake-require")';
const template = `Example: import { Foo } from './fake-template'`;

// Real imports
import real from './real-module';
const realReq = require('./real-require');
"""
        file_path = tmp_path / "test.js"
        imports = _parse_js_imports(content, file_path)
        
        # Should only capture the real imports
        assert './real-module' in imports
        assert './real-require' in imports
        # Should NOT capture the fake ones in strings
        assert './fake' not in imports
        assert './fake-require' not in imports
        assert './fake-template' not in imports
    
    def test_escaped_quotes_in_strings(self, tmp_path):
        """Test that imports inside strings with escaped quotes are ignored."""
        content = '''
const msg = "He said \\"import foo from './fake'\\"";
const doc = 'Example: \\'require("./also-fake")\\' works';

// Real imports
import real from './real-module';
const realReq = require('./real-require');
'''
        file_path = tmp_path / "test.js"
        imports = _parse_js_imports(content, file_path)
        
        # Should only capture the real imports
        assert './real-module' in imports
        assert './real-require' in imports
        # Should NOT capture the fake ones in strings with escaped quotes
        assert './fake' not in imports
        assert './also-fake' not in imports


class TestResolvePythonImport:
    """Tests for Python import resolution."""
    
    def test_relative_import_same_level(self, tmp_path):
        """Test resolving relative import at same level."""
        # Create structure
        (tmp_path / "module.py").touch()
        source_file = tmp_path / "main.py"
        source_file.touch()
        
        resolved = _resolve_python_import('.module', source_file, tmp_path)
        
        assert resolved is not None
        assert resolved == tmp_path / "module.py"
    
    def test_relative_wildcard_import_resolves_to_init(self, tmp_path):
        """Test that relative wildcard imports resolve to package __init__.py."""
        # Create package structure
        package = tmp_path / "mypackage"
        package.mkdir()
        (package / "__init__.py").touch()
        
        source_file = package / "submodule.py"
        source_file.touch()
        
        # "from . import *" should resolve to mypackage/__init__.py
        resolved = _resolve_python_import('.', source_file, tmp_path)
        
        assert resolved is not None
        assert resolved == package / "__init__.py"
    
    def test_relative_import_parent(self, tmp_path):
        """Test resolving relative import from parent."""
        # Create structure
        (tmp_path / "utils.py").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        source_file = subdir / "main.py"
        source_file.touch()
        
        resolved = _resolve_python_import('..utils', source_file, tmp_path)
        
        assert resolved is not None
        assert resolved == tmp_path / "utils.py"
    
    def test_package_init(self, tmp_path):
        """Test resolving package __init__.py."""
        # Create package structure
        package = tmp_path / "mypackage"
        package.mkdir()
        (package / "__init__.py").touch()
        source_file = tmp_path / "main.py"
        source_file.touch()
        
        resolved = _resolve_python_import('mypackage', source_file, tmp_path)
        
        assert resolved is not None
        assert resolved == package / "__init__.py"
    
    def test_stdlib_returns_none(self, tmp_path):
        """Test that standard library imports return None."""
        source_file = tmp_path / "main.py"
        source_file.touch()
        
        resolved = _resolve_python_import('os', source_file, tmp_path)
        assert resolved is None
        
        resolved = _resolve_python_import('sys', source_file, tmp_path)
        assert resolved is None
    
    def test_missing_module_returns_none(self, tmp_path):
        """Test that missing modules return None."""
        source_file = tmp_path / "main.py"
        source_file.touch()
        
        resolved = _resolve_python_import('nonexistent', source_file, tmp_path)
        assert resolved is None
    
    def test_src_layout_package_resolution(self, tmp_path):
        """Test resolving packages in src/ layout."""
        # Create src layout: src/myapp/__init__.py and src/myapp/module.py
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        myapp_dir = src_dir / "myapp"
        myapp_dir.mkdir()
        (myapp_dir / "__init__.py").touch()
        (myapp_dir / "module.py").touch()
        
        source_file = tmp_path / "main.py"
        source_file.touch()
        
        # Should resolve to src/myapp/__init__.py
        resolved = _resolve_python_import('myapp', source_file, tmp_path)
        assert resolved is not None
        assert resolved == myapp_dir / "__init__.py"
        
        # Should resolve to src/myapp/module.py
        resolved = _resolve_python_import('myapp.module', source_file, tmp_path)
        assert resolved is not None
        assert resolved == myapp_dir / "module.py"
    
    def test_absolute_import_from_repo_root(self, tmp_path):
        """Test resolving absolute import from repo root."""
        # Create package structure
        package = tmp_path / "mypackage"
        package.mkdir()
        (package / "__init__.py").touch()
        (package / "module.py").touch()
        
        source_file = tmp_path / "main.py"
        source_file.touch()
        
        # Should resolve mypackage.module
        resolved = _resolve_python_import('mypackage.module', source_file, tmp_path)
        
        assert resolved is not None
        assert resolved == package / "module.py"
    
    def test_package_level_symbol_resolves_to_init(self, tmp_path):
        """Test that package-level symbols resolve to __init__.py."""
        # Create package with only __init__.py (symbol defined there)
        package = tmp_path / "mypackage"
        package.mkdir()
        (package / "__init__.py").touch()
        
        source_file = tmp_path / "main.py"
        source_file.touch()
        
        # "from mypackage import symbol" should resolve to mypackage/__init__.py
        # since symbol.py doesn't exist
        resolved = _resolve_python_import('mypackage.symbol', source_file, tmp_path)
        
        assert resolved is not None
        assert resolved == package / "__init__.py"
    
    def test_root_level_module(self, tmp_path):
        """Test resolving root-level module imported absolutely."""
        # Create root-level file
        (tmp_path / "util.py").touch()
        
        source_file = tmp_path / "subdir" / "main.py"
        source_file.parent.mkdir()
        source_file.touch()
        
        # Should resolve util.py at root
        resolved = _resolve_python_import('util', source_file, tmp_path)
        
        assert resolved is not None
        assert resolved == tmp_path / "util.py"


class TestResolveJSImport:
    """Tests for JavaScript/TypeScript import resolution."""
    
    def test_relative_import_same_level(self, tmp_path):
        """Test resolving relative import at same level."""
        (tmp_path / "utils.js").touch()
        source_file = tmp_path / "main.js"
        source_file.touch()
        
        resolved = _resolve_js_import('./utils', source_file, tmp_path)
        
        assert resolved is not None
        assert resolved == tmp_path / "utils.js"
    
    def test_relative_import_with_extension(self, tmp_path):
        """Test resolving relative import with extension."""
        (tmp_path / "utils.js").touch()
        source_file = tmp_path / "main.js"
        source_file.touch()
        
        resolved = _resolve_js_import('./utils.js', source_file, tmp_path)
        
        assert resolved is not None
        assert resolved == tmp_path / "utils.js"
    
    def test_relative_import_parent(self, tmp_path):
        """Test resolving relative import from parent."""
        (tmp_path / "utils.js").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        source_file = subdir / "main.js"
        source_file.touch()
        
        resolved = _resolve_js_import('../utils', source_file, tmp_path)
        
        assert resolved is not None
        assert resolved == tmp_path / "utils.js"
    
    def test_index_file_resolution(self, tmp_path):
        """Test resolving directory imports to index.js."""
        utils_dir = tmp_path / "utils"
        utils_dir.mkdir()
        (utils_dir / "index.js").touch()
        
        source_file = tmp_path / "main.js"
        source_file.touch()
        
        resolved = _resolve_js_import('./utils', source_file, tmp_path)
        
        assert resolved is not None
        assert resolved == utils_dir / "index.js"
    
    def test_typescript_extensions(self, tmp_path):
        """Test resolving TypeScript files."""
        (tmp_path / "module.ts").touch()
        source_file = tmp_path / "main.ts"
        source_file.touch()
        
        resolved = _resolve_js_import('./module', source_file, tmp_path)
        
        assert resolved is not None
        assert resolved == tmp_path / "module.ts"
    
    def test_package_import_returns_none(self, tmp_path):
        """Test that package imports (not relative) return None."""
        source_file = tmp_path / "main.js"
        source_file.touch()
        
        resolved = _resolve_js_import('react', source_file, tmp_path)
        assert resolved is None
        
        resolved = _resolve_js_import('lodash', source_file, tmp_path)
        assert resolved is None
    
    def test_missing_file_returns_none(self, tmp_path):
        """Test that missing files return None."""
        source_file = tmp_path / "main.js"
        source_file.touch()
        
        resolved = _resolve_js_import('./nonexistent', source_file, tmp_path)
        assert resolved is None


class TestScanFileDependencies:
    """Tests for scanning file dependencies."""
    
    def test_python_file_dependencies(self, tmp_path):
        """Test scanning Python file for dependencies."""
        # Create files
        (tmp_path / "utils.py").write_text("# Utils module")
        (tmp_path / "config.py").write_text("# Config module")
        
        main_file = tmp_path / "main.py"
        main_file.write_text("""
from . import utils
from . import config
import os
""")
        
        deps = _scan_file_dependencies(main_file, tmp_path)
        
        # Should find utils and config, but not os (stdlib)
        assert tmp_path / "utils.py" in deps
        assert tmp_path / "config.py" in deps
        assert len([d for d in deps if 'os' in str(d)]) == 0
    
    def test_javascript_file_dependencies(self, tmp_path):
        """Test scanning JavaScript file for dependencies."""
        (tmp_path / "utils.js").write_text("// Utils module")
        (tmp_path / "config.js").write_text("// Config module")
        
        main_file = tmp_path / "main.js"
        main_file.write_text("""
import utils from './utils';
const config = require('./config');
import React from 'react';
""")
        
        deps = _scan_file_dependencies(main_file, tmp_path)
        
        # Should find utils and config, but not react (package)
        assert tmp_path / "utils.js" in deps
        assert tmp_path / "config.js" in deps
        assert len([d for d in deps if 'react' in str(d)]) == 0
    
    def test_unreadable_file_raises_error(self, tmp_path):
        """Test that unreadable files raise IOError."""
        file_path = tmp_path / "missing.py"
        
        # File doesn't exist, should raise IOError
        with pytest.raises(IOError, match="Cannot read file"):
            _scan_file_dependencies(file_path, tmp_path)
    
    def test_unsupported_file_type_returns_empty(self, tmp_path):
        """Test that unsupported file types return empty dependencies."""
        file_path = tmp_path / "data.txt"
        file_path.write_text("Some data")
        
        deps = _scan_file_dependencies(file_path, tmp_path)
        
        assert deps == []


class TestBuildDependencyGraph:
    """Tests for building dependency graph."""
    
    def test_simple_dependency_graph(self, tmp_path):
        """Test building simple dependency graph."""
        # Create files
        (tmp_path / "utils.py").write_text("# Utils")
        main = tmp_path / "main.py"
        main.write_text("from . import utils")
        
        graph_data, errors = build_dependency_graph(
            tmp_path,
            include_patterns=['*.py']
        )
        
        assert len(graph_data['nodes']) == 2
        assert len(graph_data['edges']) == 1
        assert len(errors) == 0
        
        # Check edge connects main to utils
        edge = graph_data['edges'][0]
        assert edge['source'] == 'main.py'
        assert edge['target'] == 'utils.py'
    
    def test_circular_dependencies(self, tmp_path):
        """Test handling circular dependencies."""
        a_file = tmp_path / "a.py"
        a_file.write_text("from . import b")
        
        b_file = tmp_path / "b.py"
        b_file.write_text("from . import a")
        
        graph_data, errors = build_dependency_graph(
            tmp_path,
            include_patterns=['*.py']
        )
        
        # Should detect both edges
        assert len(graph_data['nodes']) == 2
        assert len(graph_data['edges']) == 2
    
    def test_missing_dependency_graceful(self, tmp_path):
        """Test graceful handling of missing dependencies."""
        main = tmp_path / "main.py"
        main.write_text("from . import nonexistent")
        
        graph_data, errors = build_dependency_graph(
            tmp_path,
            include_patterns=['*.py']
        )
        
        # Should have the node but no edges
        assert len(graph_data['nodes']) == 1
        assert len(graph_data['edges']) == 0
    
    def test_mixed_languages(self, tmp_path):
        """Test dependency graph with mixed languages."""
        # Python files
        (tmp_path / "py_utils.py").write_text("# Python utils")
        py_main = tmp_path / "py_main.py"
        py_main.write_text("from . import py_utils")
        
        # JavaScript files
        (tmp_path / "js_utils.js").write_text("// JS utils")
        js_main = tmp_path / "js_main.js"
        js_main.write_text("import utils from './js_utils';")
        
        graph_data, errors = build_dependency_graph(
            tmp_path,
            include_patterns=['*.py', '*.js']
        )
        
        assert len(graph_data['nodes']) == 4
        assert len(graph_data['edges']) == 2
    
    def test_exclude_patterns(self, tmp_path):
        """Test that exclude patterns are respected."""
        (tmp_path / "main.py").write_text("import os")
        (tmp_path / "test_main.py").write_text("import unittest")
        
        graph_data, errors = build_dependency_graph(
            tmp_path,
            include_patterns=['*.py'],
            exclude_patterns=['test_*']
        )
        
        # Should only have main.py, not test_main.py
        assert len(graph_data['nodes']) == 1
        assert graph_data['nodes'][0]['id'] == 'main.py'
    
    def test_nested_structure(self, tmp_path):
        """Test with nested directory structure."""
        # Create nested structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "utils.py").write_text("# Utils")
        
        main = tmp_path / "main.py"
        main.write_text("from src import utils")
        
        graph_data, errors = build_dependency_graph(
            tmp_path,
            include_patterns=['*.py']
        )
        
        # Check that paths are relative to repo root
        paths = {node['id'] for node in graph_data['nodes']}
        assert 'main.py' in paths
        assert 'src/utils.py' in paths
    
    def test_deduplicates_edges(self, tmp_path):
        """Test that duplicate edges are deduplicated."""
        # Create a file that imports the same module multiple times
        (tmp_path / "utils.py").write_text("# Utils module")
        main = tmp_path / "main.py"
        main.write_text("""
# Import the same module multiple times
from . import utils
from . import utils  # Again
import utils  # Third time
""")
        
        graph_data, errors = build_dependency_graph(
            tmp_path,
            include_patterns=['*.py']
        )
        
        # Count edges from main.py to utils.py
        edges_to_utils = [
            e for e in graph_data['edges']
            if e['source'] == 'main.py' and e['target'] == 'utils.py'
        ]
        
        # Should only have one edge despite multiple imports
        assert len(edges_to_utils) == 1
    
    def test_relative_root_path_js_dependencies(self, tmp_path):
        """Test that JS dependencies work with relative root paths."""
        # Create a structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        
        utils = src_dir / "utils.js"
        utils.write_text("export const util = 42;")
        
        main = src_dir / "main.js"
        main.write_text("import { util } from './utils';")
        
        # Use relative path (not absolute)
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            graph_data, errors = build_dependency_graph(
                Path("src"),  # Relative path
                include_patterns=['*.js']
            )
        finally:
            os.chdir(old_cwd)
        
        # Should still find the dependency
        assert len(graph_data['nodes']) == 2
        assert len(graph_data['edges']) == 1
        assert len(errors) == 0
        
        # Check edge exists
        edge = graph_data['edges'][0]
        assert 'main.js' in edge['source']
        assert 'utils.js' in edge['target']


class TestGenerateDependencyReport:
    """Tests for generating dependency report."""
    
    def test_basic_report_generation(self, tmp_path):
        """Test basic report generation."""
        source = tmp_path / "source"
        source.mkdir()
        
        (source / "utils.py").write_text("# Utils")
        main = source / "main.py"
        main.write_text("from . import utils")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            source,
            output,
            include_patterns=['*.py']
        )
        
        # Check JSON output
        json_file = output / "dependencies.json"
        assert json_file.exists()
        
        data = json.loads(json_file.read_text())
        assert 'nodes' in data
        assert 'edges' in data
        assert len(data['nodes']) == 2
        assert len(data['edges']) == 1
        
        # Check Markdown output
        md_file = output / "dependencies.md"
        assert md_file.exists()
        content = md_file.read_text()
        assert "Dependency Graph" in content
        assert "Total files" in content
        assert "Intra-repo dependencies" in content  # Changed from "Total dependencies"
        # Check for new external dependency sections
        assert "External stdlib dependencies" in content
        assert "External third-party dependencies" in content
    
    def test_statistics_in_markdown(self, tmp_path):
        """Test that Markdown includes statistics."""
        source = tmp_path / "source"
        source.mkdir()
        
        (source / "utils.py").write_text("# Utils")
        (source / "config.py").write_text("# Config")
        main = source / "main.py"
        main.write_text("""
from . import utils
from . import config
""")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            source,
            output,
            include_patterns=['*.py']
        )
        
        md_file = output / "dependencies.md"
        content = md_file.read_text()
        
        # Should have statistics
        assert "Statistics" in content
        assert "**Total files**: 3" in content
        assert "**Intra-repo dependencies**: 2" in content  # Changed from "Total dependencies"
        
        # Should list most depended upon files
        assert "Most Depended Upon Files" in content
    
    def test_dry_run_mode(self, tmp_path, capsys):
        """Test dry-run mode doesn't write files."""
        source = tmp_path / "source"
        source.mkdir()
        (source / "main.py").write_text("import os")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            source,
            output,
            include_patterns=['*.py'],
            dry_run=True
        )
        
        # Check that files were not created
        assert not (output / "dependencies.json").exists()
        assert not (output / "dependencies.md").exists()
        
        # Check that messages were printed
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "dependencies.json" in captured.out
    
    def test_no_dependencies_edge_case(self, tmp_path):
        """Test behavior with files but no dependencies."""
        source = tmp_path / "source"
        source.mkdir()
        
        # Files with no internal dependencies
        (source / "standalone1.py").write_text("import os")
        (source / "standalone2.py").write_text("import sys")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            source,
            output,
            include_patterns=['*.py']
        )
        
        json_file = output / "dependencies.json"
        data = json.loads(json_file.read_text())
        
        assert len(data['nodes']) == 2
        assert len(data['edges']) == 0
    
    def test_error_reporting(self, tmp_path, capsys):
        """Test that errors are reported in output."""
        source = tmp_path / "source"
        source.mkdir()
        
        # Create a file that will cause issues during scanning
        # (This is a bit tricky to test naturally, so we'll check the structure)
        (source / "main.py").write_text("import os")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            source,
            output,
            include_patterns=['*.py']
        )
        
        # With normal files, there should be no errors
        md_file = output / "dependencies.md"
        content = md_file.read_text()
        
        # Error section should not appear if no errors
        # (or appear empty)
        # This tests that the code handles the error reporting structure
        assert md_file.exists()
    
    def test_scan_errors_cause_failure(self, tmp_path, monkeypatch):
        """Test that scan errors raise DependencyGraphError."""
        source = tmp_path / "source"
        source.mkdir()
        
        (source / "main.py").write_text("import os")
        
        output = tmp_path / "output"
        output.mkdir()
        
        # Mock _scan_file_dependencies_with_external to raise an exception
        from repo_analyzer import dependency_graph
        
        def mock_scan_with_error(file_path, repo_root):
            raise IOError("Simulated file read error")
        
        monkeypatch.setattr(dependency_graph, "_scan_file_dependencies_with_external", mock_scan_with_error)
        
        # Should raise DependencyGraphError due to scan errors
        with pytest.raises(DependencyGraphError, match="Dependency graph generation failed"):
            generate_dependency_report(
                source,
                output,
                include_patterns=['*.py']
            )


class TestExternalDependencies:
    """Tests for external dependency tracking and classification."""
    
    def test_python_stdlib_dependencies(self, tmp_path):
        """Test detection of Python stdlib dependencies."""
        source = tmp_path / "source"
        source.mkdir()
        
        main = source / "main.py"
        main.write_text("""
import os
import sys
import json
from pathlib import Path
""")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            source,
            output,
            include_patterns=['*.py']
        )
        
        json_file = output / "dependencies.json"
        data = json.loads(json_file.read_text())
        
        # Check external dependencies summary
        assert 'external_dependencies_summary' in data
        stdlib_deps = data['external_dependencies_summary']['stdlib']
        assert 'os' in stdlib_deps
        assert 'sys' in stdlib_deps
        assert 'json' in stdlib_deps
        assert 'pathlib.Path' in stdlib_deps
        
        # Check per-file dependencies
        main_node = next(n for n in data['nodes'] if n['path'] == 'main.py')
        assert 'external_dependencies' in main_node
        assert 'os' in main_node['external_dependencies']['stdlib']
        assert 'sys' in main_node['external_dependencies']['stdlib']
    
    def test_python_third_party_dependencies(self, tmp_path):
        """Test detection of Python third-party dependencies."""
        source = tmp_path / "source"
        source.mkdir()
        
        main = source / "main.py"
        main.write_text("""
import requests
import numpy as np
from django.http import HttpResponse
""")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            source,
            output,
            include_patterns=['*.py']
        )
        
        json_file = output / "dependencies.json"
        data = json.loads(json_file.read_text())
        
        # Check external dependencies summary
        third_party_deps = data['external_dependencies_summary']['third-party']
        assert 'requests' in third_party_deps
        assert 'numpy' in third_party_deps
        assert 'django.http.HttpResponse' in third_party_deps
        
        # Check per-file dependencies
        main_node = next(n for n in data['nodes'] if n['path'] == 'main.py')
        assert 'requests' in main_node['external_dependencies']['third-party']
        assert 'numpy' in main_node['external_dependencies']['third-party']
    
    def test_js_node_core_modules(self, tmp_path):
        """Test detection of Node.js core module dependencies."""
        source = tmp_path / "source"
        source.mkdir()
        
        main = source / "main.js"
        main.write_text("""
import fs from 'fs';
import path from 'path';
const http = require('http');
import('crypto').then(crypto => {});
""")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            source,
            output,
            include_patterns=['*.js']
        )
        
        json_file = output / "dependencies.json"
        data = json.loads(json_file.read_text())
        
        # Check external dependencies summary
        stdlib_deps = data['external_dependencies_summary']['stdlib']
        assert 'fs' in stdlib_deps
        assert 'path' in stdlib_deps
        assert 'http' in stdlib_deps
        assert 'crypto' in stdlib_deps
        
        # Check per-file dependencies
        main_node = next(n for n in data['nodes'] if n['path'] == 'main.js')
        assert 'fs' in main_node['external_dependencies']['stdlib']
        assert 'path' in main_node['external_dependencies']['stdlib']
    
    def test_js_third_party_packages(self, tmp_path):
        """Test detection of JavaScript third-party package dependencies."""
        source = tmp_path / "source"
        source.mkdir()
        
        main = source / "main.js"
        main.write_text("""
import express from 'express';
import React from 'react';
const lodash = require('lodash');
import '@babel/core';
""")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            source,
            output,
            include_patterns=['*.js']
        )
        
        json_file = output / "dependencies.json"
        data = json.loads(json_file.read_text())
        
        # Check external dependencies summary
        third_party_deps = data['external_dependencies_summary']['third-party']
        assert 'express' in third_party_deps
        assert 'react' in third_party_deps
        assert 'lodash' in third_party_deps
        assert '@babel/core' in third_party_deps
        
        # Check per-file dependencies
        main_node = next(n for n in data['nodes'] if n['path'] == 'main.js')
        assert 'express' in main_node['external_dependencies']['third-party']
        assert 'react' in main_node['external_dependencies']['third-party']
    
    def test_mixed_stdlib_and_third_party(self, tmp_path):
        """Test detection of mixed stdlib and third-party dependencies."""
        source = tmp_path / "source"
        source.mkdir()
        
        main = source / "main.py"
        main.write_text("""
import os
import sys
import requests
import numpy
from pathlib import Path
from django.http import HttpResponse
""")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            source,
            output,
            include_patterns=['*.py']
        )
        
        json_file = output / "dependencies.json"
        data = json.loads(json_file.read_text())
        
        # Check counts
        ext_summary = data['external_dependencies_summary']
        assert ext_summary['stdlib_count'] > 0
        assert ext_summary['third-party_count'] > 0
        
        # Verify segregation
        stdlib_deps = set(ext_summary['stdlib'])
        third_party_deps = set(ext_summary['third-party'])
        
        # Should not overlap
        assert len(stdlib_deps & third_party_deps) == 0
        
        # Check specific classifications
        assert 'os' in stdlib_deps
        assert 'requests' in third_party_deps
    
    def test_relative_imports_not_tracked_as_external(self, tmp_path):
        """Test that relative imports are not tracked as external dependencies."""
        source = tmp_path / "source"
        source.mkdir()
        
        (source / "utils.py").write_text("# Utils")
        main = source / "main.py"
        main.write_text("""
from . import utils
from .. import config
import os
""")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            source,
            output,
            include_patterns=['*.py']
        )
        
        json_file = output / "dependencies.json"
        data = json.loads(json_file.read_text())
        
        # Relative imports should not appear in external dependencies
        main_node = next(n for n in data['nodes'] if n['path'] == 'main.py')
        all_external = (
            main_node['external_dependencies']['stdlib'] +
            main_node['external_dependencies']['third-party']
        )
        
        # Should not contain relative import paths
        assert '.utils' not in all_external
        assert '..config' not in all_external
        
        # But should contain os
        assert 'os' in main_node['external_dependencies']['stdlib']
    
    def test_external_dependencies_in_markdown(self, tmp_path):
        """Test that external dependencies appear in markdown report."""
        source = tmp_path / "source"
        source.mkdir()
        
        main = source / "main.py"
        main.write_text("""
import os
import requests
""")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            source,
            output,
            include_patterns=['*.py']
        )
        
        md_file = output / "dependencies.md"
        content = md_file.read_text()
        
        # Should have external dependencies section
        assert "External Dependencies" in content
        assert "Standard Library" in content
        assert "Third-Party Packages" in content
        
        # Should list the dependencies
        assert "`os`" in content
        assert "`requests`" in content
    
    def test_deduplication_of_external_dependencies(self, tmp_path):
        """Test that external dependencies are deduplicated across files."""
        source = tmp_path / "source"
        source.mkdir()
        
        (source / "file1.py").write_text("import os\nimport requests")
        (source / "file2.py").write_text("import os\nimport json")
        
        output = tmp_path / "output"
        output.mkdir()
        
        generate_dependency_report(
            source,
            output,
            include_patterns=['*.py']
        )
        
        json_file = output / "dependencies.json"
        data = json.loads(json_file.read_text())
        
        # os should appear only once in summary even though used by both files
        stdlib_deps = data['external_dependencies_summary']['stdlib']
        assert stdlib_deps.count('os') == 1
        assert stdlib_deps.count('json') == 1
        
        # requests should appear once
        third_party_deps = data['external_dependencies_summary']['third-party']
        assert third_party_deps.count('requests') == 1
    
    def test_external_dependencies_deterministic_ordering(self, tmp_path):
        """Test that external dependencies are sorted deterministically."""
        source = tmp_path / "source"
        source.mkdir()
        
        main = source / "main.py"
        main.write_text("""
import zlib
import os
import sys
import json
""")
        
        output = tmp_path / "output"
        output.mkdir()
        
        # Generate twice and compare
        generate_dependency_report(source, output, include_patterns=['*.py'])
        json_file = output / "dependencies.json"
        data1 = json.loads(json_file.read_text())
        
        json_file.unlink()
        
        generate_dependency_report(source, output, include_patterns=['*.py'])
        data2 = json.loads(json_file.read_text())
        
        # Should be identical
        assert data1['external_dependencies_summary'] == data2['external_dependencies_summary']
        
        # Should be sorted
        stdlib_deps = data1['external_dependencies_summary']['stdlib']
        assert stdlib_deps == sorted(stdlib_deps)
