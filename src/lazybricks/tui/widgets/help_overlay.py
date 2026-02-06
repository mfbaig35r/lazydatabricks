"""Help overlay — modal showing all keybindings.

Shows context-aware help with all available keybindings.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static
from textual.binding import Binding


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
        max-height: 80%;
        background: #1a1a2e;
        border: thick #e94560;
        padding: 1 2;
    }

    #help-title {
        text-align: center;
        text-style: bold;
        color: #e94560;
        margin-bottom: 1;
    }

    .help-section {
        margin-top: 1;
    }

    .help-section-title {
        color: #e94560;
        text-style: bold;
    }

    .help-row {
        margin-left: 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Container(
            Static("[bold #e94560]LazyBricks Help[/]", id="help-title"),
            Vertical(
                # Navigation
                Static("[bold #e94560]Navigation[/]", classes="help-section-title"),
                Static("  [yellow]h[/]       Home screen", classes="help-row"),
                Static("  [yellow]c[/]       Clusters screen", classes="help-row"),
                Static("  [yellow]j[/]       Jobs screen", classes="help-row"),
                Static("  [yellow]w[/]       Warehouses screen", classes="help-row"),
                Static("  [yellow]Esc[/]     Back / Close", classes="help-row"),
                Static("  [yellow]q[/]       Quit", classes="help-row"),

                # Armed Mode
                Static("[bold #e94560]Armed Mode[/]", classes="help-section-title"),
                Static("  [yellow]A[/]       Toggle armed mode (30s)", classes="help-row"),
                Static("  [dim]Destructive actions require armed mode[/]", classes="help-row"),

                # Clusters
                Static("[bold #e94560]Clusters (when armed)[/]", classes="help-section-title"),
                Static("  [yellow]s[/]       Start cluster", classes="help-row"),
                Static("  [yellow]t[/]       Terminate cluster", classes="help-row"),
                Static("  [yellow]R[/]       Restart cluster", classes="help-row"),

                # Jobs
                Static("[bold #e94560]Jobs[/]", classes="help-section-title"),
                Static("  [yellow]Tab[/]     Switch pane", classes="help-row"),
                Static("  [yellow]Enter[/]   Select / Drill down", classes="help-row"),
                Static("  [yellow]n[/]       Run now (armed)", classes="help-row"),
                Static("  [yellow]c[/]       Cancel run (armed)", classes="help-row"),
                Static("  [yellow]R[/]       Rerun (armed)", classes="help-row"),
                Static("  [yellow]l[/]       View logs", classes="help-row"),

                # Logs
                Static("[bold #e94560]Logs[/]", classes="help-section-title"),
                Static("  [yellow]/[/]       Search", classes="help-row"),
                Static("  [yellow]n/N[/]     Next/Prev match", classes="help-row"),
                Static("  [yellow]f[/]       Cycle filter (ALL/ERROR/WARN+/INFO+)", classes="help-row"),
                Static("  [yellow]G/g[/]     Go to bottom/top", classes="help-row"),
                Static("  [yellow]o[/]       Open in browser", classes="help-row"),

                # Warehouses
                Static("[bold #e94560]Warehouses (when armed)[/]", classes="help-section-title"),
                Static("  [yellow]s[/]       Start warehouse", classes="help-row"),
                Static("  [yellow]S[/]       Stop warehouse", classes="help-row"),

                # Common
                Static("[bold #e94560]Common[/]", classes="help-section-title"),
                Static("  [yellow]r[/]       Refresh current view", classes="help-row"),
                Static("  [yellow]?[/]       Show this help", classes="help-row"),

                classes="help-section",
            ),
            Static("\n[dim]Press Esc, ?, or q to close[/]"),
            id="help-container",
        )

    def action_dismiss(self) -> None:
        """Close the help overlay."""
        self.app.pop_screen()
