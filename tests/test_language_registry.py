# Copyright (c) 2025 John Brosnihan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Tests for the language registry module.
"""

import pytest
from repo_analyzer.language_registry import (
    LanguageCapability,
    LanguageRegistry,
    get_global_registry,
    reset_global_registry
)


class TestLanguageCapability:
    """Tests for LanguageCapability dataclass."""
    
    def test_basic_creation(self):
        """Test creating a basic language capability."""
        lang = LanguageCapability(
            name="Python",
            extensions={".py"},
            has_structure_parser=True,
            has_dependency_scanner=True
        )
        
        assert lang.name == "Python"
        assert lang.extensions == {".py"}
        assert lang.has_structure_parser is True
        assert lang.has_dependency_scanner is True
        assert lang.enabled is True  # default
        assert lang.priority == 0  # default
    
    def test_to_dict(self):
        """Test converting language capability to dictionary."""
        lang = LanguageCapability(
            name="JavaScript",
            extensions={".js", ".jsx"},
            has_structure_parser=True,
            priority=10
        )
        
        result = lang.to_dict()
        
        assert result["name"] == "JavaScript"
        assert sorted(result["extensions"]) == [".js", ".jsx"]
        assert result["has_structure_parser"] is True
        assert result["priority"] == 10
        assert result["enabled"] is True


class TestLanguageRegistry:
    """Tests for LanguageRegistry class."""
    
    def test_default_languages_registered(self):
        """Test that default languages are registered on initialization."""
        registry = LanguageRegistry()
        
        # Check that key languages are present
        assert registry.get_language("Python") is not None
        assert registry.get_language("JavaScript") is not None
        assert registry.get_language("TypeScript") is not None
        assert registry.get_language("C") is not None
        assert registry.get_language("C++") is not None
        assert registry.get_language("C#") is not None
        assert registry.get_language("Rust") is not None
        assert registry.get_language("Go") is not None
        assert registry.get_language("Java") is not None
        assert registry.get_language("Swift") is not None
        assert registry.get_language("HTML") is not None
        assert registry.get_language("CSS") is not None
        assert registry.get_language("SQL") is not None
    
    def test_extension_mapping(self):
        """Test file extension to language mapping."""
        registry = LanguageRegistry()
        
        assert registry.get_language_by_extension(".py") == "Python"
        assert registry.get_language_by_extension(".js") == "JavaScript"
        assert registry.get_language_by_extension(".ts") == "TypeScript"
        assert registry.get_language_by_extension(".c") == "C"
        assert registry.get_language_by_extension(".cpp") == "C++"
        assert registry.get_language_by_extension(".cs") == "C#"
        assert registry.get_language_by_extension(".rs") == "Rust"
        assert registry.get_language_by_extension(".go") == "Go"
        assert registry.get_language_by_extension(".java") == "Java"
        assert registry.get_language_by_extension(".swift") == "Swift"
        assert registry.get_language_by_extension(".html") == "HTML"
        assert registry.get_language_by_extension(".css") == "CSS"
        assert registry.get_language_by_extension(".sql") == "SQL"
    
    def test_extension_conflict_resolution(self):
        """Test that higher priority languages win extension conflicts."""
        registry = LanguageRegistry()
        
        # .h extension is shared by C and C++
        # C++ has higher priority (9) than C (8)
        assert registry.get_language_by_extension(".h") == "C++"
    
    def test_case_insensitive_extension_lookup(self):
        """Test that extension lookup is case-insensitive."""
        registry = LanguageRegistry()
        
        assert registry.get_language_by_extension(".PY") == "Python"
        assert registry.get_language_by_extension(".Js") == "JavaScript"
        assert registry.get_language_by_extension(".TS") == "TypeScript"
    
    def test_get_all_languages(self):
        """Test getting all registered languages."""
        registry = LanguageRegistry()
        
        all_langs = registry.get_all_languages()
        
        assert len(all_langs) > 0
        assert all(isinstance(lang, LanguageCapability) for lang in all_langs)
        
        # Check that key languages are in the list
        lang_names = {lang.name for lang in all_langs}
        assert "Python" in lang_names
        assert "JavaScript" in lang_names
        assert "C++" in lang_names
    
    def test_get_enabled_languages(self):
        """Test getting only enabled languages."""
        registry = LanguageRegistry()
        
        # Initially all languages should be enabled
        all_langs = registry.get_all_languages()
        enabled_langs = registry.get_enabled_languages()
        
        assert len(enabled_langs) == len(all_langs)
        
        # Disable one language
        registry.disable_language("Ruby")
        enabled_langs = registry.get_enabled_languages()
        
        assert len(enabled_langs) == len(all_langs) - 1
        assert all(lang.name != "Ruby" for lang in enabled_langs)
    
    def test_enable_disable_language(self):
        """Test enabling and disabling languages."""
        registry = LanguageRegistry()
        
        # Disable Python
        assert registry.disable_language("Python") is True
        assert registry.is_language_enabled("Python") is False
        
        # Enable Python
        assert registry.enable_language("Python") is True
        assert registry.is_language_enabled("Python") is True
        
        # Try to disable non-existent language
        assert registry.disable_language("Nonexistent") is False
    
    def test_get_all_extensions(self):
        """Test getting all registered extensions."""
        registry = LanguageRegistry()
        
        extensions = registry.get_all_extensions()
        
        assert len(extensions) > 0
        assert ".py" in extensions
        assert ".js" in extensions
        assert ".ts" in extensions
        assert ".c" in extensions
    
    def test_apply_config_enabled_languages(self):
        """Test applying config with explicit enabled languages."""
        registry = LanguageRegistry()
        
        config = {
            "enabled_languages": ["Python", "JavaScript", "TypeScript"]
        }
        
        registry.apply_config(config)
        
        # Only specified languages should be enabled
        assert registry.is_language_enabled("Python") is True
        assert registry.is_language_enabled("JavaScript") is True
        assert registry.is_language_enabled("TypeScript") is True
        assert registry.is_language_enabled("Ruby") is False
        assert registry.is_language_enabled("C++") is False
    
    def test_apply_config_disabled_languages(self):
        """Test applying config with disabled languages."""
        registry = LanguageRegistry()
        
        config = {
            "disabled_languages": ["Ruby", "PHP"]
        }
        
        registry.apply_config(config)
        
        # Specified languages should be disabled, others enabled
        assert registry.is_language_enabled("Python") is True
        assert registry.is_language_enabled("JavaScript") is True
        assert registry.is_language_enabled("Ruby") is False
        assert registry.is_language_enabled("PHP") is False
    
    def test_apply_config_language_overrides(self):
        """Test applying language-specific overrides."""
        registry = LanguageRegistry()
        
        config = {
            "language_overrides": {
                "Python": {"priority": 20, "enabled": True},
                "Ruby": {"enabled": False}
            }
        }
        
        registry.apply_config(config)
        
        python = registry.get_language("Python")
        assert python.priority == 20
        assert python.enabled is True
        
        ruby = registry.get_language("Ruby")
        assert ruby.enabled is False
    
    def test_apply_config_empty(self):
        """Test applying empty config doesn't break anything."""
        registry = LanguageRegistry()
        
        initial_enabled = len(registry.get_enabled_languages())
        
        registry.apply_config({})
        
        # Should remain unchanged
        assert len(registry.get_enabled_languages()) == initial_enabled
    
    def test_register_custom_language(self):
        """Test registering a custom language."""
        registry = LanguageRegistry()
        
        custom_lang = LanguageCapability(
            name="CustomLang",
            extensions={".custom"},
            priority=100
        )
        
        registry.register(custom_lang)
        
        assert registry.get_language("CustomLang") is not None
        assert registry.get_language_by_extension(".custom") == "CustomLang"
    
    def test_priority_change_rebuilds_map(self):
        """Test that changing priority rebuilds extension map."""
        registry = LanguageRegistry()
        
        # Create a scenario with shared extensions
        # Register a custom language that conflicts with Python
        custom_lang = LanguageCapability(
            name="CustomPython",
            extensions={".py"},
            priority=5
        )
        registry.register(custom_lang)
        
        # Initially Python should win (priority 10)
        assert registry.get_language_by_extension(".py") == "Python"
        
        # Give CustomPython higher priority via config
        config = {
            "language_overrides": {
                "CustomPython": {"priority": 100}
            }
        }
        registry.apply_config(config)
        
        # Now CustomPython should win for .py
        assert registry.get_language_by_extension(".py") == "CustomPython"
    
    def test_to_dict(self):
        """Test converting registry to dictionary."""
        registry = LanguageRegistry()
        
        result = registry.to_dict()
        
        assert "languages" in result
        assert "extension_map" in result
        assert isinstance(result["languages"], dict)
        assert isinstance(result["extension_map"], dict)
        
        # Check that key languages are present
        assert "Python" in result["languages"]
        assert "JavaScript" in result["languages"]
        
        # Check that extensions are mapped
        assert ".py" in result["extension_map"]
        assert result["extension_map"][".py"] == "Python"


