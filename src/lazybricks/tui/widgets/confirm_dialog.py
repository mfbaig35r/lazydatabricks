"""Confirmation dialog for destructive actions.

Shows a modal dialog asking the user to confirm before proceeding.
"""

from __future__ import annotations

from typing import Callable

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.binding import Binding


class ConfirmDialog(ModalScreen[bool]):
    """Modal confirmation dialog."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
        Binding("y", "confirm", "Yes"),
        Binding("n", "cancel", "No"),
    ]

    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }

    #confirm-container {
        width: 60;
        height: auto;
        min-height: 10;
        max-height: 20;
        background: #1a1a2e;
        border: thick #e94560;
        padding: 1 2;
    }

    #confirm-title {
        text-style: bold;
        color: #e94560;
        margin-bottom: 1;
    }

    #confirm-message {
        margin-bottom: 2;
    }

    #confirm-buttons {
        align: center middle;
        height: 3;
    }

    #confirm-buttons Button {
        margin: 0 1;
        min-width: 12;
    }

    #btn-confirm {
        background: #e94560;
    }

    #btn-cancel {
        background: #444;
    }
    """

    def __init__(
        self,
        title: str = "Confirm Action",
        message: str = "Are you sure you want to proceed?",
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
    ) -> None:
        super().__init__()
        self._title = title
        self._message = message
        self._confirm_label = confirm_label
        self._cancel_label = cancel_label

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"[bold #e94560]{self._title}[/]", id="confirm-title"),
            Static(self._message, id="confirm-message"),
            Horizontal(
                Button(self._confirm_label, id="btn-confirm", variant="error"),
                Button(self._cancel_label, id="btn-cancel"),
                id="confirm-buttons",
            ),
            id="confirm-container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "btn-confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        """Confirm action."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Cancel action."""
        self.dismiss(False)
