# Copyright (c) 2025 John Brosnihan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Tests for stdlib_classification module.
"""

import pytest

from repo_analyzer.stdlib_classification import (
    classify_python_import,
    classify_js_import,
    classify_import,
    PYTHON_STDLIB,
    NODE_CORE_MODULES,
)


class TestClassifyPythonImport:
    """Tests for Python import classification."""
    
    def test_stdlib_modules(self):
        """Test classification of Python stdlib modules."""
        # Common stdlib modules
        assert classify_python_import('os') == 'stdlib'
        assert classify_python_import('sys') == 'stdlib'
        assert classify_python_import('json') == 'stdlib'
        assert classify_python_import('pathlib') == 'stdlib'
        assert classify_python_import('typing') == 'stdlib'
        assert classify_python_import('collections') == 'stdlib'
        assert classify_python_import('asyncio') == 'stdlib'
        assert classify_python_import('datetime') == 'stdlib'
        assert classify_python_import('re') == 'stdlib'
        assert classify_python_import('unittest') == 'stdlib'
    
    def test_stdlib_submodules(self):
        """Test classification of Python stdlib submodules."""
        # Submodules should be classified based on top-level module
        assert classify_python_import('os.path') == 'stdlib'
        assert classify_python_import('collections.abc') == 'stdlib'
        assert classify_python_import('urllib.parse') == 'stdlib'
        assert classify_python_import('email.mime.text') == 'stdlib'
        assert classify_python_import('xml.etree.ElementTree') == 'stdlib'
    
    def test_third_party_modules(self):
        """Test classification of third-party Python packages."""
        # Common third-party packages
        assert classify_python_import('requests') == 'third-party'
        assert classify_python_import('numpy') == 'third-party'
        assert classify_python_import('pandas') == 'third-party'
        assert classify_python_import('django') == 'third-party'
        assert classify_python_import('flask') == 'third-party'
        assert classify_python_import('pytest') == 'third-party'
        assert classify_python_import('sqlalchemy') == 'third-party'
    
    def test_third_party_submodules(self):
        """Test classification of third-party submodules."""
        assert classify_python_import('requests.adapters') == 'third-party'
        assert classify_python_import('django.contrib.auth') == 'third-party'
        assert classify_python_import('flask.views') == 'third-party'
    
    def test_relative_imports(self):
        """Test classification of relative imports."""
        # Relative imports should return unknown
        assert classify_python_import('.utils') == 'unknown'
        assert classify_python_import('..config') == 'unknown'
        assert classify_python_import('...parent.module') == 'unknown'
    
    def test_custom_modules(self):
        """Test classification of custom/project modules."""
        # Project-specific modules are third-party
        assert classify_python_import('my_project') == 'third-party'
        assert classify_python_import('my_app.models') == 'third-party'
        assert classify_python_import('repo_analyzer') == 'third-party'


class TestClassifyJsImport:
    """Tests for JavaScript/TypeScript import classification."""
    
    def test_node_core_modules(self):
        """Test classification of Node.js core modules."""
        # Common Node.js core modules
        assert classify_js_import('fs') == 'stdlib'
        assert classify_js_import('path') == 'stdlib'
        assert classify_js_import('http') == 'stdlib'
        assert classify_js_import('https') == 'stdlib'
        assert classify_js_import('crypto') == 'stdlib'
        assert classify_js_import('util') == 'stdlib'
        assert classify_js_import('stream') == 'stdlib'
        assert classify_js_import('events') == 'stdlib'
        assert classify_js_import('buffer') == 'stdlib'
        assert classify_js_import('url') == 'stdlib'
    
    def test_node_prefix_modules(self):
        """Test classification of Node.js modules with 'node:' prefix."""
        assert classify_js_import('node:fs') == 'stdlib'
        assert classify_js_import('node:path') == 'stdlib'
        assert classify_js_import('node:http') == 'stdlib'
        assert classify_js_import('node:crypto') == 'stdlib'
    
    def test_node_core_subpaths(self):
        """Test classification of Node.js core modules with subpaths."""
        # Node core modules can have subpaths (e.g., fs/promises)
        assert classify_js_import('fs/promises') == 'stdlib'
        assert classify_js_import('stream/promises') == 'stdlib'
        assert classify_js_import('path/posix') == 'stdlib'
    
    def test_third_party_packages(self):
        """Test classification of third-party npm packages."""
        # Common third-party packages
        assert classify_js_import('express') == 'third-party'
        assert classify_js_import('react') == 'third-party'
        assert classify_js_import('lodash') == 'third-party'
        assert classify_js_import('axios') == 'third-party'
        assert classify_js_import('webpack') == 'third-party'
        assert classify_js_import('typescript') == 'third-party'
        assert classify_js_import('prettier') == 'third-party'
    
    def test_scoped_packages(self):
        """Test classification of scoped npm packages."""
        # Scoped packages are third-party
        assert classify_js_import('@babel/core') == 'third-party'
        assert classify_js_import('@types/node') == 'third-party'
        assert classify_js_import('@angular/core') == 'third-party'
        assert classify_js_import('@emotion/react') == 'third-party'
    
    def test_scoped_packages_with_subpaths(self):
        """Test classification of scoped packages with subpaths."""
        assert classify_js_import('@babel/core/lib/config') == 'third-party'
        assert classify_js_import('@types/node/fs') == 'third-party'
    
    def test_third_party_subpaths(self):
        """Test classification of third-party packages with subpaths."""
        assert classify_js_import('lodash/debounce') == 'third-party'
        assert classify_js_import('react/jsx-runtime') == 'third-party'
        assert classify_js_import('express/lib/router') == 'third-party'
    
    def test_relative_imports(self):
        """Test classification of relative file imports."""
        # Relative imports are file paths, not packages (unknown)
        assert classify_js_import('./utils') == 'unknown'
        assert classify_js_import('../config') == 'unknown'
        assert classify_js_import('../../lib/helper') == 'unknown'
        assert classify_js_import('./') == 'unknown'
    
    def test_absolute_path_imports(self):
        """Test classification of absolute path imports."""
        # Absolute paths are file imports (unknown)
        assert classify_js_import('/src/utils') == 'unknown'
        assert classify_js_import('/lib/config') == 'unknown'


class TestClassifyImport:
    """Tests for language-agnostic import classification."""
    
    def test_python_classification(self):
        """Test classification for Python language."""
        assert classify_import('os', 'Python') == 'stdlib'
        assert classify_import('requests', 'Python') == 'third-party'
        assert classify_import('.utils', 'Python') == 'unknown'
    
    def test_javascript_classification(self):
        """Test classification for JavaScript language."""
        assert classify_import('fs', 'JavaScript') == 'stdlib'
        assert classify_import('express', 'JavaScript') == 'third-party'
        assert classify_import('./config', 'JavaScript') == 'unknown'
    
    def test_typescript_classification(self):
        """Test classification for TypeScript language."""
        assert classify_import('path', 'TypeScript') == 'stdlib'
        assert classify_import('react', 'TypeScript') == 'third-party'
        assert classify_import('../utils', 'TypeScript') == 'unknown'
    
    def test_unsupported_language(self):
        """Test classification for unsupported languages."""
        # Unsupported languages return unknown
        assert classify_import('some_module', 'Ruby') == 'unknown'
        assert classify_import('some_module', 'Java') == 'unknown'
        assert classify_import('some_module', 'Go') == 'unknown'
        assert classify_import('some_module', 'Unknown') == 'unknown'


class TestStdlibTables:
    """Tests for stdlib/core module tables."""
    
    def test_python_stdlib_table(self):
        """Test Python stdlib table is comprehensive."""
        # Verify some essential modules are present
        essential = ['os', 'sys', 'json', 're', 'pathlib', 'typing', 'collections',
                     'datetime', 'asyncio', 'unittest', 'argparse', 'subprocess']
        for module in essential:
            assert module in PYTHON_STDLIB, f"{module} should be in PYTHON_STDLIB"
    
    def test_node_core_modules_table(self):
        """Test Node.js core modules table is comprehensive."""
        # Verify some essential modules are present
        essential = ['fs', 'path', 'http', 'https', 'crypto', 'util', 'stream',
                     'events', 'buffer', 'url', 'os', 'process']
        for module in essential:
            assert module in NODE_CORE_MODULES, f"{module} should be in NODE_CORE_MODULES"
    
    def test_node_prefix_variants(self):
        """Test that node: prefix variants are included."""
        # Should have both bare and node: prefixed versions
        assert 'fs' in NODE_CORE_MODULES
        assert 'node:fs' in NODE_CORE_MODULES
        assert 'path' in NODE_CORE_MODULES
        assert 'node:path' in NODE_CORE_MODULES
    
    def test_tables_are_sets(self):
        """Test that tables are defined as sets."""
        # Sets provide O(1) lookup which is important for performance
        assert isinstance(PYTHON_STDLIB, set)
        assert isinstance(NODE_CORE_MODULES, set)
    
    def test_tables_not_empty(self):
        """Test that tables contain entries."""
        assert len(PYTHON_STDLIB) > 100, "PYTHON_STDLIB should have 100+ modules"
        assert len(NODE_CORE_MODULES) > 20, "NODE_CORE_MODULES should have 20+ modules"


class TestEdgeCases:
    """Tests for edge cases and corner scenarios."""
    
    def test_empty_string(self):
        """Test classification of empty strings."""
        assert classify_python_import('') == 'third-party'
        assert classify_js_import('') == 'unknown'
    
    def test_single_dot(self):
        """Test classification of single dot."""
        assert classify_python_import('.') == 'unknown'
        assert classify_js_import('.') == 'unknown'
    
    def test_multiple_dots(self):
        """Test classification of multiple dots without module name."""
        assert classify_python_import('...') == 'unknown'
        # JS treats this as relative path
        assert classify_js_import('...') == 'unknown'
    
    def test_whitespace_in_names(self):
        """Test that whitespace doesn't break classification."""
        # These should be treated as third-party since they don't match stdlib
        assert classify_python_import('my module') == 'third-party'
        assert classify_js_import('my module') == 'third-party'
    
    def test_case_sensitivity(self):
        """Test that classification is case-sensitive."""
        # Python stdlib modules are lowercase
        assert classify_python_import('OS') == 'third-party'  # OS is not in stdlib
        assert classify_python_import('os') == 'stdlib'
        
        # Node core modules are lowercase
        assert classify_js_import('FS') == 'third-party'  # FS is not a core module
        assert classify_js_import('fs') == 'stdlib'
