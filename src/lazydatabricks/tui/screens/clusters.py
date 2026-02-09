"""Clusters screen — list and manage compute clusters.

Shows all clusters with:
- Name, State, Workers, Runtime, Idle time, Flags
- Detail panel with cluster info + events
- Actions: start, terminate, restart
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Static
from textual import work

from lazydatabricks.models.cluster import ClusterSummary, ClusterState
from lazydatabricks.tui.screens.base import BaseScreen
from lazydatabricks.tui.widgets.footer_bar import HintItem


class ClustersScreen(BaseScreen):
    """Clusters management screen."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("s", "start_cluster", "Start"),
        ("t", "terminate_cluster", "Terminate"),
        ("R", "restart_cluster", "Restart"),
        ("l", "view_logs", "Logs"),
        ("enter", "select_cluster", "Select"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._clusters: list[ClusterSummary] = []
        self._selected_cluster: ClusterSummary | None = None

    def get_context_actions(self) -> list[HintItem]:
        """Cluster screen context actions - varies by selection state."""
        actions = [
            HintItem("r", "Refresh"),
            HintItem("Enter", "Open"),
        ]

        if self._selected_cluster:
            if self._selected_cluster.state == ClusterState.TERMINATED:
                actions.append(HintItem("s", "Start", destructive=True))
            elif self._selected_cluster.state == ClusterState.RUNNING:
                actions.append(HintItem("t", "Terminate", destructive=True))
                actions.append(HintItem("R", "Restart", destructive=True))

        return actions

    def compose(self) -> ComposeResult:
        yield Container(
            Horizontal(
                Vertical(
                    Static("[bold #e94560]Clusters[/]", id="clusters-title"),
                    DataTable(id="clusters-table"),
                    id="clusters-list",
                ),
                Vertical(
                    Static("", id="cluster-detail"),
                    id="detail-panel",
                ),
            ),
            id="screen-content",
        )

    def on_mount(self) -> None:
        """Initialize the screen."""
        super().on_mount()

        # Set up the table
        table = self.query_one("#clusters-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Name", "State", "Workers", "Runtime", "Idle", "Flags")

        self._refresh_data()

    def _refresh_data(self) -> None:
        """Trigger background data refresh."""
        self._load_clusters()

    @work(thread=True, exclusive=True)
    def _load_clusters(self) -> None:
        """Load clusters in background."""
        try:
            clusters = self.lazydatabricks_app.cluster_ops.list_all()
            self.app.call_from_thread(self._update_table, clusters)
        except Exception as e:
            self.app.call_from_thread(self.notify_error, f"Failed to load clusters: {e}")

    def _update_table(self, clusters: list[ClusterSummary]) -> None:
        """Update the clusters table."""
        self._clusters = clusters
        table = self.query_one("#clusters-table", DataTable)
        table.clear()

        for cluster in clusters:
            state_style = self._get_state_style(cluster.state)
            flags = ", ".join(f.value for f in cluster.flags) if cluster.flags else ""

            table.add_row(
                cluster.name[:35],
                f"[{state_style}]{cluster.state.value}[/]",
                cluster.workers_display,
                cluster.runtime_display,
                cluster.idle_time_display,
                flags,
                key=cluster.id,
            )

        # Select first row if available
        if clusters:
            table.move_cursor(row=0)
            self._update_detail(clusters[0])

    def _get_state_style(self, state: ClusterState) -> str:
        """Get style for cluster state."""
        return {
            ClusterState.RUNNING: "green",
            ClusterState.TERMINATED: "dim",
            ClusterState.PENDING: "yellow",
            ClusterState.RESTARTING: "yellow",
            ClusterState.RESIZING: "yellow",
            ClusterState.TERMINATING: "yellow dim",
            ClusterState.ERROR: "red bold",
        }.get(state, "white")

    def _update_detail(self, cluster: ClusterSummary) -> None:
        """Update the detail panel."""
        self._selected_cluster = cluster
        detail = self.query_one("#cluster-detail", Static)

        lines = [
            f"[bold #e94560]{cluster.name}[/]",
            "",
            f"[dim]ID:[/]        {cluster.id}",
            f"[dim]State:[/]     [{self._get_state_style(cluster.state)}]{cluster.state.value}[/]",
            f"[dim]Workers:[/]   {cluster.workers_display}",
            f"[dim]Runtime:[/]   {cluster.runtime_display}",
            f"[dim]Idle:[/]      {cluster.idle_time_display}",
            f"[dim]Node Type:[/] {cluster.node_type_id}",
            f"[dim]Spark:[/]     {cluster.spark_version}",
            f"[dim]Creator:[/]   {cluster.creator}",
        ]

        if cluster.flags:
            lines.append("")
            lines.append("[dim]Flags:[/]")
            for flag in cluster.flags:
                lines.append(f"  [yellow]• {flag.value}[/]")

        if cluster.state_message:
            lines.append("")
            lines.append(f"[dim]Message:[/] {cluster.state_message}")

        detail.update("\n".join(lines))

        # Update footer with context-aware actions
        self._update_footer()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection."""
        if event.row_key and event.row_key.value:
            cluster = next((c for c in self._clusters if c.id == event.row_key.value), None)
            if cluster:
                self._update_detail(cluster)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlight (cursor move)."""
        if event.row_key and event.row_key.value:
            cluster = next((c for c in self._clusters if c.id == event.row_key.value), None)
            if cluster:
                self._update_detail(cluster)

    def action_refresh(self) -> None:
        """Refresh clusters list."""
        self.notify_success("Refreshing clusters...")
        self._refresh_data()

    def action_select_cluster(self) -> None:
        """Select current cluster (opens in browser)."""
        if self._selected_cluster and self._selected_cluster.ui_url:
            import webbrowser
            webbrowser.open(self._selected_cluster.ui_url)

    def action_start_cluster(self) -> None:
        """Start the selected cluster."""
        if not self._selected_cluster:
            return

        if self._selected_cluster.state != ClusterState.TERMINATED:
            self.notify_warning("Can only start terminated clusters")
            return

        if not self.require_armed("starting cluster"):
            return

        self._do_start_cluster(self._selected_cluster.id)

    @work(thread=True)
    def _do_start_cluster(self, cluster_id: str) -> None:
        """Start cluster in background."""
        # Temporarily disable read-only for this operation
        self.lazydatabricks_app.client.config.read_only = False
        try:
            result = self.lazydatabricks_app.cluster_ops.start(cluster_id)
            if result.get("status") == "started":
                self.app.call_from_thread(self.notify_success, "Cluster start requested")
                self.app.call_from_thread(self._refresh_data)
            else:
                self.app.call_from_thread(self.notify_error, result.get("error", "Failed to start"))
        finally:
            self.lazydatabricks_app.client.config.read_only = True

    def action_terminate_cluster(self) -> None:
        """Terminate the selected cluster."""
        if not self._selected_cluster:
            return

        if self._selected_cluster.state == ClusterState.TERMINATED:
            self.notify_warning("Cluster is already terminated")
            return

        if not self.require_armed("terminating cluster"):
            return

        self._do_terminate_cluster(self._selected_cluster.id)

    @work(thread=True)
    def _do_terminate_cluster(self, cluster_id: str) -> None:
        """Terminate cluster in background."""
        self.lazydatabricks_app.client.config.read_only = False
        try:
            result = self.lazydatabricks_app.cluster_ops.terminate(cluster_id)
            if result.get("status") == "terminated":
                self.app.call_from_thread(self.notify_success, "Cluster termination requested")
                self.app.call_from_thread(self._refresh_data)
            else:
                self.app.call_from_thread(self.notify_error, result.get("error", "Failed to terminate"))
        finally:
            self.lazydatabricks_app.client.config.read_only = True

    def action_restart_cluster(self) -> None:
        """Restart the selected cluster."""
        if not self._selected_cluster:
            return

        if self._selected_cluster.state != ClusterState.RUNNING:
            self.notify_warning("Can only restart running clusters")
            return

        if not self.require_armed("restarting cluster"):
            return

        self._do_restart_cluster(self._selected_cluster.id)

    @work(thread=True)
    def _do_restart_cluster(self, cluster_id: str) -> None:
        """Restart cluster in background."""
        self.lazydatabricks_app.client.config.read_only = False
        try:
            result = self.lazydatabricks_app.cluster_ops.restart(cluster_id)
            if result.get("status") == "restarting":
                self.app.call_from_thread(self.notify_success, "Cluster restart requested")
                self.app.call_from_thread(self._refresh_data)
            else:
                self.app.call_from_thread(self.notify_error, result.get("error", "Failed to restart"))
        finally:
            self.lazydatabricks_app.client.config.read_only = True

    def action_view_logs(self) -> None:
        """View cluster logs (opens in browser as fallback)."""
        if self._selected_cluster and self._selected_cluster.ui_url:
            import webbrowser
            url = self._selected_cluster.ui_url.replace("/configuration", "/driverLogs")
            webbrowser.open(url)
