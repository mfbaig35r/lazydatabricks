"""Footer bar widget — single-line context-aware action hints.

Renders a fixed 1-line footer with:
- Left zone: global navigation (screen switching)
- Right zone: context actions for current view/selection

Never wraps; truncates intelligently to fit terminal width.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

if TYPE_CHECKING:
    from lazybricks.api.guard import ArmedGuard


@dataclass
class HintItem:
    """A single key hint."""
    key: str      # e.g., "h", "Enter", "Esc"
    label: str    # e.g., "Home", "Open", "Back"
    destructive: bool = False  # Show only in armed mode


# Global navigation items (shared across all screens)
GLOBAL_NAV: list[HintItem] = [
    HintItem("h", "Home"),
    HintItem("c", "Clusters"),
    HintItem("j", "Jobs"),
    HintItem("w", "Warehouses"),
    HintItem("p", "Profiles"),
    HintItem("?", "Help"),
    HintItem("q", "Quit"),
]


class FooterBar(Widget):
    """Single-line footer with navigation and context actions."""

    DEFAULT_CSS = """
    FooterBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text;
    }

    FooterBar > Static {
        width: 100%;
        height: 1;
    }
    """

    # Context actions for current screen (set by screens)
    context_actions: reactive[list[HintItem]] = reactive(list, always_update=True)

    # Armed state
    is_armed: reactive[bool] = reactive(False)
    armed_seconds: reactive[int] = reactive(0)

    def __init__(
        self,
        guard: "ArmedGuard | None" = None,
        context_actions: list[HintItem] | None = None,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._guard = guard
        self.context_actions = context_actions or []

    def compose(self) -> ComposeResult:
        yield Static("", id="footer-content")

    def on_mount(self) -> None:
        """Start refresh interval for armed countdown."""
        self.set_interval(1.0, self._refresh_armed_state)
        self._render_footer()

    def _refresh_armed_state(self) -> None:
        """Update armed state from guard."""
        if self._guard:
            was_armed = self.is_armed
            self.is_armed = self._guard.is_armed
            self.armed_seconds = self._guard.remaining_seconds
            if was_armed != self.is_armed or self.is_armed:
                self._render_footer()

    def watch_context_actions(self, actions: list[HintItem]) -> None:
        """Re-render when context actions change."""
        self._render_footer()

    def watch_is_armed(self, armed: bool) -> None:
        """Re-render when armed state changes."""
        self._render_footer()

    def set_context_actions(self, actions: list[HintItem]) -> None:
        """Update context actions (called by screens)."""
        self.context_actions = actions

    def _render_footer(self) -> None:
        """Render the footer bar content."""
        try:
            content = self.query_one("#footer-content", Static)
        except Exception:
            return

        width = self.size.width or 80

        # Build left zone (global nav)
        left_items = self._format_items(GLOBAL_NAV)

        # Build right zone (context actions)
        if self.is_armed:
            # Armed mode: show destructive actions + disarm hint
            armed_actions = [a for a in self.context_actions if a.destructive]
            armed_actions.append(HintItem("Esc", "Disarm"))
            right_items = self._format_items(armed_actions)
            armed_prefix = f"[$error]ARMED {self.armed_seconds}s[/] "
            right_zone = armed_prefix + right_items
        else:
            # Normal mode: show non-destructive actions + arm hint
            normal_actions = [a for a in self.context_actions if not a.destructive]
            if any(a.destructive for a in self.context_actions):
                normal_actions.append(HintItem("A", "Arm"))
            right_items = self._format_items(normal_actions)
            right_zone = right_items

        left_zone = left_items
        delimiter = " [$text-muted]|[/] "

        # Calculate display widths (approximate, ignoring markup)
        left_plain = self._plain_text(left_zone)
        right_plain = self._plain_text(right_zone)
        delim_plain = " | "

        total_width = len(left_plain) + len(delim_plain) + len(right_plain)

        if total_width <= width:
            # Everything fits
            final = left_zone + delimiter + right_zone
        elif len(left_plain) + len(delim_plain) + 3 <= width:
            # Truncate right zone
            available = width - len(left_plain) - len(delim_plain) - 3
            right_zone = self._truncate_zone(right_zone, available)
            final = left_zone + delimiter + right_zone
        elif len(left_plain) <= width:
            # Only left zone fits
            final = left_zone
        else:
            # Truncate left zone
            final = self._truncate_zone(left_zone, width - 3)

        content.update(final)

    def _format_items(self, items: list[HintItem]) -> str:
        """Format hint items as styled string."""
        parts = []
        for item in items:
            # Use \[ to escape the opening bracket in Rich markup (raw f-string)
            parts.append(rf"[$primary]\[{item.key}][/] {item.label}")
        return "  ".join(parts)

    def _plain_text(self, markup: str) -> str:
        """Strip markup to get plain text for width calculation."""
        import re
        return re.sub(r'\[.*?\]', '', markup)

    def _truncate_zone(self, zone: str, max_width: int) -> str:
        """Truncate a zone to fit width, ending with ..."""
        plain = self._plain_text(zone)
        if len(plain) <= max_width:
            return zone

        # Simple truncation: find a safe cut point
        # This is approximate since we're dealing with markup
        target_len = max_width - 3
        if target_len <= 0:
            return "..."

        # Cut at last space before target length
        cut_point = plain[:target_len].rfind("  ")
        if cut_point <= 0:
            cut_point = target_len

        # Find corresponding position in markup string
        plain_pos = 0
        markup_pos = 0
        in_tag = False

        while plain_pos < cut_point and markup_pos < len(zone):
            if zone[markup_pos] == '[':
                in_tag = True
            elif zone[markup_pos] == ']':
                in_tag = False
            elif not in_tag:
                plain_pos += 1
            markup_pos += 1

        return zone[:markup_pos] + "..."
