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

# C/C++ standard library headers
# Source: C standard library and C++ STL
C_CPP_STDLIB = {
    # C standard library headers
    'assert.h', 'ctype.h', 'errno.h', 'float.h', 'limits.h', 'locale.h',
    'math.h', 'setjmp.h', 'signal.h', 'stdarg.h', 'stddef.h', 'stdio.h',
    'stdlib.h', 'string.h', 'time.h', 'iso646.h', 'wchar.h', 'wctype.h',
    'complex.h', 'fenv.h', 'inttypes.h', 'stdbool.h', 'stdint.h', 'tgmath.h',
    # C++ standard library headers (without .h)
    'algorithm', 'array', 'atomic', 'bitset', 'chrono', 'codecvt', 'complex',
    'condition_variable', 'deque', 'exception', 'forward_list', 'fstream',
    'functional', 'future', 'initializer_list', 'iomanip', 'ios', 'iosfwd',
    'iostream', 'istream', 'iterator', 'limits', 'list', 'locale', 'map',
    'memory', 'mutex', 'new', 'numeric', 'ostream', 'queue', 'random', 'ratio',
    'regex', 'set', 'sstream', 'stack', 'stdexcept', 'streambuf', 'string',
    'system_error', 'thread', 'tuple', 'type_traits', 'typeindex', 'typeinfo',
    'unordered_map', 'unordered_set', 'utility', 'valarray', 'vector',
    # C++ C-compatible headers (c-prefixed)
    'cassert', 'cctype', 'cerrno', 'cfenv', 'cfloat', 'cinttypes', 'ciso646',
    'climits', 'clocale', 'cmath', 'csetjmp', 'csignal', 'cstdarg', 'cstddef',
    'cstdint', 'cstdio', 'cstdlib', 'cstring', 'ctime', 'cwchar', 'cwctype',
    # C++11 and later additions
    'filesystem', 'optional', 'variant', 'any', 'string_view', 'span',
    'ranges', 'concepts', 'coroutine', 'compare', 'version', 'source_location',
    # POSIX/system headers (common but not strictly standard)
    'unistd.h', 'fcntl.h', 'sys/types.h', 'sys/stat.h', 'dirent.h', 'pthread.h',
}

# Rust standard library crates and modules
# Source: https://doc.rust-lang.org/std/
RUST_STDLIB = {
    'std', 'core', 'alloc', 'proc_macro', 'test',
    # Common std modules
    'std::io', 'std::fs', 'std::path', 'std::env', 'std::process',
    'std::collections', 'std::string', 'std::vec', 'std::sync', 'std::thread',
    'std::time', 'std::net', 'std::os', 'std::fmt', 'std::error',
    'std::result', 'std::option', 'std::iter', 'std::ops', 'std::cmp',
    'std::convert', 'std::clone', 'std::marker', 'std::mem', 'std::ptr',
    'std::cell', 'std::rc', 'std::arc', 'std::box', 'std::borrow',
}

