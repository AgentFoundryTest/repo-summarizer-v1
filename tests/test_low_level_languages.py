# Copyright (c) 2025 John Brosnihan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Tests for low-level language parsing (C, C++, Rust, ASM, Perl).
"""

import tempfile
from pathlib import Path

import pytest

from repo_analyzer.parser_adapters import (
    parse_c_cpp_symbols,
    parse_rust_symbols,
    parse_asm_symbols,
    parse_perl_symbols,
    extract_symbols,
    get_parser_capability,
)
from repo_analyzer.file_summary import (
    _create_structured_summary,
    generate_file_summaries,
)


class TestCParserAdapters:
    """Tests for C parser adapter."""
    
    def test_parse_c_functions(self):
        """Test parsing C function declarations."""
        content = """
int add(int a, int b) {
    return a + b;
}

void print_hello() {
    printf("Hello");
}

static inline int helper(void) {
    return 0;
}
"""
        result = parse_c_cpp_symbols(content, Path('test.c'), 'C')
        assert 'function add' in result.functions
        assert 'function print_hello' in result.functions
        assert 'function helper' in result.functions
    
    def test_parse_c_structs(self):
        """Test parsing C struct declarations."""
        content = """
struct Point {
    int x;
    int y;
};

struct Node {
    int value;
    struct Node* next;
};
"""
        result = parse_c_cpp_symbols(content, Path('test.c'), 'C')
        assert 'struct Point' in result.classes
        assert 'struct Node' in result.classes
    
    def test_parse_c_macros(self):
        """Test parsing C macro definitions."""
        content = """
#define MAX_SIZE 100
#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define BUFFER_SIZE 1024
"""
        result = parse_c_cpp_symbols(content, Path('test.c'), 'C')
        assert '#define MAX_SIZE' in result.variables
        assert '#define MIN' in result.variables
        assert '#define BUFFER_SIZE' in result.variables
    
    def test_parse_c_global_variables(self):
        """Test parsing C global variable declarations."""
        content = """
extern int global_counter;
static int internal_counter = 0;
extern const char* message;
"""
        result = parse_c_cpp_symbols(content, Path('test.c'), 'C')
        assert 'global global_counter' in result.variables
        assert 'global internal_counter' in result.variables
        assert 'global message' in result.variables
    
    def test_parse_c_with_comments(self):
        """Test that comments are filtered out."""
        content = """
// This is a comment with function fake_func()
/* Another comment
   with void another_fake() */
int real_function() {
    return 1;
}
"""
        result = parse_c_cpp_symbols(content, Path('test.c'), 'C')
        assert 'function real_function' in result.functions
        # Should not parse commented-out functions
        assert 'function fake_func' not in result.functions
        assert 'function another_fake' not in result.functions


class TestCppParserAdapters:
    """Tests for C++ parser adapter."""
    
    def test_parse_cpp_classes(self):
        """Test parsing C++ class declarations."""
        content = """
class MyClass {
public:
    void method();
};

class TemplateClass {
    int value;
};
"""
        result = parse_c_cpp_symbols(content, Path('test.cpp'), 'C++')
        assert 'class MyClass' in result.classes
        assert 'class TemplateClass' in result.classes
    
    def test_parse_cpp_functions(self):
        """Test parsing C++ function declarations."""
        content = """
int add(int a, int b) {
    return a + b;
}

void MyClass::method() {
    // implementation
}
"""
        result = parse_c_cpp_symbols(content, Path('test.cpp'), 'C++')
        assert 'function add' in result.functions
        # Note: method parsing might not capture class::method format perfectly
        # but should still capture basic functions


class TestRustParserAdapters:
    """Tests for Rust parser adapter."""
    
    def test_parse_rust_functions(self):
        """Test parsing Rust function declarations."""
        content = """
pub fn main() {
    println!("Hello");
}

fn helper(x: i32) -> i32 {
    x * 2
}

pub async fn async_func() {
    // async code
}

pub unsafe fn unsafe_func() {
    // unsafe code
}
"""
        result = parse_rust_symbols(content, Path('test.rs'))
        assert 'fn main' in result.functions
        assert 'fn helper' in result.functions
        assert 'fn async_func' in result.functions
        assert 'fn unsafe_func' in result.functions
    
    def test_parse_rust_structs(self):
        """Test parsing Rust struct declarations."""
        content = """
pub struct User {
    name: String,
    age: u32,
}

struct Point {
    x: f64,
    y: f64,
}
"""
        result = parse_rust_symbols(content, Path('test.rs'))
        assert 'struct User' in result.classes
        assert 'struct Point' in result.classes
    
    def test_parse_rust_enums(self):
        """Test parsing Rust enum declarations."""
        content = """
pub enum Status {
    Active,
    Inactive,
}

enum Color {
    Red,
    Green,
    Blue,
}
"""
        result = parse_rust_symbols(content, Path('test.rs'))
        assert 'enum Status' in result.classes
        assert 'enum Color' in result.classes
    
    def test_parse_rust_traits(self):
        """Test parsing Rust trait declarations."""
        content = """
pub trait Display {
    fn display(&self);
}

trait Compute {
    fn compute(&self) -> i32;
}
"""
        result = parse_rust_symbols(content, Path('test.rs'))
        assert 'trait Display' in result.classes
        assert 'trait Compute' in result.classes
    
    def test_parse_rust_impls(self):
        """Test parsing Rust impl blocks."""
        content = """
impl Display for User {
    fn display(&self) {
        println!("User");
    }
}

impl User {
    fn new() -> Self {
        User { name: String::new(), age: 0 }
    }
}
"""
        result = parse_rust_symbols(content, Path('test.rs'))
        # Should capture impl blocks
        assert any('impl Display' in c or 'impl User' in c for c in result.classes)
    
    def test_parse_rust_constants(self):
        """Test parsing Rust const and static declarations."""
        content = """
pub const MAX_USERS: usize = 100;
const MIN_VALUE: i32 = 0;
static mut COUNTER: i32 = 0;
"""
        result = parse_rust_symbols(content, Path('test.rs'))
        assert 'const MAX_USERS' in result.variables
        assert 'const MIN_VALUE' in result.variables


class TestAsmParserAdapters:
    """Tests for assembly parser adapter."""
    
    def test_parse_asm_globl_gas(self):
        """Test parsing GNU assembler .globl directives."""
        content = """
.globl main
.type main, @function
main:
    push %rbp
    ret

.globl helper
helper:
    ret
"""
        result = parse_asm_symbols(content, Path('test.s'))
        assert '.globl main' in result.asm_labels
        assert '.globl helper' in result.asm_labels
        assert 'main' in result.functions
    
    def test_parse_asm_global_gas(self):
        """Test parsing GNU assembler .global directives."""
        content = """
.global start
.type start, @function
start:
    ret
"""
        result = parse_asm_symbols(content, Path('test.s'))
        assert '.globl start' in result.asm_labels
        assert 'start' in result.functions
    
    def test_parse_asm_nasm(self):
        """Test parsing NASM global directives."""
        content = """
global main
main:
    ret

global helper
helper:
    ret
"""
        result = parse_asm_symbols(content, Path('test.asm'))
        assert 'global main' in result.asm_labels
        assert 'global helper' in result.asm_labels
    
    def test_parse_asm_masm(self):
        """Test parsing MASM PUBLIC directives."""
        content = """
PUBLIC main
main PROC
    ret
main ENDP

PUBLIC helper
helper PROC
    ret
helper ENDP
"""
        result = parse_asm_symbols(content, Path('test.asm'))
        assert 'PUBLIC main' in result.asm_labels
        assert 'PUBLIC helper' in result.asm_labels
    
    def test_parse_asm_data_objects(self):
        """Test parsing assembly data objects."""
        content = """
.data
.globl data_var
.type data_var, @object
data_var:
    .long 42
