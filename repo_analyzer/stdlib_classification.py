# Copyright (c) 2025 John Brosnihan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Deterministic classification of external dependencies as stdlib vs third-party.

This module provides offline classification without network calls or package manager invocations.
Classification tables are maintained in code for Python and JavaScript/TypeScript ecosystems.
"""

from typing import Literal

DependencyType = Literal["stdlib", "third-party", "unknown"]


# Python standard library modules (Python 3.8+)
# Source: https://docs.python.org/3/py-modindex.html
# This list includes the most common stdlib modules for practical use
PYTHON_STDLIB = {
    '__future__', '__main__', '_thread', 'abc', 'aifc', 'argparse', 'array',
    'ast', 'asynchat', 'asyncio', 'asyncore', 'atexit', 'audioop', 'base64',
    'bdb', 'binascii', 'binhex', 'bisect', 'builtins', 'bz2', 'calendar',
    'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs', 'codeop',
    'collections', 'colorsys', 'compileall', 'concurrent', 'configparser',
    'contextlib', 'contextvars', 'copy', 'copyreg', 'cProfile', 'crypt',
    'csv', 'ctypes', 'curses', 'dataclasses', 'datetime', 'dbm', 'decimal',
    'difflib', 'dis', 'distutils', 'doctest', 'email', 'encodings', 'enum',
    'errno', 'faulthandler', 'fcntl', 'filecmp', 'fileinput', 'fnmatch',
    'formatter', 'fractions', 'ftplib', 'functools', 'gc', 'getopt', 'getpass',
    'gettext', 'glob', 'graphlib', 'grp', 'gzip', 'hashlib', 'heapq', 'hmac',
    'html', 'http', 'imaplib', 'imghdr', 'imp', 'importlib', 'inspect', 'io',
    'ipaddress', 'itertools', 'json', 'keyword', 'lib2to3', 'linecache',
    'locale', 'logging', 'lzma', 'mailbox', 'mailcap', 'marshal', 'math',
    'mimetypes', 'mmap', 'modulefinder', 'msilib', 'msvcrt', 'multiprocessing',
    'netrc', 'nis', 'nntplib', 'numbers', 'operator', 'optparse', 'os',
    'ossaudiodev', 'parser', 'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes',
    'pkgutil', 'platform', 'plistlib', 'poplib', 'posix', 'posixpath', 'pprint',
    'profile', 'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue',
    'quopri', 'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter',
    'runpy', 'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex',
    'shutil', 'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket',
    'socketserver', 'spwd', 'sqlite3', 'ssl', 'stat', 'statistics', 'string',
    'stringprep', 'struct', 'subprocess', 'sunau', 'symbol', 'symtable', 'sys',
    'sysconfig', 'syslog', 'tabnanny', 'tarfile', 'telnetlib', 'tempfile',
    'termios', 'test', 'textwrap', 'threading', 'time', 'timeit', 'tkinter',
    'token', 'tokenize', 'tomllib', 'trace', 'traceback', 'tracemalloc', 'tty',
    'turtle', 'turtledemo', 'types', 'typing', 'unicodedata',
    'unittest', 'urllib', 'uu', 'uuid', 'venv', 'warnings', 'wave', 'weakref',
    'webbrowser', 'winreg', 'winsound', 'wsgiref', 'xdrlib', 'xml', 'xmlrpc',
    'zipapp', 'zipfile', 'zipimport', 'zlib', 'zoneinfo',
}

# Node.js core modules (built-in modules)
# Source: https://nodejs.org/api/
# These are available without npm install
NODE_CORE_MODULES = {
    'assert', 'async_hooks', 'buffer', 'child_process', 'cluster', 'console',
    'constants', 'crypto', 'dgram', 'diagnostics_channel', 'dns', 'domain',
    'events', 'fs', 'http', 'http2', 'https', 'inspector', 'module', 'net',
    'os', 'path', 'perf_hooks', 'process', 'punycode', 'querystring', 'readline',
    'repl', 'stream', 'string_decoder', 'sys', 'timers', 'tls', 'trace_events',
    'tty', 'url', 'util', 'v8', 'vm', 'wasi', 'worker_threads', 'zlib',
    # Node.js also supports 'node:' prefix for core modules
    'node:assert', 'node:async_hooks', 'node:buffer', 'node:child_process',
    'node:cluster', 'node:console', 'node:constants', 'node:crypto', 'node:dgram',
    'node:diagnostics_channel', 'node:dns', 'node:domain', 'node:events',
    'node:fs', 'node:http', 'node:http2', 'node:https', 'node:inspector',
    'node:module', 'node:net', 'node:os', 'node:path', 'node:perf_hooks',
    'node:process', 'node:punycode', 'node:querystring', 'node:readline',
    'node:repl', 'node:stream', 'node:string_decoder', 'node:sys', 'node:timers',
    'node:tls', 'node:trace_events', 'node:tty', 'node:url', 'node:util',
    'node:v8', 'node:vm', 'node:wasi', 'node:worker_threads', 'node:zlib',
    # Legacy/deprecated modules
    'freelist', '_linklist', 'smalloc',
    # Internal modules (not typically imported but may appear)
    '_http_agent', '_http_client', '_http_common', '_http_incoming',
    '_http_outgoing', '_http_server', '_stream_duplex', '_stream_passthrough',
    '_stream_readable', '_stream_transform', '_stream_wrap', '_stream_writable',
    '_tls_common', '_tls_wrap',
}

# Web platform APIs available in browsers and Deno
# These are NOT Node.js modules but are commonly used in frontend code
# For our purposes, we'll classify these as "stdlib" when in browser/Deno context
BROWSER_WEB_APIS = {
    # Not applicable for import classification as these are global objects
    # Listed here for documentation purposes
}


def classify_python_import(module_name: str) -> DependencyType:
    """
    Classify a Python import as stdlib, third-party, or unknown.
    
    Args:
        module_name: The module name to classify (e.g., 'os', 'requests', 'mypackage.submodule')
    
    Returns:
        Classification as 'stdlib', 'third-party', or 'unknown'
    
    Examples:
        >>> classify_python_import('os')
        'stdlib'
        >>> classify_python_import('requests')
        'third-party'
        >>> classify_python_import('mypackage.submodule')
        'third-party'
    """
    # Extract the top-level module name
    top_level = module_name.split('.')[0]
    
    # Check if it's a stdlib module
    if top_level in PYTHON_STDLIB:
        return "stdlib"
    
    # Check for relative imports (start with dots)
    if module_name.startswith('.'):
        # Relative imports are intra-package, not external
        # This shouldn't be called for these, but return unknown if it is
        return "unknown"
    
    # Everything else is third-party
    return "third-party"


def classify_js_import(module_name: str) -> DependencyType:
    """
    Classify a JavaScript/TypeScript import as stdlib (core), third-party, or unknown.
    
    For JS/TS, "stdlib" means Node.js core modules. Browser APIs are not classified
    as they're not imported as modules.
    
    Args:
        module_name: The module name to classify (e.g., 'fs', 'express', 'lodash')
    
    Returns:
        Classification as 'stdlib', 'third-party', or 'unknown'
    
    Examples:
        >>> classify_js_import('fs')
        'stdlib'
        >>> classify_js_import('node:fs')
        'stdlib'
        >>> classify_js_import('express')
        'third-party'
        >>> classify_js_import('./utils')
        'unknown'
    """
    # Handle empty string
    if not module_name:
        return "unknown"
    
    # Skip relative/absolute imports (these are file paths, not package imports)
    if module_name.startswith('.') or module_name.startswith('/'):
        return "unknown"
    
    # Extract the package name (handle scoped packages like @org/package)
    if module_name.startswith('@'):
        # Scoped package: @org/package or @org/package/subpath
        parts = module_name.split('/')
        if len(parts) >= 2:
            package_name = '/'.join(parts[:2])
        else:
            package_name = module_name
    else:
        # Regular package: package or package/subpath
        package_name = module_name.split('/')[0]
    
    # Check if it's a Node.js core module
    if package_name in NODE_CORE_MODULES:
        return "stdlib"
    
    # Also check without 'node:' prefix
    if module_name.startswith('node:'):
        bare_name = module_name[5:]  # Remove 'node:' prefix
        if bare_name in NODE_CORE_MODULES:
            return "stdlib"
    
    # Everything else is third-party
    return "third-party"


def classify_import(module_name: str, language: str) -> DependencyType:
    """
    Classify an import based on the source file's language.
    
    Args:
        module_name: The module/package name to classify
        language: The programming language ('Python', 'JavaScript', 'TypeScript', etc.)
    
    Returns:
        Classification as 'stdlib', 'third-party', or 'unknown'
    """
    if language == "Python":
        return classify_python_import(module_name)
    elif language in ["JavaScript", "TypeScript"]:
        return classify_js_import(module_name)
    else:
        # For unsupported languages, return unknown
        return "unknown"