# Go standard library packages
# Source: https://pkg.go.dev/std
GO_STDLIB = {
    'archive/tar', 'archive/zip', 'bufio', 'bytes', 'compress/bzip2',
    'compress/flate', 'compress/gzip', 'compress/lzw', 'compress/zlib',
    'container/heap', 'container/list', 'container/ring', 'context', 'crypto',
    'crypto/aes', 'crypto/cipher', 'crypto/des', 'crypto/dsa', 'crypto/ecdsa',
    'crypto/ed25519', 'crypto/elliptic', 'crypto/hmac', 'crypto/md5', 'crypto/rand',
    'crypto/rc4', 'crypto/rsa', 'crypto/sha1', 'crypto/sha256', 'crypto/sha512',
    'crypto/subtle', 'crypto/tls', 'crypto/x509', 'database/sql', 'debug/buildinfo',
    'debug/dwarf', 'debug/elf', 'debug/gosym', 'debug/macho', 'debug/pe',
    'debug/plan9obj', 'embed', 'encoding', 'encoding/ascii85', 'encoding/asn1',
    'encoding/base32', 'encoding/base64', 'encoding/binary', 'encoding/csv',
    'encoding/gob', 'encoding/hex', 'encoding/json', 'encoding/pem', 'encoding/xml',
    'errors', 'expvar', 'flag', 'fmt', 'go/ast', 'go/build', 'go/constant',
    'go/doc', 'go/format', 'go/importer', 'go/parser', 'go/printer', 'go/scanner',
    'go/token', 'go/types', 'hash', 'hash/adler32', 'hash/crc32', 'hash/crc64',
    'hash/fnv', 'hash/maphash', 'html', 'html/template', 'image', 'image/color',
    'image/draw', 'image/gif', 'image/jpeg', 'image/png', 'index/suffixarray',
    'io', 'io/fs', 'io/ioutil', 'log', 'log/slog', 'log/syslog', 'math',
    'math/big', 'math/bits', 'math/cmplx', 'math/rand', 'mime', 'mime/multipart',
    'mime/quotedprintable', 'net', 'net/http', 'net/http/cgi', 'net/http/cookiejar',
    'net/http/fcgi', 'net/http/httptest', 'net/http/httptrace', 'net/http/httputil',
    'net/http/pprof', 'net/mail', 'net/netip', 'net/rpc', 'net/rpc/jsonrpc',
    'net/smtp', 'net/textproto', 'net/url', 'os', 'os/exec', 'os/signal',
    'os/user', 'path', 'path/filepath', 'plugin', 'reflect', 'regexp',
    'regexp/syntax', 'runtime', 'runtime/cgo', 'runtime/debug', 'runtime/metrics',
    'runtime/pprof', 'runtime/race', 'runtime/trace', 'sort', 'strconv', 'strings',
    'sync', 'sync/atomic', 'syscall', 'testing', 'testing/fstest', 'testing/iotest',
    'testing/quick', 'text/scanner', 'text/tabwriter', 'text/template',
    'text/template/parse', 'time', 'unicode', 'unicode/utf16', 'unicode/utf8',
    'unsafe',
}

# Java standard library packages (java.* and javax.*)
# Source: Java SE API
JAVA_STDLIB = {
    'java.applet', 'java.awt', 'java.beans', 'java.io', 'java.lang', 'java.math',
    'java.net', 'java.nio', 'java.rmi', 'java.security', 'java.sql', 'java.text',
    'java.time', 'java.util', 'javax.accessibility', 'javax.activation', 'javax.activity',
    'javax.annotation', 'javax.crypto', 'javax.imageio', 'javax.jws', 'javax.lang',
    'javax.management', 'javax.naming', 'javax.net', 'javax.print', 'javax.rmi',
    'javax.script', 'javax.security', 'javax.sound', 'javax.sql', 'javax.swing',
    'javax.tools', 'javax.transaction', 'javax.xml',
}

# C# standard library namespaces (System.*)
# Source: .NET Framework/Core API
CSHARP_STDLIB = {
    'System', 'System.Collections', 'System.Collections.Generic', 'System.ComponentModel',
    'System.Configuration', 'System.Data', 'System.Diagnostics', 'System.Drawing',
    'System.Globalization', 'System.IO', 'System.Linq', 'System.Net', 'System.Reflection',
    'System.Resources', 'System.Runtime', 'System.Security', 'System.Text', 'System.Threading',
    'System.Timers', 'System.Web', 'System.Windows', 'System.Xml', 'Microsoft.CSharp',
    'Microsoft.VisualBasic', 'Microsoft.Win32',
}

# Swift standard library modules
# Source: Swift standard library
SWIFT_STDLIB = {
    'Swift', 'Foundation', 'Dispatch', 'Darwin', 'Glibc', 'XCTest',
    # Common Foundation types
    'CoreFoundation', 'CoreGraphics', 'CoreData', 'CoreLocation', 'CoreImage',
    'UIKit', 'AppKit', 'SwiftUI', 'Combine',
}