"""
        result = parse_asm_symbols(content, Path('test.s'))
        assert '.globl data_var' in result.asm_labels
        assert 'data_var' in result.variables
    
    def test_parse_asm_local_labels(self):
        """Test parsing local labels."""
        content = """
.globl main
main:
    jmp local_label
    
local_label:
    nop
    ret
"""
        result = parse_asm_symbols(content, Path('test.s'))
        assert '.globl main' in result.asm_labels
        assert 'label local_label' in result.asm_labels


class TestPerlParserAdapters:
    """Tests for Perl parser adapter."""
    
    def test_parse_perl_subs(self):
        """Test parsing Perl subroutine declarations."""
        content = """
sub new {
    my $class = shift;
    return bless {}, $class;
}

sub process {
    my ($self, $data) = @_;
    return $data * 2;
}

sub helper_function {
    print "Helper";
}
"""
        result = parse_perl_symbols(content, Path('MyModule.pm'))
        assert 'sub new' in result.functions
        assert 'sub process' in result.functions
        assert 'sub helper_function' in result.functions
    
    def test_parse_perl_packages(self):
        """Test parsing Perl package declarations."""
        content = """
package MyModule;

sub func1 {
    return 1;
}

package MyModule::Helper;

sub func2 {
    return 2;
}
"""
        result = parse_perl_symbols(content, Path('MyModule.pm'))
        assert 'package MyModule' in result.classes
        assert 'package MyModule::Helper' in result.classes


class TestExtractSymbols:
    """Tests for the main extract_symbols function."""
    
    def test_extract_symbols_c(self):
        """Test symbol extraction for C files."""
        content = "int main() { return 0; }"
        result = extract_symbols('C', content, Path('test.c'))
        assert len(result.functions) > 0 or len(result.classes) > 0 or len(result.variables) > 0
    
    def test_extract_symbols_cpp(self):
        """Test symbol extraction for C++ files."""
        content = "class MyClass {};"
        result = extract_symbols('C++', content, Path('test.cpp'))
        assert len(result.classes) > 0
    
    def test_extract_symbols_rust(self):
        """Test symbol extraction for Rust files."""
        content = "pub fn main() {}"
        result = extract_symbols('Rust', content, Path('test.rs'))
        assert len(result.functions) > 0
    
    def test_extract_symbols_asm(self):
        """Test symbol extraction for assembly files."""
        content = ".globl main\nmain:\n    ret"
        result = extract_symbols('ASM', content, Path('test.s'))
        assert len(result.asm_labels) > 0
    
    def test_extract_symbols_perl(self):
        """Test symbol extraction for Perl files."""
        content = "sub func { return 1; }"
        result = extract_symbols('Perl', content, Path('test.pl'))
        assert len(result.functions) > 0


class TestFileSummaryIntegration:
    """Tests for integration with file_summary module."""
    
    def test_c_file_detailed_summary(self, tmp_path):
        """Test detailed summary for C files."""
        source = tmp_path / 'source'
        source.mkdir()
        
        c_file = source / 'utils.c'
        c_file.write_text("""
int add(int a, int b) {
    return a + b;
}

void print_hello() {
    printf("Hello");
}

#define MAX_SIZE 100
""")
        
        summary = _create_structured_summary(c_file, source, detail_level='detailed', include_legacy=True)
        
        assert summary['language'] == 'C'
        assert 'structure' in summary
        assert len(summary['structure']['declarations']) > 0
        # Should have functions and macros
        decls = summary['structure']['declarations']
        assert any('add' in d for d in decls)
        assert any('print_hello' in d for d in decls)
        assert any('MAX_SIZE' in d for d in decls)
    
    def test_cpp_file_detailed_summary(self, tmp_path):
        """Test detailed summary for C++ files."""
        source = tmp_path / 'source'
        source.mkdir()
        
        cpp_file = source / 'MyClass.cpp'
        cpp_file.write_text("""
class MyClass {
public:
    void method();
};

