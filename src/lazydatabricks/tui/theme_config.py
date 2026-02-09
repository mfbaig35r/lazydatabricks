"""Theme configuration — terminal-aware with user overrides.

By default, uses ANSI colors that inherit from your terminal theme.
Users can override specific colors in ~/.lazydatabricks/config.toml:

    [theme]
    accent = "#e94560"
    background = "#0a0a0f"
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11


@dataclass
class ThemeColors:
    """Theme color configuration with terminal-aware defaults."""

    # Textual built-in theme name (uses terminal ANSI colors by default)
    # Options: textual-ansi, textual-dark, textual-light, nord, gruvbox,
    #          catppuccin-mocha, dracula, tokyo-night, monokai, solarized-dark
    theme_name: str = "textual-ansi"

    # Core UI colors - use Textual design tokens (inherit from theme)
    background: str = "$background"        # Theme background
    surface: str = "$surface"              # Surface color
    panel: str = "$panel"                  # Panel backgrounds
    border: str = "$primary-background"    # Borders

    # Text colors
    text: str = "$text"                    # Primary text
    text_muted: str = "$text-muted"        # Dimmed text

    # Accent color - uses primary by default
    accent: str = "$primary"               # Theme's primary color

    # Status colors - use ANSI for terminal consistency
    success: str = "$success"
    error: str = "$error"
    warning: str = "$warning"
    info: str = "$primary"

    # State-specific (can override)
    running: str = "$success"
    stopped: str = "$text-muted"
    pending: str = "$warning"

    # Armed mode
    armed: str = "$error"
    disarmed: str = "$success"

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "ThemeColors":
        """Load theme with user overrides from config file."""
        theme = cls()

        # Default config path
        if config_path is None:
            config_path = Path.home() / ".lazydatabricks" / "config.toml"

        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    config = tomllib.load(f)

                theme_config = config.get("theme", {})

                # Apply overrides for any field that exists
                for key, value in theme_config.items():
                    if hasattr(theme, key) and value:
                        setattr(theme, key, value)

            except Exception:
                # If config is malformed, use defaults
                pass

        return theme


def generate_css(theme: ThemeColors) -> str:
    """Generate Textual CSS from theme configuration."""

    return f"""
/* ─── Generated Theme ─────────────────────────────────────── */
/* Terminal-aware defaults with user overrides */

/* ─── Global ─────────────────────────────────────────── */

Screen {{
    background: {theme.background};
}}

/* ─── Header Widget ─────────────────────────────────── */

#header {{
    dock: top;
    height: 3;
    background: {theme.surface};
    border-bottom: solid {theme.border};
    padding: 0 1;
}}

#header-title {{
    width: auto;
    color: {theme.accent};
    text-style: bold;
}}

#header-status {{
    width: auto;
    margin-left: 2;
}}

#header-armed {{
    width: auto;
    dock: right;
    margin-right: 1;
}}

.armed-active {{
    color: {theme.armed};
    text-style: bold;
}}

.armed-inactive {{
    color: {theme.disarmed};
}}

/* ─── Status Bar ────────────────────────────────────── */

#status-bar {{
    dock: bottom;
    height: 1;
    background: {theme.surface};
    border-top: solid {theme.border};
    padding: 0 1;
}}

.status-key {{
    color: {theme.accent};
    text-style: bold;
}}

.status-desc {{
    color: {theme.text_muted};
    margin-right: 2;
}}

/* ─── Screen Content ────────────────────────────────── */

#screen-content {{
    padding: 1 2;
}}

/* ─── Data Tables ───────────────────────────────────── */

DataTable {{
    height: auto;
    max-height: 100%;
}}

DataTable > .datatable--header {{
    background: {theme.surface};
    color: {theme.accent};
    text-style: bold;
}}

DataTable > .datatable--cursor {{
    background: {theme.border};
}}

DataTable > .datatable--hover {{
    background: {theme.panel};
}}

/* ─── State Styles ─────────────────────────────────── */

.state-running {{
    color: {theme.running};
}}

.state-terminated {{
    color: {theme.stopped};
}}

.state-pending {{
    color: {theme.pending};
}}

