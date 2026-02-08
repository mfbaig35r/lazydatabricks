"""Help overlay — modal showing all keybindings.

Shows complete keyboard reference organized by section.
Dynamically includes extension keybindings when extensions are loaded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Static
from textual.binding import Binding

if TYPE_CHECKING:
    from lazybricks.tui.app import LazyBricksApp


class HelpOverlay(ModalScreen):
    """Modal overlay showing all keybindings."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("question_mark", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
    ]

    DEFAULT_CSS = """
    HelpOverlay {
        align: center middle;
    }

    #help-container {
        width: 70;
        max-height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #help-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }

    #help-scroll {
        height: auto;
        max-height: 100%;
        padding-bottom: 2;
    }

    .section-title {
        color: $primary;
        text-style: bold;
        margin-top: 1;
    }

    .help-row {
        margin-left: 2;
    }

    .key {
        color: $warning;
    }

    #help-footer {
        margin-top: 1;
        text-align: center;
        color: $text-muted;
    }
    """

    def _get_extension_nav_items(self) -> list[Static]:
        """Get navigation items for loaded extensions."""
        items = []
        try:
            from lazybricks.tui.app import LazyBricksApp
            if isinstance(self.app, LazyBricksApp):
                for ext in self.app.extensions:
                    key = ext.info.hotkey
                    label = ext.info.display_name
                    items.append(Static(rf"  \[{key}]       {label}", classes="help-row"))
        except Exception:
            pass
        return items

    def _get_extension_sections(self) -> list[Static]:
        """Get help sections for loaded extensions."""
        sections = []
        try:
            from lazybricks.tui.app import LazyBricksApp
            if isinstance(self.app, LazyBricksApp):
                for ext in self.app.extensions:
                    # Add section title
                    sections.append(Static(ext.info.display_name, classes="section-title"))

                    # Add extension help items
                    for key, desc in ext.get_help_items():
                        sections.append(Static(rf"  \[{key}]       {desc}", classes="help-row"))
        except Exception:
            pass
        return sections

    def compose(self) -> ComposeResult:
        # Build extension nav items
        extension_nav = self._get_extension_nav_items()

        # Build extension sections
        extension_sections = self._get_extension_sections()

        # Build content list
        content = [
            # Global Navigation
            Static("Global Navigation", classes="section-title"),
            Static(r"  \[h]       Home", classes="help-row"),
            Static(r"  \[c]       Clusters", classes="help-row"),
            Static(r"  \[j]       Jobs", classes="help-row"),
            Static(r"  \[p]       Pipelines", classes="help-row"),
            Static(r"  \[w]       Warehouses", classes="help-row"),
            *extension_nav,  # Insert extension nav items
            Static(r"  \[P]       Profiles", classes="help-row"),
            Static(r"  \[?]       Help", classes="help-row"),
            Static(r"  \[q]       Quit", classes="help-row"),

            # Armed Mode
            Static("Armed Mode", classes="section-title"),
            Static(r"  \[A]       Arm (30s countdown)", classes="help-row"),
            Static(r"  \[Esc]     Disarm (when armed)", classes="help-row"),
            Static("  Destructive actions only work when armed.", classes="help-row"),
            Static("  Footer shows ARMED + countdown when active.", classes="help-row"),

            # Clusters
            Static("Clusters", classes="section-title"),
            Static(r"  \[r]       Refresh list", classes="help-row"),
            Static(r"  \[Enter]   Open in browser", classes="help-row"),
            Static(r"  \[s]       Start (when armed, if stopped)", classes="help-row"),
            Static(r"  \[t]       Terminate (when armed, if running)", classes="help-row"),
            Static(r"  \[R]       Restart (when armed, if running)", classes="help-row"),

            # Jobs
            Static("Jobs", classes="section-title"),
            Static(r"  \[Tab]     Switch pane (Jobs/Runs/Detail)", classes="help-row"),
            Static(r"  \[Enter]   Drill down into selection", classes="help-row"),
            Static(r"  \[Esc]     Back up one pane", classes="help-row"),
            Static(r"  \[r]       Refresh", classes="help-row"),
            Static(r"  \[l]       View logs for selected run", classes="help-row"),
            Static(r"  \[n]       Run job now (when armed)", classes="help-row"),
            Static(r"  \[c]       Cancel run (when armed, if active)", classes="help-row"),
            Static(r"  \[R]       Rerun (when armed, if completed)", classes="help-row"),

            # Pipelines
            Static("Pipelines", classes="section-title"),
            Static(r"  \[Tab]     Switch pane (Pipelines/Updates/Detail)", classes="help-row"),
            Static(r"  \[Enter]   Drill down into selection", classes="help-row"),
            Static(r"  \[Esc]     Back up one pane", classes="help-row"),
            Static(r"  \[r]       Refresh", classes="help-row"),
            Static(r"  \[s]       Start update (when armed, if idle)", classes="help-row"),
            Static(r"  \[S]       Stop pipeline (when armed, if running)", classes="help-row"),
            Static(r"  \[f]       Full refresh (when armed, if idle)", classes="help-row"),

            # Logs
            Static("Logs", classes="section-title"),
            Static(r"  \[/]       Search", classes="help-row"),
            Static(r"  \[n]       Next match", classes="help-row"),
            Static(r"  \[N]       Previous match", classes="help-row"),
            Static(r"  \[f]       Cycle filter (ALL/ERROR/WARN+/INFO+)", classes="help-row"),
            Static(r"  \[g]       Go to top", classes="help-row"),
            Static(r"  \[G]       Go to bottom", classes="help-row"),
            Static(r"  \[o]       Open in browser", classes="help-row"),
            Static(r"  \[Esc]     Close log viewer", classes="help-row"),

            # Warehouses
            Static("Warehouses", classes="section-title"),
            Static(r"  \[r]       Refresh list", classes="help-row"),
            Static(r"  \[Enter]   Open in browser", classes="help-row"),
            Static(r"  \[s]       Start (when armed, if stopped)", classes="help-row"),
            Static(r"  \[S]       Stop (when armed, if running)", classes="help-row"),

            # Extension sections (inserted before Profiles)
            *extension_sections,

            # Profiles
            Static("Profiles", classes="section-title"),
            Static(r"  \[Enter]   Switch to selected profile", classes="help-row"),
            Static(r"  \[t]       Test connection", classes="help-row"),
        ]

        scroll = ScrollableContainer(*content, id="help-scroll")

        yield Container(
            Static("LazyBricks Keyboard Reference", id="help-title"),
            scroll,
            Static("Press Esc to close", id="help-footer"),
            id="help-container",
        )

    def action_dismiss(self) -> None:
        """Close the help overlay."""
        self.app.pop_screen()