int helper() {
    return 1;
}
""")
        
        summary = _create_structured_summary(cpp_file, source, detail_level='detailed', include_legacy=True)
        
        assert summary['language'] == 'C++'
        assert len(summary['structure']['declarations']) > 0
        decls = summary['structure']['declarations']
        assert any('MyClass' in d for d in decls)
        assert any('helper' in d for d in decls)
    
    def test_rust_file_detailed_summary(self, tmp_path):
        """Test detailed summary for Rust files."""
        source = tmp_path / 'source'
        source.mkdir()
        
        rust_file = source / 'lib.rs'
        rust_file.write_text("""
pub fn main() {
    println!("Hello");
}

pub struct User {
    name: String,
}

pub trait Display {
    fn display(&self);
}
""")
        
        summary = _create_structured_summary(rust_file, source, detail_level='detailed', include_legacy=True)
        
        assert summary['language'] == 'Rust'
        assert len(summary['structure']['declarations']) > 0
        decls = summary['structure']['declarations']
        assert any('main' in d for d in decls)
        assert any('User' in d for d in decls)
        assert any('Display' in d for d in decls)
    
    def test_asm_file_detailed_summary(self, tmp_path):
        """Test detailed summary for assembly files."""
        source = tmp_path / 'source'
        source.mkdir()
        
        asm_file = source / 'func.s'
        asm_file.write_text("""
.globl main
.type main, @function
main:
    push %rbp
    ret

.globl helper
helper:
    ret
""")
        
        summary = _create_structured_summary(asm_file, source, detail_level='detailed', include_legacy=True)
        
        assert summary['language'] == 'ASM'
        assert len(summary['structure']['declarations']) > 0
        decls = summary['structure']['declarations']
        assert any('main' in d for d in decls)
        assert any('helper' in d for d in decls)
    
    def test_perl_file_detailed_summary(self, tmp_path):
        """Test detailed summary for Perl files."""
        source = tmp_path / 'source'
        source.mkdir()
        
        perl_file = source / 'MyModule.pm'
        perl_file.write_text("""
package MyModule;

sub new {
    my $class = shift;
    return bless {}, $class;
}

sub process {
    return 1;
}
""")
        
        summary = _create_structured_summary(perl_file, source, detail_level='detailed', include_legacy=True)
        
        assert summary['language'] == 'Perl'
        assert len(summary['structure']['declarations']) > 0
        decls = summary['structure']['declarations']
        assert any('new' in d for d in decls)
        assert any('process' in d for d in decls)
        assert any('MyModule' in d for d in decls)
    
    def test_mixed_low_level_languages(self, tmp_path):
        """Test file summaries with mixed low-level languages."""
        source = tmp_path / 'source'
        source.mkdir()
        
        # Create files in different low-level languages
        (source / 'main.c').write_text('int main() { return 0; }')
        (source / 'utils.cpp').write_text('class Utils {};')
        (source / 'lib.rs').write_text('pub fn func() {}')
        (source / 'func.s').write_text('.globl main\nmain:\n    ret')
        (source / 'Module.pm').write_text('package Module;\nsub func {}')
        
        output = tmp_path / 'output'
        output.mkdir()
        
        generate_file_summaries(
            source,
            output,
            include_patterns=['*.c', '*.cpp', '*.rs', '*.s', '*.pm'],
            detail_level='detailed'
        )
        
        import json
        json_file = output / 'file-summaries.json'
        assert json_file.exists()
        
        data = json.loads(json_file.read_text())
        assert data['total_files'] == 5
        
        # Verify all languages are represented
        languages = {entry['language'] for entry in data['files']}
        assert languages == {'C', 'C++', 'Rust', 'ASM', 'Perl'}
        
        # Verify all have declarations at detailed level
        for entry in data['files']:
            assert 'structure' in entry
            assert 'declarations' in entry['structure']
    
    def test_c_header_with_detailed_summary(self, tmp_path):
        """Test that C header files get appropriate summaries."""
        source = tmp_path / 'source'
        source.mkdir()
        
        header = source / 'utils.h'
        header.write_text("""
#ifndef UTILS_H
#define UTILS_H