.state-error {{
    color: {theme.error};
    text-style: bold;
}}

/* ─── Result Styles ─────────────────────────────────── */

.result-success {{
    color: {theme.success};
}}

.result-failed {{
    color: {theme.error};
    text-style: bold;
}}

.result-canceled {{
    color: {theme.text_muted};
}}

/* ─── Panels ────────────────────────────────────────── */

.panel {{
    border: solid {theme.border};
    padding: 1;
    margin: 1 0;
}}

.panel-title {{
    color: {theme.accent};
    text-style: bold;
    margin-bottom: 1;
}}

/* ─── Detail Panel ─────────────────────────────────── */

#detail-panel {{
    width: 40%;
    dock: right;
    border-left: solid {theme.border};
    padding: 1 2;
    background: {theme.panel};
}}

.detail-label {{
    color: {theme.text_muted};
}}

.detail-value {{
    color: {theme.text};
}}

/* ─── Modals / Dialogs ─────────────────────────────── */

ModalScreen {{
    align: center middle;
}}

#confirm-dialog {{
    width: 60;
    height: auto;
    min-height: 10;
    max-height: 20;
    background: {theme.surface};
    border: thick {theme.accent};
    padding: 1 2;
}}

#confirm-title {{
    text-style: bold;
    color: {theme.accent};
    margin-bottom: 1;
}}

#confirm-message {{
    margin-bottom: 1;
}}

#confirm-buttons {{
    align: center bottom;
    height: 3;
}}

#confirm-buttons Button {{
    margin: 0 1;
}}

/* ─── Help Overlay ─────────────────────────────────── */

#help-overlay {{
    width: 80;
    height: auto;
    max-height: 80%;
    background: {theme.surface};
    border: thick {theme.border};
    padding: 2;
}}

#help-title {{
    text-style: bold;
    color: {theme.accent};
    text-align: center;
    margin-bottom: 1;
}}

.help-section {{
    margin-top: 1;
}}

.help-section-title {{
    color: {theme.accent};
    text-style: bold;
}}

.help-key {{
    color: {theme.warning};
    min-width: 8;
}}

.help-desc {{
    color: {theme.text};
}}

/* ─── Log Viewer ────────────────────────────────────── */

#log-viewer {{
    height: 100%;
    border: solid {theme.border};
}}

.log-line-error {{
    color: {theme.error};
}}

.log-line-warn {{
    color: {theme.warning};
}}

.log-line-info {{
    color: {theme.text};
}}

.log-line-debug {{
    color: {theme.text_muted};
}}

.log-line-number {{
    color: {theme.text_muted};
    min-width: 5;
}}

.log-bookmark {{
    color: {theme.accent};
}}

.log-search-match {{
    background: {theme.warning};
}}

/* ─── Three-Pane Layout (Jobs screen) ───────────────── */

#pane-jobs {{
    width: 1fr;
    border-right: solid {theme.border};
}}

#pane-runs {{
    width: 1fr;
    border-right: solid {theme.border};
}}

#pane-detail {{
    width: 1fr;
}}

.pane-active {{
    border: solid {theme.accent};
}}

.pane-inactive {{
    border: solid {theme.border};
}}

/* ─── Input / Search ────────────────────────────────── */

#search-input {{
    dock: bottom;
    height: 3;
    background: {theme.surface};
    border-top: solid {theme.border};
}}

#search-input Input {{
    width: 100%;
}}

/* ─── Toast Notifications ───────────────────────────── */

Toast {{
    background: {theme.surface};
    border: solid {theme.border};
    padding: 1 2;
}}

Toast.-information {{
    border: solid {theme.info};
}}

Toast.-warning {{
    border: solid {theme.warning};
}}

Toast.-error {{
    border: solid {theme.error};
}}
"""


# Singleton for easy access
_theme: Optional[ThemeColors] = None


def get_theme() -> ThemeColors:
    """Get the current theme (loads from config on first call)."""
    global _theme
    if _theme is None:
        _theme = ThemeColors.load()
    return _theme


def get_css() -> str:
    """Get the generated CSS for the current theme."""
    return generate_css(get_theme())