# SQL standard objects (keywords and built-in functions are not typically "imported")
# This is for SQL include/reference statements, which are non-standard
# We track common schema references and vendor-specific includes
SQL_STDLIB = {
    # Standard SQL schemas
    'information_schema', 'pg_catalog', 'sys', 'mysql', 'performance_schema',
    # Common system tables/views
    'dual', 'sysibm', 'syscat', 'sysstat',
}

# Perl core modules (shipped with Perl distribution)
# Source: https://perldoc.perl.org/modules
PERL_STDLIB = {
    # Essential modules
    'strict', 'warnings', 'utf8', 'vars', 'constant', 'lib', 'feature',
    'base', 'parent', 'fields', 'mro', 'attributes', 'version',
    # File and I/O
    'File::Basename', 'File::Copy', 'File::Find', 'File::Path', 'File::Spec',
    'File::Temp', 'File::Compare', 'File::stat', 'FileHandle', 'IO::File',
    'IO::Handle', 'IO::Dir', 'IO::Socket', 'IO::Select', 'IO::Pipe',
    # Data structures
    'Data::Dumper', 'Storable', 'Scalar::Util', 'List::Util', 'Hash::Util',
    'Tie::Hash', 'Tie::Array', 'Tie::Scalar',
    # Text processing
    'Text::Wrap', 'Text::Tabs', 'Text::Abbrev', 'Text::ParseWords',
    # System and process
    'POSIX', 'Errno', 'Config', 'Cwd', 'Env', 'English', 'IPC::Open2', 'IPC::Open3',
    'IPC::Cmd', 'FindBin', 'Getopt::Long', 'Getopt::Std',
    # Time and date
    'Time::Local', 'Time::HiRes', 'Time::gmtime', 'Time::localtime', 'Time::Piece',
    # Testing
    'Test::More', 'Test::Simple', 'Test::Harness', 'Test::Builder',
    # Networking
    'Socket', 'Net::FTP', 'Net::SMTP', 'Net::HTTP', 'Net::Domain', 'Net::Ping',
    'LWP::Simple', 'HTTP::Request', 'HTTP::Response', 'URI',
    # Databases
    'DBI', 'DBD', 'AnyDBM_File', 'DB_File', 'GDBM_File', 'NDBM_File', 'ODBM_File',
    'SDBM_File',
    # Encoding
    'Encode', 'Encode::Guess', 'Digest::MD5', 'Digest::SHA', 'MIME::Base64',
    'MIME::QuotedPrint',
    # Archives
    'Archive::Tar', 'Archive::Zip', 'Compress::Zlib',
    # Math
    'Math::BigInt', 'Math::BigFloat', 'Math::Complex', 'Math::Trig',
    # Misc utilities
    'Benchmark', 'Carp', 'Exporter', 'ExtUtils::MakeMaker', 'AutoLoader',
    'SelfLoader', 'Symbol', 'Sys::Hostname', 'Sys::Syslog',
}

# Common Perl pragmas (lowercase, no ::) - subset of PERL_STDLIB
PERL_PRAGMAS = {'strict', 'warnings', 'utf8', 'vars', 'constant', 'lib', 'feature'}

# Assembly languages don't have standard library imports
# Assembly source files include headers or other .inc/.s files
# These are typically project-specific, not standard library
ASM_STDLIB = set()  # Empty - assembly has no standard library modules


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