int add(int a, int b);
void print_hello(void);

#define MAX_SIZE 100

#endif
""")
        
        summary = _create_structured_summary(header, source, detail_level='detailed', include_legacy=True)
        
        assert summary['language'] in ['C', 'C++', 'C/C++']
        assert 'header' in summary['summary'].lower()
        # Should still extract declarations from header
        decls = summary['structure']['declarations']
        assert len(decls) > 0
    
    def test_large_c_file_skips_parsing(self, tmp_path):
        """Test that large C files skip parsing."""
        source = tmp_path / 'source'
        source.mkdir()
        
        large_file = source / 'large.c'
        # Create a large file
        large_content = "// Large file\n" * 100000
        large_file.write_text(large_content)
        
        summary = _create_structured_summary(
            large_file, source, detail_level='detailed', include_legacy=True, max_file_size_kb=1
        )
        
        # Should have structure field with warning about size
        assert 'structure' in summary
        assert 'warning' in summary['structure']
        assert 'exceeds' in summary['structure']['warning']


class TestParserCapability:
    """Tests for parser capability detection."""
    
    def test_c_parser_capability(self):
        """Test that C has parser capability."""
        cap = get_parser_capability('C')
        assert cap.available
        assert cap.can_extract_symbols
    
    def test_cpp_parser_capability(self):
        """Test that C++ has parser capability."""
        cap = get_parser_capability('C++')
        assert cap.available
        assert cap.can_extract_symbols
    
    def test_rust_parser_capability(self):
        """Test that Rust has parser capability."""
        cap = get_parser_capability('Rust')
        assert cap.available
        assert cap.can_extract_symbols
    
    def test_asm_parser_capability(self):
        """Test that ASM has parser capability."""
        cap = get_parser_capability('ASM')
        assert cap.available
        assert cap.can_extract_symbols
        assert cap.can_extract_asm_labels
    
    def test_perl_parser_capability(self):
        """Test that Perl has parser capability."""
        cap = get_parser_capability('Perl')
        assert cap.available


class TestStringLiteralProtection:
    """Tests that string literals with comment-like sequences are preserved."""
    
    def test_c_string_with_comment_sequences(self):
        """Test that C strings containing comment sequences are preserved."""
        content = """
int func() {
    char* str1 = "/* not a comment */";
    char* str2 = "// also not a comment";
    // This is a real comment
    return 1;
}

void another() {
    char c = '//';  // Real comment here
}
"""
        result = parse_c_cpp_symbols(content, Path('test.c'), 'C')
        # Both functions should be detected
        assert 'function func' in result.functions
        assert 'function another' in result.functions
        # Verify we got exactly 2 functions (no false positives from strings)
        assert len(result.functions) == 2
    
    def test_rust_string_with_comment_sequences(self):
        """Test that Rust strings containing comment sequences are preserved."""
        content = """
fn func() {
    let s = "// not a comment";
    let s2 = "/* also not */";
    // This is a real comment
}

fn another() {
    let raw = r#"/* raw string */"#;
    let byte = b"// byte string";
}
"""
        result = parse_rust_symbols(content, Path('test.rs'))
        # Both functions should be detected
        assert 'fn func' in result.functions
        assert 'fn another' in result.functions
        # Verify we got exactly 2 functions
        assert len(result.functions) == 2
    
    def test_rust_impl_with_generics(self):
        """Test that Rust impl blocks with generics are detected."""
        content = """
impl<T> MyType<T> {
    fn method(&self) {}
}

impl<T: Display> MyTrait for MyType<T> {
    fn trait_method(&self) {}
}

impl lowercase_type {
    fn new() {}
}
"""
        result = parse_rust_symbols(content, Path('test.rs'))
        # All impl blocks should be detected
        assert any('MyType<T>' in c for c in result.classes)
        assert any('MyType<T>' in c or 'MyTrait' in c for c in result.classes)
        # lowercase_type should also be detected
        assert any('lowercase_type' in c for c in result.classes)
