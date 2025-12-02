# Copyright (c) 2025 John Brosnihan
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
"""
Language capability registry for multi-language repository analysis.

This module provides a pluggable registry of supported programming languages,
their file extensions, and analyzer capabilities. It enables deterministic
language detection and allows for future extension without modifying core files.
"""

from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field


@dataclass
class LanguageCapability:
    """
    Defines capabilities and metadata for a programming language.
    
    Attributes:
        name: Human-readable language name (e.g., "Python", "JavaScript")
        extensions: Set of file extensions (e.g., {".py", ".pyw"})
        has_structure_parser: Whether the language has a structure parser
        has_dependency_scanner: Whether the language has a dependency scanner
        enabled: Whether analysis is enabled for this language
        priority: Priority for resolving extension conflicts (higher = preferred)
    """
    name: str
    extensions: Set[str]
    has_structure_parser: bool = False
    has_dependency_scanner: bool = False
    enabled: bool = True
    priority: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "extensions": sorted(self.extensions),
            "has_structure_parser": self.has_structure_parser,
            "has_dependency_scanner": self.has_dependency_scanner,
            "enabled": self.enabled,
            "priority": self.priority
        }


class LanguageRegistry:
    """
    Registry of supported programming languages and their capabilities.
    
    This registry provides a centralized, pluggable system for managing
    language support. It enables:
    - Deterministic file extension to language mapping
    - Language-specific feature toggles
    - Conflict resolution for shared extensions
    - Easy extension without modifying core analyzer code
    """
    
    def __init__(self):
        self._languages: Dict[str, LanguageCapability] = {}
        self._extension_map: Dict[str, str] = {}
        self._initialize_default_languages()
    
    def _initialize_default_languages(self) -> None:
        """Initialize the registry with default language definitions."""
        
        # Python - full support with AST parser
        self.register(LanguageCapability(
            name="Python",
            extensions={".py", ".pyw"},
            has_structure_parser=True,
            has_dependency_scanner=True,
            priority=10
        ))
        
        # JavaScript - full support with regex parser
        self.register(LanguageCapability(
            name="JavaScript",
            extensions={".js", ".jsx", ".mjs", ".cjs"},
            has_structure_parser=True,
            has_dependency_scanner=True,
            priority=10
        ))
        
        # TypeScript - full support with regex parser
        self.register(LanguageCapability(
            name="TypeScript",
            extensions={".ts", ".tsx"},
            has_structure_parser=True,
            has_dependency_scanner=True,
            priority=10
        ))
        
        # C - basic support
        self.register(LanguageCapability(
            name="C",
            extensions={".c"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=8
        ))
        
        # C++ - basic support, higher priority than C for .h files
        self.register(LanguageCapability(
            name="C++",
            extensions={".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".h"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=9
        ))
        
        # C# - basic support
        self.register(LanguageCapability(
            name="C#",
            extensions={".cs"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=8
        ))
        
        # Rust - basic support
        self.register(LanguageCapability(
            name="Rust",
            extensions={".rs"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=8
        ))
        
        # Go - basic support
        self.register(LanguageCapability(
            name="Go",
            extensions={".go"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=8
        ))
        
        # Java - basic support
        self.register(LanguageCapability(
            name="Java",
            extensions={".java"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=8
        ))
        
        # Swift - basic support
        self.register(LanguageCapability(
            name="Swift",
            extensions={".swift"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=8
        ))
        
        # HTML - basic support
        self.register(LanguageCapability(
            name="HTML",
            extensions={".html", ".htm"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        # CSS - basic support
        self.register(LanguageCapability(
            name="CSS",
            extensions={".css"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        # SQL - basic support
        self.register(LanguageCapability(
            name="SQL",
            extensions={".sql"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        # Additional languages with lower priority (existing in LANGUAGE_MAP)
        
        self.register(LanguageCapability(
            name="Ruby",
            extensions={".rb"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        self.register(LanguageCapability(
            name="PHP",
            extensions={".php"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        self.register(LanguageCapability(
            name="Kotlin",
            extensions={".kt"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        self.register(LanguageCapability(
            name="Scala",
            extensions={".scala"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        self.register(LanguageCapability(
            name="Shell",
            extensions={".sh"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        self.register(LanguageCapability(
            name="Bash",
            extensions={".bash"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        self.register(LanguageCapability(
            name="Zsh",
            extensions={".zsh"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        self.register(LanguageCapability(
            name="PowerShell",
            extensions={".ps1"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        self.register(LanguageCapability(
            name="R",
            extensions={".r", ".R"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        self.register(LanguageCapability(
            name="Objective-C",
            extensions={".m"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        self.register(LanguageCapability(
            name="SCSS",
            extensions={".scss"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        self.register(LanguageCapability(
            name="Sass",
            extensions={".sass"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        self.register(LanguageCapability(
            name="Less",
            extensions={".less"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        self.register(LanguageCapability(
            name="Vue",
            extensions={".vue"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=5
        ))
        
        # Markup and config languages
        
        self.register(LanguageCapability(
            name="Markdown",
            extensions={".md"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=3
        ))
        
        self.register(LanguageCapability(
            name="reStructuredText",
            extensions={".rst"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=3
        ))
        
        self.register(LanguageCapability(
            name="YAML",
            extensions={".yml", ".yaml"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=3
        ))
        
        self.register(LanguageCapability(
            name="JSON",
            extensions={".json"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=3
        ))
        
        self.register(LanguageCapability(
            name="XML",
            extensions={".xml"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=3
        ))
        
        self.register(LanguageCapability(
            name="TOML",
            extensions={".toml"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=3
        ))
        
        self.register(LanguageCapability(
            name="INI",
            extensions={".ini"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=3
        ))
        
        self.register(LanguageCapability(
            name="Config",
            extensions={".cfg", ".conf"},
            has_structure_parser=False,
            has_dependency_scanner=False,
            priority=2
        ))
    
    def register(self, language: LanguageCapability) -> None:
        """
        Register a language in the registry.
        
        This will rebuild the extension map to handle priority changes.
        For extension conflicts, the language with higher priority wins.
        If priorities are equal, the first registered language is used.
        
        Args:
            language: Language capability to register
        """
        self._languages[language.name] = language
        self._rebuild_extension_map()
    
    def get_language_by_extension(self, extension: str) -> Optional[str]:
        """
        Get language name for a file extension if the language is enabled.
        
        Args:
            extension: File extension (e.g., ".py", ".js")
        
        Returns:
            Language name if found and enabled, or None otherwise
        """
        lang_name = self._extension_map.get(extension.lower())
        if lang_name and self.is_language_enabled(lang_name):
            return lang_name
        return None
    
    def get_language(self, name: str) -> Optional[LanguageCapability]:
        """
        Get language capability by name.
        
        Args:
            name: Language name
        
        Returns:
            LanguageCapability or None if not found
        """
        return self._languages.get(name)
    
    def get_all_languages(self) -> List[LanguageCapability]:
        """
        Get all registered languages.
        
        Returns:
            List of all language capabilities
        """
        return list(self._languages.values())
    
    def get_enabled_languages(self) -> List[LanguageCapability]:
        """
        Get all enabled languages.
        
        Returns:
            List of enabled language capabilities
        """
        return [lang for lang in self._languages.values() if lang.enabled]
    
    def get_all_extensions(self) -> Set[str]:
        """
        Get all registered file extensions.
        
        Returns:
            Set of all file extensions
        """
        return set(self._extension_map.keys())
    
    def enable_language(self, name: str) -> bool:
        """
        Enable a language.
        
        Args:
            name: Language name
        
        Returns:
            True if language was found and enabled, False otherwise
        """
        if name in self._languages:
            self._languages[name].enabled = True
            return True
        return False
    
    def disable_language(self, name: str) -> bool:
        """
        Disable a language.
        
        Args:
            name: Language name
        
        Returns:
            True if language was found and disabled, False otherwise
        """
        if name in self._languages:
            self._languages[name].enabled = False
            return True
        return False
    
    def is_language_enabled(self, name: str) -> bool:
        """
        Check if a language is enabled.
        
        Args:
            name: Language name
        
        Returns:
            True if language is enabled, False otherwise
        """
        lang = self._languages.get(name)
        return lang.enabled if lang else False
    
    def apply_config(self, config: Dict[str, Any]) -> None:
        """
        Apply configuration to the registry.
        
        Config format:
        {
            "enabled_languages": ["Python", "JavaScript", ...],
            "disabled_languages": ["Ruby", "PHP", ...],
            "language_overrides": {
                "Python": {"priority": 15, "enabled": true},
                ...
            }
        }
        
        Configuration is applied in this order:
        1. enabled_languages (if specified, disables all others first)
        2. disabled_languages (disables specified languages)
        3. language_overrides (applies individual settings)
        
        Note: If a language appears in both enabled_languages and disabled_languages,
        it will be disabled (disabled_languages takes precedence).
        
        Args:
            config: Configuration dictionary
        """
        # Validate config structure
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")
        
        # Apply enabled/disabled lists
        enabled_languages = config.get("enabled_languages")
        if enabled_languages is not None:
            if not isinstance(enabled_languages, list):
                raise ValueError("enabled_languages must be a list")
            # If explicit enabled list provided, disable all first
            for lang in self._languages.values():
                lang.enabled = False
            # Then enable specified languages
            for name in enabled_languages:
                if not isinstance(name, str):
                    raise ValueError(f"Language name must be a string, got {type(name)}")
                if not self.enable_language(name):
                    # Language not found - log but don't fail
                    pass
        
        disabled_languages = config.get("disabled_languages", [])
        if not isinstance(disabled_languages, list):
            raise ValueError("disabled_languages must be a list")
        for name in disabled_languages:
            if not isinstance(name, str):
                raise ValueError(f"Language name must be a string, got {type(name)}")
            self.disable_language(name)
        
        # Apply language-specific overrides
        priority_changed = False
        overrides = config.get("language_overrides", {})
        if not isinstance(overrides, dict):
            raise ValueError("language_overrides must be a dictionary")
        
        for name, settings in overrides.items():
            if not isinstance(name, str):
                raise ValueError(f"Language name must be a string, got {type(name)}")
            if not isinstance(settings, dict):
                raise ValueError(f"Language settings must be a dictionary, got {type(settings)}")
            
            if name in self._languages:
                lang = self._languages[name]
                if "enabled" in settings:
                    if not isinstance(settings["enabled"], bool):
                        raise ValueError(f"enabled setting must be a boolean, got {type(settings['enabled'])}")
                    lang.enabled = settings["enabled"]
                if "priority" in settings:
                    priority = settings["priority"]
                    if not isinstance(priority, (int, float)):
                        raise ValueError(f"priority setting must be a number, got {type(priority)}")
                    lang.priority = int(priority)
                    priority_changed = True
        
        # Rebuild extension map if any priority changed
        if priority_changed:
            self._rebuild_extension_map()
    
    def _rebuild_extension_map(self) -> None:
        """Rebuild extension map after priority changes."""
        self._extension_map.clear()
        # Sort by priority (descending) to process higher priority first
        sorted_langs = sorted(
            self._languages.values(),
            key=lambda x: x.priority,
            reverse=True
        )
        for lang in sorted_langs:
            for ext in lang.extensions:
                ext_lower = ext.lower()
                if ext_lower not in self._extension_map:
                    self._extension_map[ext_lower] = lang.name
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Export registry to dictionary for serialization.
        
        Returns:
            Dictionary representation of the registry
        """
        return {
            "languages": {
                name: lang.to_dict() 
                for name, lang in sorted(self._languages.items())
            },
            "extension_map": {
                ext: lang_name 
                for ext, lang_name in sorted(self._extension_map.items())
            }
        }


# Global registry instance
_global_registry: Optional[LanguageRegistry] = None


def get_global_registry() -> LanguageRegistry:
    """
    Get the global language registry instance.
    
    Returns:
        Global LanguageRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = LanguageRegistry()
    return _global_registry


def reset_global_registry() -> None:
    """Reset the global registry (mainly for testing)."""
    global _global_registry
    _global_registry = None
