"""Log viewer screen — full-screen searchable log display.

Features:
- Severity coloring (ERROR=red, WARN=yellow, INFO=white, DEBUG=dim)
- Search (/) with match highlighting
- Filter (f) cycling through severity levels
- Auto-scroll with G to re-enable
- Bookmarking (b)
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static, Input, RichLog
from textual import work
from textual.binding import Binding

from lazydatabricks.api.logs import LogBlock, LogLine, LogSeverity
from lazydatabricks.tui.screens.base import BaseScreen
from lazydatabricks.tui.widgets.footer_bar import HintItem


class LogsScreen(BaseScreen):
    """Full-screen log viewer."""

    BINDINGS = [
        Binding("slash", "start_search", "Search", show=False),
        Binding("n", "next_match", "Next Match"),
        Binding("N", "prev_match", "Prev Match"),
        Binding("f", "cycle_filter", "Filter"),
        Binding("G", "go_bottom", "Bottom"),
        Binding("g", "go_top", "Top"),
        Binding("b", "toggle_bookmark", "Bookmark"),
        Binding("escape", "close_or_cancel", "Close"),
        Binding("o", "open_in_browser", "Open in Browser"),
    ]

    def __init__(self, run_id: int) -> None:
        super().__init__()
        self._run_id = run_id
        self._log_blocks: list[LogBlock] = []
        self._all_lines: list[LogLine] = []
        self._filtered_lines: list[LogLine] = []
        self._search_pattern = ""
        self._search_matches: list[int] = []  # Line indices
        self._current_match = 0
        self._filter_level = 0  # 0=ALL, 1=ERROR, 2=WARN+, 3=INFO+
        self._searching = False
        self._fallback_url = ""

    def get_context_actions(self) -> list[HintItem]:
        """Logs screen context actions."""
        actions = [
            HintItem("/", "Search"),
            HintItem("f", "Filter"),
            HintItem("g", "Top"),
            HintItem("G", "Bottom"),
            HintItem("o", "Browser"),
            HintItem("Esc", "Close"),
        ]
        if self._search_pattern:
            actions.insert(1, HintItem("n", "Next"))
            actions.insert(2, HintItem("N", "Prev"))
        return actions

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                Static(f"[bold #e94560]Logs for Run {self._run_id}[/]", id="logs-title"),
                Static("", id="logs-status"),
                RichLog(id="log-viewer", highlight=True, markup=True),
                id="logs-container",
            ),
            Vertical(
                Input(placeholder="Search pattern...", id="search-input"),
                id="search-container",
            ),
            id="screen-content",
        )

    def on_mount(self) -> None:
        """Load logs on mount."""
        super().on_mount()
        self.query_one("#search-container").display = False
        self._load_logs()

    @work(thread=True)
    def _load_logs(self) -> None:
        """Load logs in background."""
        try:
            blocks = self.lazydatabricks_app.log_ops.get_run_logs(self._run_id)
            self.app.call_from_thread(self._display_logs, blocks)
        except Exception as e:
            self.app.call_from_thread(self.notify_error, f"Failed to load logs: {e}")

    def _display_logs(self, blocks: list[LogBlock]) -> None:
        """Display the loaded logs."""
        self._log_blocks = blocks
        self._all_lines = []

        # Collect all lines
        for block in blocks:
            self._all_lines.extend(block.lines)
            if block.fallback_url:
                self._fallback_url = block.fallback_url

        self._filtered_lines = self._all_lines
        self._render_logs()
        self._update_status()

    def _render_logs(self) -> None:
        """Render the log lines to the viewer."""
        viewer = self.query_one("#log-viewer", RichLog)
        viewer.clear()

        for line in self._filtered_lines:
            style = self._get_line_style(line)
            prefix = ""
            if line.bookmarked:
                prefix = "[#e94560]★[/] "

            # Highlight search matches
            text = line.text
            if self._search_pattern and self._search_pattern.lower() in text.lower():
                # Simple highlight by wrapping matches
                import re
                pattern = re.compile(re.escape(self._search_pattern), re.IGNORECASE)
                text = pattern.sub(f"[on yellow]{self._search_pattern}[/]", text)

            viewer.write(f"{prefix}[{style}]{line.line_number:5d}[/] [{style}]{text}[/]")

    def _get_line_style(self, line: LogLine) -> str:
        """Get style for a log line based on severity."""
        return {
            LogSeverity.ERROR: "red bold",
            LogSeverity.WARN: "yellow",
            LogSeverity.INFO: "white",
            LogSeverity.DEBUG: "dim",
        }.get(line.severity, "white")

    def _update_status(self) -> None:
        """Update the status line."""
        status = self.query_one("#logs-status", Static)

        parts = [f"{len(self._filtered_lines)}/{len(self._all_lines)} lines"]

        filter_names = ["ALL", "ERROR", "WARN+", "INFO+"]
        parts.append(f"Filter: {filter_names[self._filter_level]}")

        if self._search_pattern:
            parts.append(f"Search: '{self._search_pattern}' ({len(self._search_matches)} matches)")
            if self._search_matches:
                parts.append(f"[{self._current_match + 1}/{len(self._search_matches)}]")

        status.update("[dim]" + " | ".join(parts) + "[/]")

    def _apply_filter(self) -> None:
        """Apply the current severity filter."""
        if self._filter_level == 0:  # ALL
            self._filtered_lines = self._all_lines
        elif self._filter_level == 1:  # ERROR only
            self._filtered_lines = [l for l in self._all_lines if l.severity == LogSeverity.ERROR]
        elif self._filter_level == 2:  # WARN+
            self._filtered_lines = [l for l in self._all_lines if l.severity in (LogSeverity.ERROR, LogSeverity.WARN)]
        else:  # INFO+ (excludes DEBUG)
            self._filtered_lines = [l for l in self._all_lines if l.severity != LogSeverity.DEBUG]

        self._render_logs()
        self._update_status()

    def _apply_search(self) -> None:
        """Apply search and find matches."""
        self._search_matches = []
        if self._search_pattern:
            pattern_lower = self._search_pattern.lower()
            for i, line in enumerate(self._filtered_lines):
                if pattern_lower in line.text.lower():
                    self._search_matches.append(i)

        self._current_match = 0
        self._render_logs()
        self._update_status()

        if self._search_matches:
            self._scroll_to_match()

    def _scroll_to_match(self) -> None:
        """Scroll to the current search match."""
        if not self._search_matches:
            return

        viewer = self.query_one("#log-viewer", RichLog)
        line_idx = self._search_matches[self._current_match]
        # RichLog doesn't have direct scroll-to-line, but we can approximate
        # by scrolling to a percentage
        if self._filtered_lines:
            percent = line_idx / len(self._filtered_lines)
            viewer.scroll_to(y=int(percent * viewer.virtual_size.height))

    def action_start_search(self) -> None:
        """Show search input."""
        self._searching = True
        search_container = self.query_one("#search-container")
        search_container.display = True
        search_input = self.query_one("#search-input", Input)
        search_input.value = self._search_pattern
        search_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search submission."""
        self._search_pattern = event.value
        self._searching = False
        self.query_one("#search-container").display = False
        self._apply_search()

    def action_next_match(self) -> None:
        """Jump to next search match."""
        if not self._search_matches:
            return
        self._current_match = (self._current_match + 1) % len(self._search_matches)
        self._update_status()
        self._scroll_to_match()

    def action_prev_match(self) -> None:
        """Jump to previous search match."""
        if not self._search_matches:
            return
        self._current_match = (self._current_match - 1) % len(self._search_matches)
        self._update_status()
        self._scroll_to_match()

    def action_cycle_filter(self) -> None:
        """Cycle through severity filters."""
        self._filter_level = (self._filter_level + 1) % 4
        self._apply_filter()
        filter_names = ["ALL", "ERROR only", "WARN+", "INFO+"]
        self.notify_success(f"Filter: {filter_names[self._filter_level]}")

    def action_go_bottom(self) -> None:
        """Scroll to bottom."""
        viewer = self.query_one("#log-viewer", RichLog)
        viewer.scroll_end()

    def action_go_top(self) -> None:
        """Scroll to top."""
        viewer = self.query_one("#log-viewer", RichLog)
        viewer.scroll_home()

    def action_toggle_bookmark(self) -> None:
        """Toggle bookmark on current line."""
        # This is a simplified version - would need cursor tracking for real implementation
        self.notify_success("Bookmark toggled (feature in progress)")

    def action_close_or_cancel(self) -> None:
        """Close search or screen."""
        if self._searching:
            self._searching = False
            self.query_one("#search-container").display = False
        else:
            self.app.pop_screen()

    def action_open_in_browser(self) -> None:
        """Open logs in Databricks UI."""
        if self._fallback_url:
            import webbrowser
            webbrowser.open(self._fallback_url)
        else:
            self.notify_warning("No browser URL available")
