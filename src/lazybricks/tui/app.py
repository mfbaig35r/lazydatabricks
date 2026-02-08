"""LazyBricks main TUI application.

This is the entry point for the Textual TUI. It owns:
- DatabricksClient instance
- ArmedGuard instance
- All operations instances (ClusterOps, JobOps, etc.)
- Extensions (optional feature sets)
- Global keybindings and screen routing
"""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container

from lazybricks.api.client import DatabricksClient
from lazybricks.api.clusters import ClusterOps
from lazybricks.api.guard import ArmedGuard
from lazybricks.api.health import HealthBuilder
from lazybricks.api.jobs import JobOps
from lazybricks.api.logs import LogOps
from lazybricks.api.pipelines import PipelineOps
from lazybricks.api.warehouses import WarehouseOps
from lazybricks.extensions import load_extensions, load_lazybricks_config
from lazybricks.extensions.base import BaseExtension
from lazybricks.tui.theme_config import get_css, get_theme
from lazybricks.tui.widgets.header import Header


class LazyBricksApp(App):
    """LazyBricks TUI application."""

    CSS = ""  # Set dynamically in __init__

    BINDINGS = [
        Binding("h", "go_home", "Home", show=False),
        Binding("c", "go_clusters", "Clusters", show=False),
        Binding("j", "go_jobs", "Jobs", show=False),
        Binding("p", "go_pipelines", "Pipelines", show=False),
        Binding("w", "go_warehouses", "Warehouses", show=False),
        Binding("l", "go_logs", "Logs", show=False),
        Binding("P", "go_config", "Config/Profiles", show=False),
        Binding("A", "toggle_armed", "Arm/Disarm", show=False),
        Binding("question_mark", "show_help", "Help", show=False),
        Binding("q", "quit", "Quit", show=False),
        Binding("escape", "back", "Back", show=False),
    ]

    SCREENS = {}  # Will be populated dynamically

    def __init__(self, client: DatabricksClient) -> None:
        # Load theme config
        self._theme_config = get_theme()
        LazyBricksApp.CSS = get_css()
        super().__init__()
        # Set theme after init
        self.theme = self._theme_config.theme_name
        self._client = client
        self._guard = ArmedGuard(ttl_seconds=30)

        # Operations instances
        self._cluster_ops = ClusterOps(client)
        self._job_ops = JobOps(client)
        self._pipeline_ops = PipelineOps(client)
        self._warehouse_ops = WarehouseOps(client)
        self._log_ops = LogOps(client)
        self._health_builder = HealthBuilder(client)

        # Load LazyBricks config and extensions
        self._lazybricks_config = load_lazybricks_config()
        self._extensions = load_extensions(client, self._lazybricks_config)
        self._extension_ops: dict[str, Any] = {}

        # Create ops instances for each extension
        for ext in self._extensions:
            ext_config = self._lazybricks_config.get("extensions", {}).get(ext.info.name, {})
            ops_class = ext.get_ops_class()
            self._extension_ops[ext.info.name] = ops_class(client, ext_config)

        # Widgets (created in compose)
        self._header: Header | None = None

    @property
    def client(self) -> DatabricksClient:
        """The Databricks API client."""
        return self._client

    @property
    def guard(self) -> ArmedGuard:
        """The armed mode guard."""
        return self._guard

    @property
    def cluster_ops(self) -> ClusterOps:
        """Cluster operations."""
        return self._cluster_ops

    @property
    def job_ops(self) -> JobOps:
        """Job operations."""
        return self._job_ops

    @property
    def pipeline_ops(self) -> PipelineOps:
        """Pipeline operations."""
        return self._pipeline_ops

    @property
    def warehouse_ops(self) -> WarehouseOps:
        """Warehouse operations."""
        return self._warehouse_ops

    @property
    def log_ops(self) -> LogOps:
        """Log operations."""
        return self._log_ops

    @property
    def health_builder(self) -> HealthBuilder:
        """Health snapshot builder."""
        return self._health_builder

    @property
    def extensions(self) -> list[BaseExtension]:
        """Loaded extensions."""
        return self._extensions

    def get_extension_ops(self, name: str) -> Any | None:
        """Get ops instance for an extension by name."""
        return self._extension_ops.get(name)

    def compose(self) -> ComposeResult:
        """Compose the app layout."""
        # Get workspace info for header
        config = self._client.config
        workspace = config.host_short if config else ""
        profile = config.profile_name if config else ""

        # Create header
        self._header = Header(
            guard=self._guard,
            workspace=workspace,
            profile=profile,
        )

        yield self._header
        yield Container(id="screen-content")

    def on_mount(self) -> None:
        """Called when app is mounted."""
        # Install core screens
        from lazybricks.tui.screens.home import HomeScreen
        from lazybricks.tui.screens.clusters import ClustersScreen
        from lazybricks.tui.screens.jobs import JobsScreen
        from lazybricks.tui.screens.pipelines import PipelinesScreen
        from lazybricks.tui.screens.warehouses import WarehousesScreen
        from lazybricks.tui.screens.config import ConfigScreen

        self.install_screen(HomeScreen(), name="home")
        self.install_screen(ClustersScreen(), name="clusters")
        self.install_screen(JobsScreen(), name="jobs")
        self.install_screen(PipelinesScreen(), name="pipelines")
        self.install_screen(WarehousesScreen(), name="warehouses")
        self.install_screen(ConfigScreen(), name="config")

        # Install extension screens
        for ext in self._extensions:
            screen_class = ext.get_screen_class()
            self.install_screen(screen_class(), name=ext.info.name)

        # Start on home screen
        self.push_screen("home")

    def update_header(self, workspace: str = "", profile: str = "") -> None:
        """Update header workspace/profile display."""
        if self._header:
            if workspace:
                self._header.workspace = workspace
            if profile:
                self._header.profile = profile

    # ─── Actions ────────────────────────────────────────────────

    def action_go_home(self) -> None:
        """Navigate to home screen."""
        self.switch_screen("home")

    def action_go_clusters(self) -> None:
        """Navigate to clusters screen."""
        self.switch_screen("clusters")

    def action_go_jobs(self) -> None:
        """Navigate to jobs screen."""
        self.switch_screen("jobs")

    def action_go_pipelines(self) -> None:
        """Navigate to pipelines screen."""
        self.switch_screen("pipelines")

    def action_go_warehouses(self) -> None:
        """Navigate to warehouses screen."""
        self.switch_screen("warehouses")

    def action_go_logs(self) -> None:
        """Navigate to logs screen (if context available)."""
        # Log screen requires a run context - notify if no run selected
        self.notify(
            "Select a run from Jobs screen first, then press 'l' for logs",
            severity="warning",
        )

    def action_go_config(self) -> None:
        """Navigate to config/profiles screen."""
        self.switch_screen("config")

    def action_toggle_armed(self) -> None:
        """Toggle armed mode."""
        if self._guard.is_armed:
            self._guard.disarm()
            self.notify("Disarmed - read-only mode", severity="information")
        else:
            self._guard.arm()
            self.notify(
                f"ARMED for {self._guard.ttl_seconds} seconds - destructive actions enabled",
                severity="warning",
            )

    def action_show_help(self) -> None:
        """Show help overlay."""
        from lazybricks.tui.widgets.help_overlay import HelpOverlay
        self.push_screen(HelpOverlay())

    def action_back(self) -> None:
        """Go back / close current modal.

        Only pops modal screens (like help overlay), never main screens.
        """
        from textual.screen import ModalScreen

        # Only pop if current screen is a modal
        if isinstance(self.screen, ModalScreen):
            self.pop_screen()

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def __getattr__(self, name: str) -> Any:
        """Handle dynamic action methods for extensions.

        Allows extension navigation like action_go_billing without
        explicitly defining each method.
        """
        if name.startswith("action_go_"):
            ext_name = name[len("action_go_"):]
            # Check if this is an extension
            if any(ext.info.name == ext_name for ext in self._extensions):
                return lambda: self.switch_screen(ext_name)

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Check if an action is valid, including dynamic extension actions."""
        # Handle extension navigation actions
        if action.startswith("go_"):
            ext_name = action[3:]
            if any(ext.info.name == ext_name for ext in self._extensions):
                return True

        # Defer to parent for all other actions
        return super().check_action(action, parameters)


def run_tui(client: DatabricksClient) -> None:
    """Entry point to run the TUI."""
    app = LazyBricksApp(client)
    app.run()
