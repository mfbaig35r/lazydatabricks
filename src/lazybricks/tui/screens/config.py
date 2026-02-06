"""Config screen — profile management.

Shows available Databricks CLI profiles and allows switching between them.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Static
from textual.worker import work

from lazybricks.models.config import DatabricksProfile
from lazybricks.tui.screens.base import BaseScreen
from lazybricks.tui.widgets.status_bar import CONFIG_BINDINGS


class ConfigScreen(BaseScreen):
    """Configuration and profile management screen."""

    SCREEN_BINDINGS = CONFIG_BINDINGS

    BINDINGS = [
        ("enter", "switch_profile", "Switch"),
        ("t", "test_connection", "Test"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._profiles: list[DatabricksProfile] = []
        self._selected_profile: DatabricksProfile | None = None
        self._current_profile: str = ""

    def compose(self) -> ComposeResult:
        yield Container(
            Horizontal(
                Vertical(
                    Static("[bold #e94560]Profiles[/]", id="profiles-title"),
                    DataTable(id="profiles-table"),
                    id="profiles-list",
                ),
                Vertical(
                    Static("", id="profile-detail"),
                    id="detail-panel",
                ),
            ),
            id="screen-content",
        )

    def on_mount(self) -> None:
        """Initialize the screen."""
        super().on_mount()

        table = self.query_one("#profiles-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Profile", "Host", "Auth", "Active")

        self._load_profiles()

    def _load_profiles(self) -> None:
        """Load available profiles."""
        config = self.lazybricks_app.client.config
        self._profiles = config.available_profiles
        self._current_profile = config.profile_name or ""

        self._update_table()

    def _update_table(self) -> None:
        """Update the profiles table."""
        table = self.query_one("#profiles-table", DataTable)
        table.clear()

        for profile in self._profiles:
            is_active = profile.name == self._current_profile
            active_marker = "[green]●[/]" if is_active else ""

            table.add_row(
                profile.name,
                profile.host_short[:40],
                profile.auth_method.value,
                active_marker,
                key=profile.name,
            )

        if self._profiles:
            table.move_cursor(row=0)
            self._update_detail(self._profiles[0])

    def _update_detail(self, profile: DatabricksProfile) -> None:
        """Update the detail panel."""
        self._selected_profile = profile
        detail = self.query_one("#profile-detail", Static)

        is_active = profile.name == self._current_profile

        lines = [
            f"[bold #e94560]{profile.name}[/]",
            "[green]● Active[/]" if is_active else "",
            "",
            f"[dim]Host:[/]      {profile.host}",
            f"[dim]Auth:[/]      {profile.auth_method.value}",
        ]

        if profile.cluster_id:
            lines.append(f"[dim]Cluster:[/]   {profile.cluster_id}")

        if profile.account_id:
            lines.append(f"[dim]Account:[/]   {profile.account_id}")

        detail.update("\n".join(lines))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlight."""
        if event.row_key and event.row_key.value:
            profile = next((p for p in self._profiles if p.name == event.row_key.value), None)
            if profile:
                self._update_detail(profile)

    def action_switch_profile(self) -> None:
        """Switch to the selected profile."""
        if not self._selected_profile:
            return

        if self._selected_profile.name == self._current_profile:
            self.notify_success("Already using this profile")
            return

        self._do_switch_profile(self._selected_profile.name)

    @work(thread=True)
    def _do_switch_profile(self, profile_name: str) -> None:
        """Switch profile in background."""
        try:
            from lazybricks.models.config import LazyBricksConfig

            new_config = LazyBricksConfig.load(profile=profile_name)
            self.lazybricks_app.client.config = new_config
            self.lazybricks_app.client.refresh()

            self.call_from_thread(self._on_profile_switched, profile_name)
        except Exception as e:
            self.call_from_thread(self.notify_error, f"Failed to switch: {e}")

    def _on_profile_switched(self, profile_name: str) -> None:
        """Handle successful profile switch."""
        self._current_profile = profile_name
        self._update_table()

        # Update app header
        config = self.lazybricks_app.client.config
        self.lazybricks_app.update_header(
            workspace=config.host_short,
            profile=config.profile_name or "",
        )

        self.notify_success(f"Switched to profile: {profile_name}")

    def action_test_connection(self) -> None:
        """Test connection with selected profile."""
        if not self._selected_profile:
            return

        self._do_test_connection()

    @work(thread=True)
    def _do_test_connection(self) -> None:
        """Test connection in background."""
        try:
            result = self.lazybricks_app.client.test_connection()
            if result.get("status") == "ok":
                user = result.get("user", "unknown")
                self.call_from_thread(self.notify_success, f"Connection OK - user: {user}")
            else:
                self.call_from_thread(self.notify_error, f"Connection failed: {result.get('error')}")
        except Exception as e:
            self.call_from_thread(self.notify_error, f"Connection test failed: {e}")
