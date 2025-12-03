# Copyright (c) 2025 John Brosnihan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""Tests for parser adapter module and low-level language support."""

import pytest
from pathlib import Path
from repo_analyzer.parser_adapters import (
    ParserType,
    ParserCapability,
    ParsedSymbols,
    get_parser_capability,
    parse_asm_symbols,
    parse_perl_symbols,
    parse_perl_dependencies,
    extract_symbols,
    get_parser_diagnostics,
)


class TestParserCapability:
    """Tests for parser capability detection."""
    
    def test_asm_parser_capability(self):
        """ASM should always have regex parser available."""
        cap = get_parser_capability("ASM")
        assert cap.available is True
        assert cap.can_extract_symbols is True
        assert cap.can_extract_asm_labels is True
        assert cap.can_extract_dependencies is False
        assert cap.parser_type == ParserType.REGEX_FALLBACK
    
    def test_perl_parser_capability(self):
        """Perl should have at least regex fallback available."""
        cap = get_parser_capability("Perl")
        assert cap.available is True
        assert cap.can_extract_dependencies is True
        # Symbol extraction may or may not be available depending on tree-sitter
        assert cap.parser_type in [ParserType.TREE_SITTER, ParserType.REGEX_FALLBACK]
    
    def test_c_parser_capability(self):
        """C should have at least regex fallback available."""
        cap = get_parser_capability("C")
        assert cap.available is True
        assert cap.can_extract_dependencies is True
        # Parser type depends on what's installed
        assert cap.parser_type in [ParserType.LIBCLANG, ParserType.TREE_SITTER, ParserType.REGEX_FALLBACK]
    
    def test_unknown_language_capability(self):
        """Unknown languages should return unavailable capability."""
        cap = get_parser_capability("UnknownLang")
        assert cap.available is False
        assert cap.unavailable_reason is not None


class TestParseAsmSymbols:
    """Tests for assembly symbol extraction."""
    
    def test_gnu_globl_directive(self):
        """Parse GNU assembler .globl directive."""
        content = """
        .globl main
        main:
            mov $1, %eax
            ret
        """
        result = parse_asm_symbols(content, Path("test.s"))
        assert ".globl main" in result.asm_labels
        assert result.parser_used == ParserType.REGEX_FALLBACK
    
    def test_gnu_global_directive(self):
        """Parse GNU assembler .global directive (alias for .globl)."""
        content = """
        .global my_function
        my_function:
            nop
            ret
        """
        result = parse_asm_symbols(content, Path("test.s"))
        assert ".globl my_function" in result.asm_labels
    
    def test_type_function_directive(self):
        """Parse .type @function directive to identify functions."""
        content = """
        .globl compute
        .type compute, @function
        compute:
            add $1, %eax
            ret
        """
        result = parse_asm_symbols(content, Path("test.s"))
        assert "compute" in result.functions
        assert ".globl compute" in result.asm_labels
    
    def test_type_object_directive(self):
        """Parse .type @object directive to identify data."""
        content = """
        .globl my_data
        .type my_data, @object
        my_data:
            .quad 42
        """
        result = parse_asm_symbols(content, Path("test.s"))
        assert "my_data" in result.variables
        assert ".globl my_data" in result.asm_labels
    
    def test_nasm_global_directive(self):
        """Parse NASM global directive."""
        content = """
        global _start
        _start:
            mov eax, 1
            int 0x80
        """
        result = parse_asm_symbols(content, Path("test.asm"))
        assert "global _start" in result.asm_labels
    
    def test_masm_public_directive(self):
        """Parse MASM PUBLIC directive."""
        content = """
        PUBLIC MyProc
        MyProc PROC
            ret
        MyProc ENDP
        """
        result = parse_asm_symbols(content, Path("test.asm"))
        assert "PUBLIC MyProc" in result.asm_labels
    
    def test_mixed_assembly_syntax(self):
        """Parse assembly with multiple directive types."""
        content = """
        .globl func1
        .type func1, @function
        func1:
            nop
        
        global func2
        func2:
            ret
        
        PUBLIC func3
        func3:
            ret
        """
        result = parse_asm_symbols(content, Path("test.s"))
        assert "func1" in result.functions
        assert "global func2" in result.asm_labels
        assert "PUBLIC func3" in result.asm_labels
        assert len(result.asm_labels) >= 3
    
    def test_label_without_directive(self):
        """Parse labels without directives as generic labels."""
        content = """
        local_label:
            mov $0, %eax
            ret
        """
        result = parse_asm_symbols(content, Path("test.s"))
        assert "label local_label" in result.asm_labels
    
    def test_no_duplicate_symbols(self):
        """Ensure symbols are not duplicated in output."""
        content = """
        .globl test_func
        .type test_func, @function
        test_func:
            ret
        """
        result = parse_asm_symbols(content, Path("test.s"))
        # Should have .globl directive and function entry, but not duplicate
        assert ".globl test_func" in result.asm_labels
        assert "test_func" in result.functions
        # Count occurrences of test_func across all lists
        count = sum([
            result.asm_labels.count(".globl test_func"),
            result.functions.count("test_func"),
        ])
        assert count == 2  # Exactly one in each list


