"""Status bar widget — context-sensitive keybindings.

Shows available keybindings for the current screen context.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static


class StatusBar(Widget):
    """Context-sensitive status bar showing available keybindings."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: #1a1a2e;
        border-top: solid #0f3460;
    }

    StatusBar Horizontal {
        height: 100%;
        align: left middle;
        padding: 0 1;
    }

    StatusBar .key {
        color: #e94560;
        text-style: bold;
    }

    StatusBar .desc {
        color: #888888;
        margin-right: 2;
    }
    """

    # List of (key, description) tuples
    bindings: reactive[list[tuple[str, str]]] = reactive(list)

    def __init__(self, bindings: list[tuple[str, str]] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.bindings = bindings or []

    def compose(self) -> ComposeResult:
        yield Horizontal(id="status-bindings")

    def on_mount(self) -> None:
        """Initial render."""
        self._render_bindings()

    def watch_bindings(self, new_bindings: list[tuple[str, str]]) -> None:
        """React to binding changes."""
        self._render_bindings()

    def _render_bindings(self) -> None:
        """Render the keybinding display."""
        try:
            container = self.query_one("#status-bindings", Horizontal)
            container.remove_children()

            for key, desc in self.bindings:
                container.mount(Static(f"[bold #e94560]{key}[/]", classes="key"))
                container.mount(Static(f" {desc}  ", classes="desc"))
        except Exception:
            # Widget not yet composed
            pass

    def set_bindings(self, bindings: list[tuple[str, str]]) -> None:
        """Update the displayed bindings."""
        self.bindings = bindings


# Default keybindings for different contexts
GLOBAL_BINDINGS = [
    ("h", "home"),
    ("c", "clusters"),
    ("j", "jobs"),
    ("p", "pipelines"),
    ("w", "warehouses"),
    ("P", "profiles"),
    ("A", "arm"),
    ("?", "help"),
    ("q", "quit"),
]

HOME_BINDINGS = [
    ("r", "refresh"),
    ("c", "clusters"),
    ("j", "jobs"),
    ("w", "warehouses"),
    ("A", "arm"),
    ("?", "help"),
    ("q", "quit"),
]

CLUSTERS_BINDINGS = [
    ("s", "start"),
    ("t", "terminate"),
    ("R", "restart"),
    ("l", "logs"),
    ("r", "refresh"),
    ("A", "arm"),
    ("?", "help"),
]

JOBS_BINDINGS = [
    ("Enter", "select"),
    ("Tab", "pane"),
    ("Esc", "back"),
    ("n", "run now"),
    ("c", "cancel"),
    ("R", "rerun"),
    ("l", "logs"),
    ("r", "refresh"),
]

PIPELINES_BINDINGS = [
    ("Enter", "select"),
    ("Tab", "pane"),
    ("Esc", "back"),
    ("s", "start"),
    ("S", "stop"),
    ("f", "full refresh"),
    ("r", "refresh"),
]

LOGS_BINDINGS = [
    ("/", "search"),
    ("n", "next"),
    ("N", "prev"),
    ("f", "filter"),
    ("G", "bottom"),
    ("g", "top"),
    ("b", "bookmark"),
    ("Esc", "close"),
]

WAREHOUSES_BINDINGS = [
    ("s", "start"),
    ("S", "stop"),
    ("r", "refresh"),
    ("A", "arm"),
    ("?", "help"),
]

CONFIG_BINDINGS = [
    ("Enter", "switch"),
    ("t", "test"),
    ("?", "help"),
]
