"""Base screen with common patterns for all LazyDatabricks screens.

All screens inherit from this to get:
- Access to app-level state (client, guard, ops)
- Common refresh patterns
- Error handling
- Footer bar (rendered per-screen)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen

from lazydatabricks.tui.widgets.footer_bar import FooterBar, HintItem

if TYPE_CHECKING:
    from lazydatabricks.tui.app import LazyDatabricksApp


class BaseScreen(Screen):
    """Base class for all LazyDatabricks screens.

    Provides:
    - Type-safe access to app instance
    - Common refresh pattern with error handling
    - Footer bar with context actions
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._footer_bar: FooterBar | None = None

    @property
    def lazydatabricks_app(self) -> "LazyDatabricksApp":
        """Type-safe access to the LazyDatabricks app."""
        from lazydatabricks.tui.app import LazyDatabricksApp
        assert isinstance(self.app, LazyDatabricksApp)
        return self.app

    @property
    def client(self):
        """Shortcut to DatabricksClient."""
        return self.lazydatabricks_app.client

    @property
    def guard(self):
        """Shortcut to ArmedGuard."""
        return self.lazydatabricks_app.guard

    def on_mount(self) -> None:
        """Called when screen is mounted. Adds footer and updates it."""
        # Build extension hints for footer
        extension_hints = [
            HintItem(ext.info.hotkey, ext.info.display_name)
            for ext in self.lazydatabricks_app.extensions
        ]

        # Create and mount footer bar
        self._footer_bar = FooterBar(
            guard=self.guard,
            extension_hints=extension_hints,
        )
        self.mount(self._footer_bar)
        self._update_footer()

    def on_screen_resume(self) -> None:
        """Called when screen is resumed. Updates footer."""
        self._update_footer()

    def get_context_actions(self) -> list[HintItem]:
        """Return context actions for footer bar.

        Override in subclasses to provide screen-specific actions.
        Actions with destructive=True only show when armed.
        """
        return []

    def _update_footer(self) -> None:
        """Update footer bar with this screen's context actions."""
        if self._footer_bar:
            actions = self.get_context_actions()
            self._footer_bar.set_context_actions(actions)

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