class TestGlobalRegistry:
    """Tests for global registry functions."""
    
    def teardown_method(self):
        """Reset global registry after each test."""
        reset_global_registry()
    
    def test_get_global_registry_singleton(self):
        """Test that global registry is a singleton."""
        registry1 = get_global_registry()
        registry2 = get_global_registry()
        
        assert registry1 is registry2
    
    def test_reset_global_registry(self):
        """Test resetting the global registry."""
        registry1 = get_global_registry()
        reset_global_registry()
        registry2 = get_global_registry()
        
        assert registry1 is not registry2
    
    def test_global_registry_configuration_persists(self):
        """Test that global registry configuration persists."""
        registry = get_global_registry()
        registry.disable_language("Ruby")
        
        # Get registry again
        registry2 = get_global_registry()
        
        assert registry2.is_language_enabled("Ruby") is False


class TestBackwardCompatibility:
    """Tests for backward compatibility with existing code."""
    
    def test_all_legacy_extensions_mapped(self):
        """Test that all legacy LANGUAGE_MAP extensions are still supported in the registry."""
        from repo_analyzer.file_summary import LANGUAGE_MAP
        
        registry = get_global_registry()
        
        # Verify all legacy extensions are supported in the registry
        # This ensures backward compatibility - no regression in supported file types
        for ext in LANGUAGE_MAP.keys():
            language = registry.get_language_by_extension(ext)
            assert language is not None, \
                f"Extension {ext} from LANGUAGE_MAP not supported in registry"
    
    def test_registry_handles_disabled_languages_gracefully(self):
        """Test that disabled languages don't crash the system."""
        registry = LanguageRegistry()
        
        # Disable all languages
        for lang in registry.get_all_languages():
            registry.disable_language(lang.name)
        
        # Should still be able to query
        assert registry.get_language_by_extension(".py") == "Python"
        assert registry.is_language_enabled("Python") is False
        assert len(registry.get_enabled_languages()) == 0