def classify_c_cpp_import(header_name: str) -> DependencyType:
    """
    Classify a C/C++ include as stdlib or third-party.
    
    Args:
        header_name: The header name to classify (e.g., 'stdio.h', 'vector', 'boost/shared_ptr.hpp')
    
    Returns:
        Classification as 'stdlib', 'third-party', or 'unknown'
    
    Examples:
        >>> classify_c_cpp_import('stdio.h')
        'stdlib'
        >>> classify_c_cpp_import('vector')
        'stdlib'
        >>> classify_c_cpp_import('boost/shared_ptr.hpp')
        'third-party'
    """
    # Remove path components to get base header name
    base_name = header_name.split('/')[-1]
    
    # Check if it's a standard library header
    if base_name in C_CPP_STDLIB:
        return "stdlib"
    
    # Check full path for standard headers (e.g., sys/types.h)
    if header_name in C_CPP_STDLIB:
        return "stdlib"
    
    # Everything else is third-party
    return "third-party"


def classify_rust_import(module_name: str) -> DependencyType:
    """
    Classify a Rust use/mod statement as stdlib or third-party.
    
    Args:
        module_name: The module name to classify (e.g., 'std::io', 'serde', 'crate::utils')
    
    Returns:
        Classification as 'stdlib', 'third-party', or 'unknown'
    
    Examples:
        >>> classify_rust_import('std::io')
        'stdlib'
        >>> classify_rust_import('core::fmt')
        'stdlib'
        >>> classify_rust_import('serde')
        'third-party'
    """
    # Handle crate-relative imports
    if module_name.startswith('crate::') or module_name.startswith('self::') or module_name.startswith('super::'):
        return "unknown"
    
    # Extract the top-level crate/module name
    top_level = module_name.split('::')[0]
    
    # Check if it's a stdlib crate
    if top_level in RUST_STDLIB:
        return "stdlib"
    
    # Check full path for nested std modules
    if module_name in RUST_STDLIB:
        return "stdlib"
    
    # Everything else is third-party
    return "third-party"


def classify_go_import(package_name: str) -> DependencyType:
    """
    Classify a Go import as stdlib or third-party.
    
    Args:
        package_name: The package name to classify (e.g., 'fmt', 'github.com/user/repo')
    
    Returns:
        Classification as 'stdlib', 'third-party', or 'unknown'
    
    Examples:
        >>> classify_go_import('fmt')
        'stdlib'
        >>> classify_go_import('net/http')
        'stdlib'
        >>> classify_go_import('github.com/user/repo')
        'third-party'
    """
    # Go stdlib packages don't contain domain names
    if '.' in package_name.split('/')[0]:
        # Contains domain name (e.g., github.com/...)
        return "third-party"
    
    # Check if it's a stdlib package
    if package_name in GO_STDLIB:
        return "stdlib"
    
    # Everything else is third-party
    return "third-party"


def classify_java_import(class_name: str) -> DependencyType:
    """
    Classify a Java import as stdlib or third-party.
    
    Args:
        class_name: The class name to classify (e.g., 'java.util.List', 'com.example.MyClass')
    
    Returns:
        Classification as 'stdlib', 'third-party', or 'unknown'
    
    Examples:
        >>> classify_java_import('java.util.List')
        'stdlib'
        >>> classify_java_import('javax.swing.JFrame')
        'stdlib'
        >>> classify_java_import('com.example.MyClass')
        'third-party'
    """
    # Extract the top-level package
    parts = class_name.split('.')
    if not parts:
        return "unknown"
    
    # Check for java.* and javax.* packages
    top_level = parts[0]
    if top_level in ['java', 'javax']:
        # Check if the second level is in stdlib
        if len(parts) >= 2:
            package = '.'.join(parts[:2])
            if package in JAVA_STDLIB:
                return "stdlib"
        return "stdlib"  # Assume all java.* and javax.* are stdlib
    
    # Everything else is third-party
    return "third-party"