class TestParsePerlSymbols:
    """Tests for Perl symbol extraction."""
    
    def test_simple_subroutine(self):
        """Parse simple subroutine declaration."""
        content = """
        sub hello {
            print "Hello, World!\\n";
        }
        """
        result = parse_perl_symbols(content, Path("test.pl"))
        assert "sub hello" in result.functions
    
    def test_multiple_subroutines(self):
        """Parse multiple subroutine declarations."""
        content = """
        sub first {
            return 1;
        }
        
        sub second {
            return 2;
        }
        
        sub third {
            return 3;
        }
        """
        result = parse_perl_symbols(content, Path("test.pl"))
        assert "sub first" in result.functions
        assert "sub second" in result.functions
        assert "sub third" in result.functions
    
    def test_package_declaration(self):
        """Parse package declaration."""
        content = """
        package MyModule::Utils;
        
        sub helper {
            return 42;
        }
        """
        result = parse_perl_symbols(content, Path("Utils.pm"))
        assert "package MyModule::Utils" in result.classes
        assert "sub helper" in result.functions
    
    def test_multiple_packages(self):
        """Parse multiple package declarations in one file."""
        content = """
        package First::Package;
        sub first_sub { }
        
        package Second::Package;
        sub second_sub { }
        """
        result = parse_perl_symbols(content, Path("test.pm"))
        assert "package First::Package" in result.classes
        assert "package Second::Package" in result.classes


class TestParsePerlDependencies:
    """Tests for Perl dependency extraction."""
    
    def test_use_statement(self):
        """Parse use statement."""
        content = """
        use File::Copy;
        use Data::Dumper;
        """
        deps = parse_perl_dependencies(content, Path("test.pl"))
        assert "File::Copy" in deps
        assert "Data::Dumper" in deps
    
    def test_require_statement(self):
        """Parse require statement."""
        content = """
        require MyModule;
        require "path/to/module.pm";
        """
        deps = parse_perl_dependencies(content, Path("test.pl"))
        assert "MyModule" in deps
        assert "path/to/module.pm" in deps
    
    def test_skip_pragmas(self):
        """Skip common pragmas from dependency list."""
        content = """
        use strict;
        use warnings;
        use File::Copy;
        use constant PI => 3.14159;
        """
        deps = parse_perl_dependencies(content, Path("test.pl"))
        assert "strict" not in deps
        assert "warnings" not in deps
        assert "constant" not in deps
        assert "File::Copy" in deps
    
    def test_use_with_import_list(self):
        """Parse use statement with import list."""
        content = """
        use File::Copy qw(copy move);
        use List::Util qw(first max);
        """
        deps = parse_perl_dependencies(content, Path("test.pl"))
        assert "File::Copy" in deps
        assert "List::Util" in deps


