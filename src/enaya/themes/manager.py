#!/usr/bin/env python3
"""
Enaya Agent - Themes/Skins System
Customizable themes with live reload across all surfaces.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


# =============================================================================
# Theme Data Classes
# =============================================================================

@dataclass
class ThemePalette:
    """Color palette for a theme."""
    # Base colors
    background: str = "#0d1117"
    surface: str = "#161b22"
    surface_elevated: str = "#21262d"
    
    # Text colors
    text_primary: str = "#e6edf3"
    text_secondary: str = "#8b949e"
    text_muted: str = "#6e7681"
    
    # Accent colors
    accent: str = "#00d4aa"  # Teal
    accent_hover: str = "#00b894"
    accent_muted: str = "#00d4aa33"
    
    # Status colors
    success: str = "#3fb950"
    warning: str = "#d29922"
    error: str = "#f85149"
    info: str = "#58a6ff"
    
    # Border
    border: str = "#30363d"
    border_focus: str = "#00d4aa"
    
    # Code
    code_background: str = "#0d1117"
    code_text: str = "#e6edf3"
    
    # Selection
    selection: str = "#00d4aa44"


@dataclass
class ThemeTypography:
    """Typography settings."""
    font_family: str = "JetBrains Mono, Fira Code, Consolas, monospace"
    font_size: int = 14
    line_height: float = 1.6
    font_weight_normal: int = 400
    font_weight_bold: int = 600


@dataclass
class ThemeSpacing:
    """Spacing scale."""
    xs: int = 4
    sm: int = 8
    md: int = 16
    lg: int = 24
    xl: int = 32
    xxl: int = 48


@dataclass
class Theme:
    """Complete theme definition."""
    name: str
    display_name: str
    description: str = ""
    author: str = ""
    version: str = "1.0.0"
    
    palette: ThemePalette = field(default_factory=ThemePalette)
    typography: ThemeTypography = field(default_factory=ThemeTypography)
    spacing: ThemeSpacing = field(default_factory=ThemeSpacing)
    
    # Surface-specific overrides
    cli_overrides: dict = field(default_factory=dict)
    tui_overrides: dict = field(default_factory=dict)
    dashboard_overrides: dict = field(default_factory=dict)
    desktop_overrides: dict = field(default_factory=dict)


# =============================================================================
# Built-in Themes
# =============================================================================

BUILTIN_THEMES = {
    "default": Theme(
        name="default",
        display_name="Enaya Default",
        description="Clean dark theme with teal accents",
        author="Enaya Team",
    ),
    
    "light": Theme(
        name="light",
        display_name="Enaya Light",
        description="Clean light theme",
        author="Enaya Team",
        palette=ThemePalette(
            background="#ffffff",
            surface="#f6f8fa",
            surface_elevated="#ffffff",
            text_primary="#24292f",
            text_secondary="#57606a",
            text_muted="#6e7781",
            accent="#006b5b",
            accent_hover="#00584a",
            accent_muted="#006b5b1a",
            success="#2da44e",
            warning="#9a6700",
            error="#cf222e",
            info="#0969da",
            border="#d0d7de",
            border_focus="#006b5b",
            code_background="#f6f8fa",
            code_text="#24292f",
            selection="#006b5b44",
        ),
    ),
    
    "synthwave": Theme(
        name="synthwave",
        display_name="Synthwave",
        description="Retro-futuristic neon theme",
        author="Enaya Team",
        palette=ThemePalette(
            background="#1a103c",
            surface="#251a5c",
            surface_elevated="#2d1f6e",
            text_primary="#ffe4e1",
            text_secondary="#b8a8d1",
            text_muted="#8a7a9e",
            accent="#ff00ff",
            accent_hover="#ff66ff",
            accent_muted="#ff00ff33",
            success="#00ff88",
            warning="#ffaa00",
            error="#ff3366",
            info="#00ffff",
            border="#4a2c6e",
            border_focus="#ff00ff",
            code_background="#160b3a",
            code_text="#ffe4e1",
            selection="#ff00ff44",
        ),
        typography=ThemeTypography(
            font_family="'Orbitron', 'JetBrains Mono', monospace",
        ),
    ),
    
    "dracula": Theme(
        name="dracula",
        display_name="Dracula",
        description="Popular dark theme",
        author="Dracula Theme Contributors",
        palette=ThemePalette(
            background="#282a36",
            surface="#44475a",
            surface_elevated="#6272a4",
            text_primary="#f8f8f2",
            text_secondary="#6272a4",
            text_muted="#44475a",
            accent="#bd93f9",
            accent_hover="#caa9fa",
            accent_muted="#bd93f933",
            success="#50fa7b",
            warning="#f1fa8c",
            error="#ff5555",
            info="#8be9fd",
            border="#6272a4",
            border_focus="#bd93f9",
            code_background="#282a36",
            code_text="#f8f8f2",
            selection="#bd93f944",
        ),
    ),
    
    "nord": Theme(
        name="nord",
        display_name="Nord",
        description="Arctic-inspired theme",
        author="Nord Theme Contributors",
        palette=ThemePalette(
            background="#2e3440",
            surface="#3b4252",
            surface_elevated="#434c5e",
            text_primary="#eceff4",
            text_secondary="#81a1c1",
            text_muted="#4c566a",
            accent="#88c0d0",
            accent_hover="#8fbcbb",
            accent_muted="#88c0d033",
            success="#a3be8c",
            warning="#ebcb8b",
            error="#bf616a",
            info="#88c0d0",
            border="#4c566a",
            border_focus="#88c0d0",
            code_background="#2e3440",
            code_text="#eceff4",
            selection="#88c0d044",
        ),
    ),
    
    "github": Theme(
        name="github",
        display_name="GitHub Dark",
        description="GitHub's official dark theme",
        author="GitHub",
        palette=ThemePalette(
            background="#0d1117",
            surface="#161b22",
            surface_elevated="#21262d",
            text_primary="#e6edf3",
            text_secondary="#8b949e",
            text_muted="#6e7681",
            accent="#58a6ff",
            accent_hover="#79b8ff",
            accent_muted="#58a6ff33",
            success="#3fb950",
            warning="#d29922",
            error="#f85149",
            info="#58a6ff",
            border="#30363d",
            border_focus="#58a6ff",
            code_background="#0d1117",
            code_text="#e6edf3",
            selection="#58a6ff44",
        ),
    ),
}


# =============================================================================
# Theme Manager
# =============================================================================

class ThemeManager:
    """Manages themes with live reload across surfaces."""
    
    def __init__(self, themes_dir: Path = None):
        self.themes_dir = themes_dir or (Path.home() / ".enaya" / "skins")
        self.themes_dir.mkdir(parents=True, exist_ok=True)
        
        self.themes: dict[str, Theme] = {}
        self.current_theme: Optional[Theme] = None
        self._listeners: list[Callable] = []
        
        self._load_builtin_themes()
        self._load_custom_themes()
        
        # Set default
        if "default" in self.themes:
            self.current_theme = self.themes["default"]
    
    def _load_builtin_themes(self) -> None:
        for name, theme in BUILTIN_THEMES.items():
            self.themes[name] = theme
    
    def _load_custom_themes(self) -> None:
        for theme_file in self.themes_dir.glob("*.yaml"):
            try:
                with open(theme_file) as f:
                    data = yaml.safe_load(f)
                
                # Parse theme
                palette = ThemePalette(**data.get("palette", {}))
                typography = ThemeTypography(**data.get("typography", {}))
                spacing = ThemeSpacing(**data.get("spacing", {}))
                
                theme = Theme(
                    name=data.get("name", theme_file.stem),
                    display_name=data.get("display_name", theme_file.stem),
                    description=data.get("description", ""),
                    author=data.get("author", ""),
                    version=data.get("version", "1.0.0"),
                    palette=palette,
                    typography=typography,
                    spacing=spacing,
                    cli_overrides=data.get("cli_overrides", {}),
                    tui_overrides=data.get("tui_overrides", {}),
                    dashboard_overrides=data.get("dashboard_overrides", {}),
                    desktop_overrides=data.get("desktop_overrides", {}),
                )
                
                self.themes[theme.name] = theme
            except Exception as e:
                print(f"Failed to load theme {theme_file}: {e}")
    
    def get_theme(self, name: str) -> Optional[Theme]:
        return self.themes.get(name)
    
    def set_theme(self, name: str) -> bool:
        if name in self.themes:
            self.current_theme = self.themes[name]
            self._notify_listeners()
            return True
        return False
    
    def get_current(self) -> Optional[Theme]:
        return self.current_theme
    
    def list_themes(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "display_name": t.display_name,
                "description": t.description,
                "author": t.author,
                "builtin": t.name in BUILTIN_THEMES,
            }
            for t in self.themes.values()
        ]
    
    def create_custom_theme(self, name: str, base_theme: str = "default") -> Theme:
        """Create a new custom theme based on an existing one."""
        base = self.themes.get(base_theme, self.themes["default"])
        
        # Deep copy
        import copy
        new_theme = copy.deepcopy(base)
        new_theme.name = name
        new_theme.display_name = name.title()
        new_theme.description = f"Custom theme based on {base_theme}"
        new_theme.author = "User"
        new_theme.version = "1.0.0"
        
        # Save to file
        theme_file = self.themes_dir / f"{name}.yaml"
        self.save_theme(new_theme, theme_file)
        
        self.themes[name] = new_theme
        return new_theme
    
    def save_theme(self, theme: Theme, path: Path) -> None:
        """Save theme to YAML file."""
        data = {
            "name": theme.name,
            "display_name": theme.display_name,
            "description": theme.description,
            "author": theme.author,
            "version": theme.version,
            "palette": theme.palette.__dict__,
            "typography": theme.typography.__dict__,
            "spacing": theme.spacing.__dict__,
            "cli_overrides": theme.cli_overrides,
            "tui_overrides": theme.tui_overrides,
            "dashboard_overrides": theme.dashboard_overrides,
            "desktop_overrides": theme.desktop_overrides,
        }
        
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def update_color(self, key: str, value: str) -> bool:
        """Update a single color in the current theme."""
        if not self.current_theme:
            return False
        
        if hasattr(self.current_theme.palette, key):
            setattr(self.current_theme.palette, key, value)
            self._notify_listeners()
            return True
        return False
    
    def add_listener(self, callback: Callable) -> None:
        """Add a listener for theme changes."""
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self) -> None:
        for listener in self._listeners:
            try:
                listener(self.current_theme)
            except Exception:
                pass
    
    def get_css_variables(self) -> dict[str, str]:
        """Get CSS variables for web surfaces."""
        if not self.current_theme:
            return {}
        
        p = self.current_theme.palette
        return {
            "--bg-primary": p.background,
            "--bg-secondary": p.surface,
            "--bg-tertiary": p.surface_elevated,
            "--text-primary": p.text_primary,
            "--text-secondary": p.text_secondary,
            "--text-muted": p.text_muted,
            "--accent": p.accent,
            "--accent-hover": p.accent_hover,
            "--accent-muted": p.accent_muted,
            "--success": p.success,
            "--warning": p.warning,
            "--error": p.error,
            "--info": p.info,
            "--border": p.border,
            "--border-focus": p.border_focus,
            "--code-bg": p.code_background,
            "--code-text": p.code_text,
            "--selection": p.selection,
        }
    
    def get_rich_style(self) -> dict[str, str]:
        """Get Rich library styles for CLI/TUI."""
        if not self.current_theme:
            return {}
        
        p = self.current_theme.palette
        return {
            "primary": p.accent,
            "secondary": p.text_secondary,
            "success": p.success,
            "warning": p.warning,
            "error": p.error,
            "info": p.info,
            "muted": p.text_muted,
            "dim": p.text_muted,
        }


# =============================================================================
# Skin CLI Commands
# =============================================================================

def skin_list() -> None:
    """List available themes."""
    manager = ThemeManager()
    themes = manager.list_themes()
    
    print("Available themes:")
    for t in themes:
        marker = " *" if t["name"] == manager.current_theme.name else ""
        builtin = " (builtin)" if t["builtin"] else ""
        print(f"  {t['name']}{marker}{builtin} - {t['display_name']}: {t['description']}")


def skin_use(name: str) -> bool:
    """Set active theme."""
    manager = ThemeManager()
    if manager.set_theme(name):
        print(f"Theme set to: {name}")
        return True
    else:
        print(f"Theme not found: {name}")
        return False


def skin_set(key: str, value: str) -> bool:
    """Set a specific color value."""
    manager = ThemeManager()
    if manager.update_color(key, value):
        print(f"Set {key} = {value}")
        # Save to current theme file
        if manager.current_theme and manager.current_theme.name not in BUILTIN_THEMES:
            theme_file = manager.themes_dir / f"{manager.current_theme.name}.yaml"
            manager.save_theme(manager.current_theme, theme_file)
        return True
    else:
        print(f"Unknown color key: {key}")
        return False


def skin_create(name: str, base: str = "default") -> None:
    """Create a new custom theme."""
    manager = ThemeManager()
    theme = manager.create_custom_theme(name, base)
    print(f"Created theme: {name} (based on {base})")
    print(f"Edit {manager.themes_dir / f'{name}.yaml'} to customize")


def skin_export(name: str, output: str) -> None:
    """Export theme to file."""
    manager = ThemeManager()
    theme = manager.get_theme(name)
    if not theme:
        print(f"Theme not found: {name}")
        return
    
    output_path = Path(output)
    manager.save_theme(theme, output_path)
    print(f"Exported {name} to {output}")


# Global instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager