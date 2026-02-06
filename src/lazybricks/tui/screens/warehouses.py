"""Warehouses screen — SQL warehouse management.

Simple table with start/stop actions.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Static
from textual import work

from lazybricks.models.warehouse import WarehouseSummary, WarehouseState
from lazybricks.tui.screens.base import BaseScreen
from lazybricks.tui.widgets.status_bar import WAREHOUSES_BINDINGS


class WarehousesScreen(BaseScreen):
    """SQL Warehouses management screen."""

    SCREEN_BINDINGS = WAREHOUSES_BINDINGS

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("s", "start_warehouse", "Start"),
        ("S", "stop_warehouse", "Stop"),
        ("enter", "open_warehouse", "Open"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._warehouses: list[WarehouseSummary] = []
        self._selected_warehouse: WarehouseSummary | None = None

    def compose(self) -> ComposeResult:
        yield Container(
            Horizontal(
                Vertical(
                    Static("[bold #e94560]SQL Warehouses[/]", id="warehouses-title"),
                    DataTable(id="warehouses-table"),
                    id="warehouses-list",
                ),
                Vertical(
                    Static("", id="warehouse-detail"),
                    id="detail-panel",
                ),
            ),
            id="screen-content",
        )

    def on_mount(self) -> None:
        """Initialize the screen."""
        super().on_mount()

        table = self.query_one("#warehouses-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Name", "State", "Size", "Type", "Sessions")

        self._refresh_data()

    def _refresh_data(self) -> None:
        """Refresh warehouses list."""
        self._load_warehouses()

    @work(thread=True, exclusive=True)
    def _load_warehouses(self) -> None:
        """Load warehouses in background."""
        try:
            warehouses = self.lazybricks_app.warehouse_ops.list_all()
            self.call_from_thread(self._update_table, warehouses)
        except Exception as e:
            self.call_from_thread(self.notify_error, f"Failed to load warehouses: {e}")

    def _update_table(self, warehouses: list[WarehouseSummary]) -> None:
        """Update the warehouses table."""
        self._warehouses = warehouses
        table = self.query_one("#warehouses-table", DataTable)
        table.clear()

        for wh in warehouses:
            state_style = self._get_state_style(wh.state)

            table.add_row(
                wh.name[:30],
                f"[{state_style}]{wh.state.value}[/]",
                wh.size_display[:20],
                wh.type_display,
                str(wh.num_active_sessions),
                key=wh.id,
            )

        if warehouses:
            table.move_cursor(row=0)
            self._update_detail(warehouses[0])

    def _get_state_style(self, state: WarehouseState) -> str:
        """Get style for warehouse state."""
        return {
            WarehouseState.RUNNING: "green",
            WarehouseState.STOPPED: "dim",
            WarehouseState.STARTING: "yellow",
            WarehouseState.STOPPING: "yellow dim",
            WarehouseState.DELETED: "red dim",
        }.get(state, "white")

    def _update_detail(self, warehouse: WarehouseSummary) -> None:
        """Update the detail panel."""
        self._selected_warehouse = warehouse
        detail = self.query_one("#warehouse-detail", Static)

        lines = [
            f"[bold #e94560]{warehouse.name}[/]",
            "",
            f"[dim]ID:[/]        {warehouse.id}",
            f"[dim]State:[/]     [{self._get_state_style(warehouse.state)}]{warehouse.state.value}[/]",
            f"[dim]Size:[/]      {warehouse.size_display}",
            f"[dim]Type:[/]      {warehouse.type_display}",
            f"[dim]Sessions:[/]  {warehouse.num_active_sessions}",
            f"[dim]Clusters:[/]  {warehouse.num_clusters}",
            f"[dim]Auto-stop:[/] {warehouse.auto_stop_mins}m" if warehouse.auto_stop_mins else "[dim]Auto-stop:[/] disabled",
            f"[dim]Creator:[/]   {warehouse.creator}",
        ]

        detail.update("\n".join(lines))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlight."""
        if event.row_key and event.row_key.value:
            warehouse = next((w for w in self._warehouses if w.id == event.row_key.value), None)
            if warehouse:
                self._update_detail(warehouse)

    def action_refresh(self) -> None:
        """Refresh warehouses list."""
        self.notify_success("Refreshing warehouses...")
        self._refresh_data()

    def action_open_warehouse(self) -> None:
        """Open warehouse in browser."""
        if self._selected_warehouse and self._selected_warehouse.ui_url:
            import webbrowser
            webbrowser.open(self._selected_warehouse.ui_url)

    def action_start_warehouse(self) -> None:
        """Start the selected warehouse."""
        if not self._selected_warehouse:
            return

        if self._selected_warehouse.state != WarehouseState.STOPPED:
            self.notify_warning("Can only start stopped warehouses")
            return

        if not self.require_armed("starting warehouse"):
            return

        self._do_start_warehouse(self._selected_warehouse.id)

    @work(thread=True)
    def _do_start_warehouse(self, warehouse_id: str) -> None:
        """Start warehouse in background."""
        self.lazybricks_app.client.config.read_only = False
        try:
            result = self.lazybricks_app.warehouse_ops.start(warehouse_id)
            if result.get("status") == "started":
                self.call_from_thread(self.notify_success, "Warehouse start requested")
                self.call_from_thread(self._refresh_data)
            else:
                self.call_from_thread(self.notify_error, result.get("error", "Failed to start"))
        finally:
            self.lazybricks_app.client.config.read_only = True

    def action_stop_warehouse(self) -> None:
        """Stop the selected warehouse."""
        if not self._selected_warehouse:
            return

        if self._selected_warehouse.state != WarehouseState.RUNNING:
            self.notify_warning("Can only stop running warehouses")
            return

        if not self.require_armed("stopping warehouse"):
            return

        self._do_stop_warehouse(self._selected_warehouse.id)

    @work(thread=True)
    def _do_stop_warehouse(self, warehouse_id: str) -> None:
        """Stop warehouse in background."""
        self.lazybricks_app.client.config.read_only = False
        try:
            result = self.lazybricks_app.warehouse_ops.stop(warehouse_id)
            if result.get("status") == "stopped":
                self.call_from_thread(self.notify_success, "Warehouse stop requested")
                self.call_from_thread(self._refresh_data)
            else:
                self.call_from_thread(self.notify_error, result.get("error", "Failed to stop"))
        finally:
            self.lazybricks_app.client.config.read_only = True
