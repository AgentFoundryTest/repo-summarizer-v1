# Copyright (c) 2025 John Brosnihan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Parser adapters for low-level languages (C, C++, Rust, ASM, Perl).

This module provides a pluggable architecture for integrating structured parsers
(tree-sitter, libclang) with caching to maintain performance. It avoids regex-only
implementations for structural understanding.

Design Principles:
1. Parser unavailability is graceful - registry tracks parser availability
2. Caching layer keeps performance on par with regex approaches
3. Extension interface supports AST traversal, symbol extraction, and include resolution
4. Assembly-specific semantics (.globl labels) are properly surfaced
5. No breaking changes to existing Python analysis entry points

Parser Availability:
- Tree-sitter: Optional dependency (graceful degradation if unavailable)
- Libclang: Optional dependency for C/C++ (graceful degradation if unavailable)
- Fallback: Regex-based heuristics when structured parsers unavailable
"""

from typing import Dict, List, Optional, Set, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import re


class ParserType(Enum):
    """Types of parsers available for language analysis."""
    TREE_SITTER = "tree-sitter"
    LIBCLANG = "libclang"
    REGEX_FALLBACK = "regex-fallback"
    NONE = "none"


@dataclass
class ParserCapability:
    """
    Defines what a parser can extract from source files.
    
    Attributes:
        can_extract_symbols: Can extract function/class/global declarations
        can_extract_dependencies: Can extract import/include statements
        can_extract_asm_labels: Can extract assembly labels (.globl, etc.)
        parser_type: Which parser provides these capabilities
        available: Whether the parser is currently available (dependencies installed)
        unavailable_reason: Explanation if parser is unavailable
    """
    can_extract_symbols: bool = False
    can_extract_dependencies: bool = False
    can_extract_asm_labels: bool = False
    parser_type: ParserType = ParserType.NONE
    available: bool = False
    unavailable_reason: Optional[str] = None


@dataclass
class ParsedSymbols:
    """
    Structured result of symbol extraction.
    
    Attributes:
        functions: List of function names/signatures
        classes: List of class names
        variables: List of global variable names
        asm_labels: List of assembly labels (.globl directives)
        warnings: List of parsing warnings
        parser_used: Which parser was used for extraction
    """
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    asm_labels: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    parser_used: ParserType = ParserType.NONE


# Global cache for parser availability checks
_parser_availability_cache: Dict[str, ParserCapability] = {}


def _check_tree_sitter_available() -> Tuple[bool, Optional[str]]:
    """
    Check if tree-sitter is available for use.
    
    Returns:
        Tuple of (available, reason_if_unavailable)
    """
    try:
        import tree_sitter
        return True, None
    except ImportError:
        return False, "tree-sitter Python package not installed (pip install tree-sitter)"
    except Exception as e:
        return False, f"tree-sitter import failed: {str(e)}"


def _check_libclang_available() -> Tuple[bool, Optional[str]]:
    """
    Check if libclang is available for use.
    
    Returns:
        Tuple of (available, reason_if_unavailable)
    """
    try:
        import clang.cindex
        # Try to create a Config object and access its library_file attribute.
        # This will fail if the libclang shared library is not found or cannot be loaded.
        config = clang.cindex.Config()
        if config.library_file:
            return True, None
        else:
            return False, "libclang library file not found. Check installation and environment variables (e.g., LD_LIBRARY_PATH)."
    except ImportError:
        return False, "libclang Python package not installed (pip install libclang)"
    except Exception as e:
        return False, f"libclang library load failed: {str(e)}"


def get_parser_capability(language: str) -> ParserCapability:
    """
    Get parser capability for a language with caching.
    
    Args:
        language: Language name (e.g., "C", "C++", "Rust", "ASM", "Perl")
    
    Returns:
        ParserCapability describing what can be extracted
    """
    # Check cache first
    if language in _parser_availability_cache:
        return _parser_availability_cache[language]
    
    capability = ParserCapability()
    
    # Check language-specific parser availability
    if language in ["C", "C++"]:
        # Prefer libclang for C/C++, fallback to tree-sitter, then regex
        libclang_available, libclang_reason = _check_libclang_available()
        if libclang_available:
            capability = ParserCapability(
                can_extract_symbols=True,
                can_extract_dependencies=True,
                can_extract_asm_labels=False,
                parser_type=ParserType.LIBCLANG,
                available=True
            )
        else:
            ts_available, ts_reason = _check_tree_sitter_available()
            if ts_available:
                capability = ParserCapability(
                    can_extract_symbols=True,
                    can_extract_dependencies=True,
                    can_extract_asm_labels=False,
                    parser_type=ParserType.TREE_SITTER,
                    available=True
                )
            else:
                # Fallback to regex (existing implementation)
                capability = ParserCapability(
                    can_extract_symbols=False,
                    can_extract_dependencies=True,  # Regex can extract includes
                    can_extract_asm_labels=False,
                    parser_type=ParserType.REGEX_FALLBACK,
                    available=True
                )
    
    elif language == "Rust":
        ts_available, ts_reason = _check_tree_sitter_available()
        if ts_available:
            capability = ParserCapability(
                can_extract_symbols=True,
                can_extract_dependencies=True,
                can_extract_asm_labels=False,
                parser_type=ParserType.TREE_SITTER,
                available=True
            )
        else:
            # Fallback to regex (existing implementation)
            capability = ParserCapability(
                can_extract_symbols=False,
                can_extract_dependencies=True,  # Regex can extract use/mod
                can_extract_asm_labels=False,
                parser_type=ParserType.REGEX_FALLBACK,
                available=True
            )
    
    elif language == "ASM":
        # Assembly always uses regex-based parsing for labels
        capability = ParserCapability(
            can_extract_symbols=True,  # Can extract labels
            can_extract_dependencies=False,  # Assembly doesn't have imports
            can_extract_asm_labels=True,
            parser_type=ParserType.REGEX_FALLBACK,
            available=True
        )
    
    elif language == "Perl":
        ts_available, ts_reason = _check_tree_sitter_available()
        if ts_available:
            capability = ParserCapability(
                can_extract_symbols=True,
                can_extract_dependencies=True,
                can_extract_asm_labels=False,
                parser_type=ParserType.TREE_SITTER,
                available=True
            )
        else:
            # Fallback to regex
            capability = ParserCapability(
                can_extract_symbols=False,
                can_extract_dependencies=True,  # Regex can extract use/require
                can_extract_asm_labels=False,
                parser_type=ParserType.REGEX_FALLBACK,
                available=True
            )
    
    else:
        # Unknown language - no parser available
        capability = ParserCapability(
            parser_type=ParserType.NONE,
            available=False,
            unavailable_reason=f"No parser configured for language: {language}"
        )
    
    # Cache the result
    _parser_availability_cache[language] = capability
    return capability


def parse_asm_symbols(content: str, file_path: Path) -> ParsedSymbols:
    """
    Parse assembly source to extract symbols (.globl directives, labels).
    
    Supports multiple assembly syntaxes:
    - GNU assembler (gas): .globl, .global, .type
    - NASM: global, extern
    - MASM: PUBLIC, EXTERN
    
    Args:
        content: Assembly source code
        file_path: Path to the file (for context in warnings)
    
    Returns:
        ParsedSymbols with extracted assembly labels and functions
    """
    result = ParsedSymbols(parser_used=ParserType.REGEX_FALLBACK)
    
    # Regex patterns
    globl_pattern = re.compile(r'^\s*\.glob(?:al|l)\s+([A-Za-z_][A-Za-z0-9_]*)', re.MULTILINE)
    type_pattern = re.compile(r'^\s*\.type\s+([A-Za-z_][A-Za-z0-9_]*)\s*,\s*[@%](function|object)', re.MULTILINE)
    nasm_global_pattern = re.compile(r'^\s*global\s+([A-Za-z_][A-Za-z0-9_]*)', re.MULTILINE | re.IGNORECASE)
    masm_public_pattern = re.compile(r'^\s*PUBLIC\s+([A-Za-z_][A-Za-z0-9_]*)', re.MULTILINE | re.IGNORECASE)
    label_pattern = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*):(?:\s|$)', re.MULTILINE)
    
    # Pass 1: Extract type annotations
    type_annotations: Dict[str, str] = {m.group(1): m.group(2) for m in type_pattern.finditer(content)}
    
    # Pass 2: Extract all global/public symbols from all syntaxes
    global_symbols: Dict[str, str] = {}
    for match in globl_pattern.finditer(content):
        global_symbols.setdefault(match.group(1), ".globl")
    for match in nasm_global_pattern.finditer(content):
        global_symbols.setdefault(match.group(1), "global")
    for match in masm_public_pattern.finditer(content):
        global_symbols.setdefault(match.group(1), "PUBLIC")

    # Pass 3: Categorize global symbols and add to results
    for symbol, directive in global_symbols.items():
        result.asm_labels.append(f"{directive} {symbol}")
        if symbol in type_annotations:
            if type_annotations[symbol] == "function":
                result.functions.append(symbol)
            else:
                result.variables.append(symbol)

    # Pass 4: Extract standalone labels that are not already global
    seen_labels = set(global_symbols.keys())
    for match in label_pattern.finditer(content):
        label = match.group(1)
        if label not in seen_labels:
            seen_labels.add(label)
            if label in type_annotations:
                if type_annotations[label] == "function":
                    result.functions.append(label)
                else:
                    result.variables.append(label)
            else:
                result.asm_labels.append(f"label {label}")
    
    return result


def parse_perl_symbols(content: str, file_path: Path) -> ParsedSymbols:
    """
    Parse Perl source to extract subroutines and package declarations.
    
    Uses regex-based parsing as tree-sitter fallback.
    
    Args:
        content: Perl source code
        file_path: Path to the file (for context in warnings)
    
    Returns:
        ParsedSymbols with extracted Perl subroutines and packages
    """
    result = ParsedSymbols(parser_used=ParserType.REGEX_FALLBACK)
    
    # Pattern for sub declarations
    # Matches: sub name { ... } or sub name;
    sub_pattern = re.compile(r'^\s*sub\s+([A-Za-z_][A-Za-z0-9_]*)', re.MULTILINE)
    
    # Pattern for package declarations
    # Matches: package Package::Name;
    package_pattern = re.compile(r'^\s*package\s+([\w:]+)\s*;', re.MULTILINE)
    
    # Extract subroutines
    for match in sub_pattern.finditer(content):
        sub_name = match.group(1)
        result.functions.append(f"sub {sub_name}")
    
    # Extract packages (treat as classes)
    for match in package_pattern.finditer(content):
        package_name = match.group(1)
        result.classes.append(f"package {package_name}")
    
    return result


def parse_perl_dependencies(content: str, file_path: Path) -> List[str]:
    """
    Parse Perl use/require statements to extract dependencies.
    
    Args:
        content: Perl source code
        file_path: Path to the file (for context)
    
    Returns:
        List of module dependencies
    """
    dependencies = []
    
    # Import pragma list from stdlib_classification to avoid duplication
    from repo_analyzer.stdlib_classification import PERL_PRAGMAS
    
    # Pattern for use statements
    # Matches: use Module::Name; or use Module::Name qw(...);
    use_pattern = re.compile(r'^\s*use\s+([\w:]+)', re.MULTILINE)
    
    # Pattern for require statements
    # Matches: require Module::Name; or require "path/to/module.pm";
    require_pattern = re.compile(r'^\s*require\s+(?:([\w:]+)|["\']([^"\']+)["\'])', re.MULTILINE)
    
    # Extract use statements
    for match in use_pattern.finditer(content):
        module = match.group(1)
        # Skip pragmas and version declarations
        if module not in PERL_PRAGMAS and not module.startswith('v'):
            dependencies.append(module)
    
    # Extract require statements
    for match in require_pattern.finditer(content):
        # require can use either Module::Name or "path/to/file"
        module = match.group(1) if match.group(1) else match.group(2)
        if module:
            dependencies.append(module)
    
    return dependencies


def extract_symbols(
    language: str,
    content: str,
    file_path: Path
) -> ParsedSymbols:
    """
    Extract symbols (functions, classes, etc.) from source code.
    
    This is the main entry point for symbol extraction. It checks parser
    availability and delegates to appropriate parser or fallback.
    
    Args:
        language: Programming language name
        content: Source code content
        file_path: Path to the source file
    
    Returns:
        ParsedSymbols with extracted information
    """
    capability = get_parser_capability(language)
    
    if not capability.available:
        result = ParsedSymbols()
        result.warnings.append(capability.unavailable_reason or "No parser available")
        return result
    
    # Dispatch to language-specific parser
    if language == "ASM":
        return parse_asm_symbols(content, file_path)
    elif language == "Perl":
        # Perl can extract symbols even with regex fallback
        return parse_perl_symbols(content, file_path)
    elif language in ["C", "C++", "Rust"]:
        # For now, return empty result with note
        # Future: Implement tree-sitter/libclang integration
        result = ParsedSymbols()
        if capability.can_extract_symbols:
            result.warnings.append(f"{capability.parser_type.value} integration pending - using heuristics")
        else:
            result.warnings.append(f"Symbol extraction not yet implemented for {language}")
        return result
    else:
        result = ParsedSymbols()
        result.warnings.append(f"No symbol extractor implemented for {language}")
        return result


def get_parser_diagnostics() -> Dict[str, Any]:
    """
    Get diagnostic information about parser availability.
    
    Returns:
        Dictionary with parser status for each language
    """
    diagnostics = {
        "tree_sitter": {},
        "libclang": {},
        "languages": {}
    }
    
    # Check tree-sitter
    ts_available, ts_reason = _check_tree_sitter_available()
    diagnostics["tree_sitter"]["available"] = ts_available
    if not ts_available:
        diagnostics["tree_sitter"]["reason"] = ts_reason
    
    # Check libclang
    lc_available, lc_reason = _check_libclang_available()
    diagnostics["libclang"]["available"] = lc_available
    if not lc_available:
        diagnostics["libclang"]["reason"] = lc_reason
    
    # Get capability for each target language
    for lang in ["C", "C++", "Rust", "ASM", "Perl"]:
        cap = get_parser_capability(lang)
        diagnostics["languages"][lang] = {
            "parser_type": cap.parser_type.value,
            "available": cap.available,
            "can_extract_symbols": cap.can_extract_symbols,
            "can_extract_dependencies": cap.can_extract_dependencies,
            "can_extract_asm_labels": cap.can_extract_asm_labels,
        }
        if cap.unavailable_reason:
            diagnostics["languages"][lang]["unavailable_reason"] = cap.unavailable_reason
    
    return diagnostics
