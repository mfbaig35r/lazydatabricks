"""Base screen with common patterns for all LazyBricks screens.

All screens inherit from this to get:
- Access to app-level state (client, guard, ops)
- Common refresh patterns
- Error handling
- Status bar updates
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen

if TYPE_CHECKING:
    from lazybricks.tui.app import LazyBricksApp


class BaseScreen(Screen):
    """Base class for all LazyBricks screens.

    Provides:
    - Type-safe access to app instance
    - Common refresh pattern with error handling
    - Status bar binding management
    """

    # Subclasses should override this with their keybindings
    SCREEN_BINDINGS: list[tuple[str, str]] = []

    @property
    def lazybricks_app(self) -> "LazyBricksApp":
        """Type-safe access to the LazyBricks app."""
        from lazybricks.tui.app import LazyBricksApp
        assert isinstance(self.app, LazyBricksApp)
        return self.app

    @property
    def client(self):
        """Shortcut to DatabricksClient."""
        return self.lazybricks_app.client

    @property
    def guard(self):
        """Shortcut to ArmedGuard."""
        return self.lazybricks_app.guard

    def on_mount(self) -> None:
        """Called when screen is mounted. Updates status bar."""
        self._update_status_bar()

    def on_screen_resume(self) -> None:
        """Called when screen is resumed. Updates status bar."""
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        """Update status bar with this screen's bindings."""
        if self.SCREEN_BINDINGS:
            self.lazybricks_app.update_status_bar(self.SCREEN_BINDINGS)

    def notify_error(self, message: str) -> None:
        """Show an error notification."""
        self.app.notify(message, severity="error", timeout=5)

    def notify_success(self, message: str) -> None:
        """Show a success notification."""
        self.app.notify(message, severity="information", timeout=3)

    def notify_warning(self, message: str) -> None:
        """Show a warning notification."""
        self.app.notify(message, severity="warning", timeout=4)

    def require_armed(self, action_name: str) -> bool:
        """Check if armed mode is active.

        If not armed, shows a warning notification.

        Returns:
            True if armed and action can proceed, False otherwise.
        """
        if self.guard.is_armed:
            return True

        self.notify_warning(f"Press A to arm before {action_name}")
        return False