class TestExtractSymbols:
    """Tests for unified symbol extraction interface."""
    
    def test_asm_symbol_extraction(self):
        """Extract symbols from assembly code."""
        content = """
        .globl main
        .type main, @function
        main:
            ret
        """
        result = extract_symbols("ASM", content, Path("test.s"))
        assert "main" in result.functions
        assert ".globl main" in result.asm_labels
    
    def test_perl_symbol_extraction(self):
        """Extract symbols from Perl code."""
        content = """
        package Test;
        sub test_func {
            return 1;
        }
        """
        result = extract_symbols("Perl", content, Path("test.pl"))
        # Note: tree-sitter may not be available, so we test regex fallback
        assert result.parser_used in [ParserType.TREE_SITTER, ParserType.REGEX_FALLBACK]
    
    def test_unsupported_language(self):
        """Handle unsupported language gracefully."""
        result = extract_symbols("UnknownLang", "code", Path("test.txt"))
        assert not result.functions
        assert not result.classes
        assert len(result.warnings) > 0


class TestParserDiagnostics:
    """Tests for parser diagnostics reporting."""
    
    def test_diagnostics_structure(self):
        """Diagnostics should have expected structure."""
        diag = get_parser_diagnostics()
        assert "tree_sitter" in diag
        assert "libclang" in diag
        assert "languages" in diag
        assert "available" in diag["tree_sitter"]
        assert "available" in diag["libclang"]
    
    def test_language_diagnostics(self):
        """Language diagnostics should include all target languages."""
        diag = get_parser_diagnostics()
        langs = diag["languages"]
        assert "C" in langs
        assert "C++" in langs
        assert "Rust" in langs
        assert "ASM" in langs
        assert "Perl" in langs
        
        # All should have required fields
        for lang in ["C", "C++", "Rust", "ASM", "Perl"]:
            assert "parser_type" in langs[lang]
            assert "available" in langs[lang]
            assert "can_extract_symbols" in langs[lang]
            assert "can_extract_dependencies" in langs[lang]


class TestGracefulDegradation:
    """Tests for graceful degradation when parsers unavailable."""
    
    def test_asm_always_works(self):
        """ASM should always work (no external dependencies)."""
        cap = get_parser_capability("ASM")
        assert cap.available is True
        assert cap.unavailable_reason is None
    
    def test_fallback_for_missing_parser(self):
        """Languages should fall back to regex when structured parsers unavailable."""
        # Even if tree-sitter/libclang unavailable, languages should still have regex fallback
        for lang in ["C", "C++", "Rust", "Perl"]:
            cap = get_parser_capability(lang)
            # At minimum, regex fallback should be available
            assert cap.available is True


class TestEdgeCases:
    """Tests for edge cases in parser adapters."""
    
    def test_empty_content(self):
        """Handle empty file content."""
        result = parse_asm_symbols("", Path("empty.s"))
        assert result.functions == []
        assert result.asm_labels == []
        
        result = parse_perl_symbols("", Path("empty.pl"))
        assert result.functions == []
        assert result.classes == []
    
    def test_comment_only_content(self):
        """Handle content with only comments."""
        asm_content = """
        ; This is a comment
        # Another comment
        """
        result = parse_asm_symbols(asm_content, Path("comments.s"))
        assert result.functions == []
        assert result.asm_labels == []
    
    def test_malformed_directives(self):
        """Handle malformed directives gracefully."""
        content = """
        .globl  # Missing symbol name
        global  # Missing symbol name
        .type incomplete
        """
        result = parse_asm_symbols(content, Path("malformed.s"))
        # Should not crash, may extract nothing or partial results
        assert isinstance(result, ParsedSymbols)