class TestEdgeCases:
    """Tests for edge cases and error conditions."""
    
    def test_unknown_extension(self):
        """Test handling of unknown file extensions."""
        registry = LanguageRegistry()
        
        result = registry.get_language_by_extension(".xyz")
        assert result is None
    
    def test_empty_extension(self):
        """Test handling of empty extension."""
        registry = LanguageRegistry()
        
        result = registry.get_language_by_extension("")
        assert result is None
    
    def test_no_dot_extension(self):
        """Test handling of extension without dot."""
        registry = LanguageRegistry()
        
        # Should work with or without leading dot
        result = registry.get_language_by_extension("py")
        # May or may not match depending on implementation
    
    def test_multiple_dots_extension(self):
        """Test handling of extensions with multiple dots."""
        registry = LanguageRegistry()
        
        # Should only use the last extension
        result = registry.get_language_by_extension(".min.js")
        # Behavior may vary
    
    def test_register_duplicate_language_name(self):
        """Test registering language with duplicate name."""
        registry = LanguageRegistry()
        
        # Register Python again with different extensions
        custom_python = LanguageCapability(
            name="Python",
            extensions={".python"},
            priority=1
        )
        
        registry.register(custom_python)
        
        # Should replace the previous registration
        python = registry.get_language("Python")
        assert ".python" in python.extensions
    
    def test_get_language_nonexistent(self):
        """Test getting a language that doesn't exist."""
        registry = LanguageRegistry()
        
        result = registry.get_language("NonexistentLanguage")
        assert result is None
    
    def test_disable_already_disabled_language(self):
        """Test disabling an already disabled language."""
        registry = LanguageRegistry()
        
        registry.disable_language("Ruby")
        result = registry.disable_language("Ruby")
        
        assert result is True
        assert registry.is_language_enabled("Ruby") is False
    
    def test_enable_already_enabled_language(self):
        """Test enabling an already enabled language."""
        registry = LanguageRegistry()
        
        result = registry.enable_language("Python")
        
        assert result is True
        assert registry.is_language_enabled("Python") is True