def classify_csharp_import(namespace: str) -> DependencyType:
    """
    Classify a C# using statement as stdlib or third-party.
    
    Args:
        namespace: The namespace to classify (e.g., 'System.IO', 'Newtonsoft.Json')
    
    Returns:
        Classification as 'stdlib', 'third-party', or 'unknown'
    
    Examples:
        >>> classify_csharp_import('System.IO')
        'stdlib'
        >>> classify_csharp_import('System.Collections.Generic')
        'stdlib'
        >>> classify_csharp_import('Newtonsoft.Json')
        'third-party'
    """
    # Extract top-level namespace
    parts = namespace.split('.')
    if not parts:
        return "unknown"
    
    top_level = parts[0]
    
    # Check for System.* and Microsoft.* standard namespaces
    # All System.* and Microsoft.* namespaces are considered stdlib
    if top_level in ['System', 'Microsoft']:
        return "stdlib"
    
    # Check if full namespace is explicitly in stdlib list
    if namespace in CSHARP_STDLIB:
        return "stdlib"
    
    # Everything else is third-party
    return "third-party"


def classify_swift_import(module_name: str) -> DependencyType:
    """
    Classify a Swift import as stdlib or third-party.
    
    Args:
        module_name: The module name to classify (e.g., 'Foundation', 'Alamofire')
    
    Returns:
        Classification as 'stdlib', 'third-party', or 'unknown'
    
    Examples:
        >>> classify_swift_import('Foundation')
        'stdlib'
        >>> classify_swift_import('UIKit')
        'stdlib'
        >>> classify_swift_import('Alamofire')
        'third-party'
    """
    # Check if it's a stdlib module
    if module_name in SWIFT_STDLIB:
        return "stdlib"
    
    # Everything else is third-party
    return "third-party"


def classify_sql_import(reference: str) -> DependencyType:
    """
    Classify a SQL include/reference as stdlib (system schema) or third-party.
    
    Args:
        reference: The schema/object reference to classify
    
    Returns:
        Classification as 'stdlib', 'third-party', or 'unknown'
    
    Examples:
        >>> classify_sql_import('information_schema')
        'stdlib'
        >>> classify_sql_import('pg_catalog')
        'stdlib'
        >>> classify_sql_import('my_custom_schema')
        'third-party'
    """
    # Check if it's a system schema/catalog
    if reference in SQL_STDLIB:
        return "stdlib"
    
    # Everything else is third-party
    return "third-party"


def classify_perl_import(module_name: str) -> DependencyType:
    """
    Classify a Perl use/require statement as stdlib or third-party.
    
    Args:
        module_name: The module name to classify (e.g., 'File::Copy', 'Moose', 'Local::Module')
    
    Returns:
        Classification as 'stdlib', 'third-party', or 'unknown'
    
    Examples:
        >>> classify_perl_import('File::Copy')
        'stdlib'
        >>> classify_perl_import('Moose')
        'third-party'
        >>> classify_perl_import('strict')
        'stdlib'
    """
    # Normalize module name
    module_name = module_name.strip()
    
    # Handle file paths (e.g., require "path/to/file.pm")
    if '/' in module_name or '\\' in module_name or module_name.endswith('.pm'):
        # File path, not a module name - treat as unknown
        return "unknown"
    
    # Check if it's a core module
    if module_name in PERL_STDLIB:
        return "stdlib"
    
    # Pragmas (lowercase, no ::) are usually core
    if module_name.islower() and '::' not in module_name:
        # Check against known pragma list
        if module_name in PERL_PRAGMAS:
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
    elif language in ["C", "C++"]:
        return classify_c_cpp_import(module_name)
    elif language == "Rust":
        return classify_rust_import(module_name)
    elif language == "Go":
        return classify_go_import(module_name)
    elif language == "Java":
        return classify_java_import(module_name)
    elif language == "C#":
        return classify_csharp_import(module_name)
    elif language == "Swift":
        return classify_swift_import(module_name)
    elif language == "SQL":
        return classify_sql_import(module_name)
    elif language == "Perl":
        return classify_perl_import(module_name)
    elif language == "ASM":
        # Assembly doesn't have external dependencies in the traditional sense
        return "unknown"
    else:
        # For unsupported languages, return unknown
        return "unknown"
