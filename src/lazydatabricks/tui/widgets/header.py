"""Header widget — workspace info and armed status.

Displays:
- LazyDatabricks title
- Current workspace/profile info
- Armed mode status with countdown timer
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from lazydatabricks.api.guard import ArmedGuard


class Header(Widget):
    """Application header with armed status indicator."""

    DEFAULT_CSS = """
    Header {
        dock: top;
        height: 3;
        background: #1a1a2e;
        border-bottom: solid #0f3460;
    }

    Header Horizontal {
        height: 100%;
        align: left middle;
        padding: 0 1;
    }

    Header #header-title {
        color: #e94560;
        text-style: bold;
        margin-right: 2;
    }

    Header #header-workspace {
        color: #888888;
    }

    Header #header-armed {
        dock: right;
        margin-right: 1;
        min-width: 20;
        text-align: right;
    }

    Header .armed-active {
        color: #ff4444;
        text-style: bold;
    }

    Header .armed-inactive {
        color: #44ff44;
    }
    """

    workspace: reactive[str] = reactive("")
    profile: reactive[str] = reactive("")
    armed_display: reactive[str] = reactive("READ-ONLY")
    is_armed: reactive[bool] = reactive(False)

    def __init__(
        self,
        guard: ArmedGuard,
        workspace: str = "",
        profile: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._guard = guard
        self.workspace = workspace
        self.profile = profile

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static("LazyDatabricks", id="header-title")
            yield Static("", id="header-workspace")
            yield Static("", id="header-armed")

    def on_mount(self) -> None:
        """Start the armed status timer."""
        self._update_workspace()
        self._update_armed_status()
        # Update armed status every second
        self.set_interval(1.0, self._update_armed_status)

    def _update_workspace(self) -> None:
        """Update workspace display."""
        try:
            workspace_widget = self.query_one("#header-workspace", Static)
            if self.profile:
                workspace_widget.update(f"{self.workspace} [{self.profile}]")
            else:
                workspace_widget.update(self.workspace)
        except Exception:
            # Widget not yet composed
            pass

    def _update_armed_status(self) -> None:
        """Update the armed status display."""
        if self._guard.is_armed:
            remaining = self._guard.remaining_seconds
            self.armed_display = f"ARMED ({remaining}s)"
            self.is_armed = True
        else:
            self.armed_display = "READ-ONLY"
            self.is_armed = False

        try:
            armed_widget = self.query_one("#header-armed", Static)
            if self.is_armed:
                armed_widget.update(f"[bold red]ARMED ({self._guard.remaining_seconds}s)[/]")
                armed_widget.remove_class("armed-inactive")
                armed_widget.add_class("armed-active")
            else:
                armed_widget.update("[green]READ-ONLY[/]")
                armed_widget.remove_class("armed-active")
                armed_widget.add_class("armed-inactive")
        except Exception:
            # Widget not yet composed
            pass

    def watch_workspace(self, new_value: str) -> None:
        """React to workspace changes."""
        self._update_workspace()

    def watch_profile(self, new_value: str) -> None:
        """React to profile changes."""
        self._update_workspace()
