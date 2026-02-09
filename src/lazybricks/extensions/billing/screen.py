"""Billing screen — three-pane cost visibility for DBU usage.

Layout:
- Left pane: Top SKUs by estimated cost
- Middle pane: Breakdown by compute target
- Right pane: Usage detail
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Static
from textual import work

from lazybricks.extensions.billing.models import (
    GroupBy,
    SkuCostSummary,
    TimeWindow,
    UsageBreakdown,
)
from lazybricks.tui.screens.base import BaseScreen
from lazybricks.tui.widgets.footer_bar import HintItem


class BillingScreen(BaseScreen):
    """Billing/Cost visibility screen with three-pane layout."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("tab", "next_pane", "Next Pane"),
        ("shift+tab", "prev_pane", "Prev Pane"),
        ("enter", "drill_down", "Select"),
        ("escape", "back_up", "Back"),
        ("t", "cycle_time_window", "Time Window"),
        ("g", "cycle_grouping", "Group By"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._sku_costs: list[SkuCostSummary] = []
        self._breakdowns: list[UsageBreakdown] = []
        self._selected_sku: SkuCostSummary | None = None
        self._selected_breakdown: UsageBreakdown | None = None
        self._current_pane = 0  # 0=skus, 1=breakdown, 2=detail
        self._time_window = TimeWindow.DAY_7
        self._group_by = GroupBy.CLUSTER
        self._access_ok: bool | None = None  # None = not checked yet
        self._access_error = ""

    def get_context_actions(self) -> list[HintItem]:
        """Billing screen context actions."""
        actions = [
            HintItem("r", "Refresh"),
            HintItem("Tab", "Pane"),
            HintItem("t", self._time_window.value),
        ]

        if self._current_pane == 0:
            actions.append(HintItem("Enter", "Breakdown"))
        elif self._current_pane == 1:
            actions.append(HintItem("Enter", "Navigate"))
            actions.append(HintItem("Esc", "Back"))
            actions.append(HintItem("g", self._group_by.display))
        else:
            actions.append(HintItem("Esc", "Back"))

        return actions

    def compose(self) -> ComposeResult:
        yield Container(
            Horizontal(
                Vertical(
                    Static("[bold #e94560]SKU Costs[/]", id="sku-title"),
                    Static(
                        f"[dim]{self._time_window.display} • Data delayed ~24h[/]",
                        id="sku-subtitle",
                    ),
                    DataTable(id="sku-table"),
                    id="pane-sku",
                    classes="pane-active",
                ),
                Vertical(
                    Static("[dim]Breakdown[/]", id="breakdown-title"),
                    DataTable(id="breakdown-table"),
                    id="pane-breakdown",
                    classes="pane-inactive",
                ),
                Vertical(
                    Static("[dim]Detail[/]", id="detail-title"),
                    Static("", id="usage-detail"),
                    id="pane-detail",
                    classes="pane-inactive",
                ),
            ),
            id="screen-content",
        )

    def on_mount(self) -> None:
        """Initialize the screen."""
        super().on_mount()

        # Set up tables
        sku_table = self.query_one("#sku-table", DataTable)
        sku_table.cursor_type = "row"
        sku_table.add_columns("SKU", "Type", "DBUs", "Cost")

        breakdown_table = self.query_one("#breakdown-table", DataTable)
        breakdown_table.cursor_type = "row"
        breakdown_table.add_columns("Resource", "Workspace", "DBUs", "Cost")

        self._check_access_and_load()

    @work(thread=True, exclusive=True)
    def _check_access_and_load(self) -> None:
        """Check billing access then load data."""
        try:
            billing_ops = self.lazybricks_app.get_extension_ops("billing")
            if not billing_ops:
                self.app.call_from_thread(self._show_not_configured)
                return

            ok, error = billing_ops.check_access()
            if not ok:
                self.app.call_from_thread(self._show_access_error, error)
                return

            self._access_ok = True
            self.app.call_from_thread(self._load_sku_costs)
        except Exception as e:
            self.app.call_from_thread(self._show_access_error, str(e))

    def _show_not_configured(self) -> None:
        """Show message when billing extension not configured."""
        self._access_ok = False
        self._access_error = "Billing extension not configured"
        detail = self.query_one("#usage-detail", Static)
        detail.update(
            "[yellow]Billing extension not configured.[/]\n\n"
            "Add to ~/.lazybricks/config.toml:\n\n"
            "[extensions]\n"
            'enabled = ["billing"]\n\n'
            "[extensions.billing]\n"
            'sql_warehouse_id = "your-warehouse-id"'
        )

    def _show_access_error(self, error: str) -> None:
        """Show access error message."""
        self._access_ok = False
        self._access_error = error
        detail = self.query_one("#usage-detail", Static)
        detail.update(
            f"[red]Cannot access billing data.[/]\n\n"
            f"Error: {error}\n\n"
            "Billing tables require account-level access.\n"
            "Contact your Databricks admin for permissions to:\n"
            "  • system.billing.usage\n"
            "  • system.billing.list_prices"
        )

    def _refresh_data(self) -> None:
        """Refresh billing data."""
        if self._access_ok is False:
            return
        self._load_sku_costs()

    @work(thread=True, exclusive=True)
    def _load_sku_costs(self) -> None:
        """Load SKU costs in background."""
        try:
            billing_ops = self.lazybricks_app.get_extension_ops("billing")
            if not billing_ops:
                return

            costs = billing_ops.list_sku_costs(self._time_window)
            self.app.call_from_thread(self._update_sku_table, costs)
        except Exception as e:
            self.app.call_from_thread(self.notify_error, f"Failed to load billing: {e}")

    def _update_sku_table(self, costs: list[SkuCostSummary]) -> None:
        """Update the SKU costs table."""
        self._sku_costs = costs
        table = self.query_one("#sku-table", DataTable)
        table.clear()

        # Update subtitle with time window
        subtitle = self.query_one("#sku-subtitle", Static)
        subtitle.update(f"[dim]{self._time_window.display} • Data delayed ~24h[/]")

        if not costs:
            # Show empty state in detail panel
            detail = self.query_one("#usage-detail", Static)
            detail.update(
                "[dim]No billing data found for this time window.[/]\n\n"
                "This could mean:\n"
                "  • No DBU usage in the selected period\n"
                "  • Billing data not yet available (24-48h delay)\n"
                "  • Limited access to billing tables"
            )
            return

        for i, sku in enumerate(costs):
            table.add_row(
                sku.sku_name[:30],
                sku.usage_type[:15],
                sku.dbu_display,
                f"[green]{sku.cost_display}[/]",
                key=f"{i}",
            )

        if costs:
            table.move_cursor(row=0)
            self._select_sku(costs[0])

    def _select_sku(self, sku: SkuCostSummary) -> None:
        """Select a SKU and load its breakdown."""
        self._selected_sku = sku
        self._load_breakdown(sku.sku_name, sku.usage_type)

    @work(thread=True)
    def _load_breakdown(self, sku_name: str, usage_type: str) -> None:
        """Load usage breakdown for selected SKU."""
        try:
            billing_ops = self.lazybricks_app.get_extension_ops("billing")
            if not billing_ops:
                return

            breakdowns = billing_ops.get_usage_breakdown(
                sku_name, usage_type, self._time_window
            )
            self.app.call_from_thread(self._update_breakdown_table, breakdowns)
        except Exception as e:
            self.app.call_from_thread(self.notify_error, f"Failed to load breakdown: {e}")

    def _update_breakdown_table(self, breakdowns: list[UsageBreakdown]) -> None:
        """Update the breakdown table."""
        self._breakdowns = breakdowns
        table = self.query_one("#breakdown-table", DataTable)
        table.clear()

        for i, item in enumerate(breakdowns):
            table.add_row(
                item.resource_display,
                item.workspace_id[:12] if item.workspace_id else "—",
                item.dbu_display,
                f"[green]{item.cost_display}[/]",
                key=f"{i}",
            )

        if breakdowns:
            table.move_cursor(row=0)
            self._select_breakdown(breakdowns[0])
        else:
            # Clear detail panel
            detail = self.query_one("#usage-detail", Static)
            detail.update("[dim]No breakdown data for this SKU.[/]")

    def _select_breakdown(self, breakdown: UsageBreakdown) -> None:
        """Select a breakdown item and show detail."""
        self._selected_breakdown = breakdown
        self._update_detail(breakdown)

    def _update_detail(self, breakdown: UsageBreakdown) -> None:
        """Update the detail panel."""
        detail = self.query_one("#usage-detail", Static)

        lines = [
            "[bold #e94560]Usage Detail[/]",
            "",
            f"[dim]Workspace:[/]  {breakdown.workspace_id}",
        ]

        if breakdown.cluster_id:
            lines.append(f"[dim]Cluster:[/]    {breakdown.cluster_id}")
        if breakdown.warehouse_id:
            lines.append(f"[dim]Warehouse:[/]  {breakdown.warehouse_id}")
        if breakdown.job_id:
            lines.append(f"[dim]Job ID:[/]     {breakdown.job_id}")
        if breakdown.job_run_id:
            lines.append(f"[dim]Run ID:[/]     {breakdown.job_run_id}")

        lines.extend([
            "",
            f"[dim]Total DBUs:[/] {breakdown.total_dbu:,.2f}",
            f"[dim]Unit Price:[/] ${breakdown.unit_price_effective:.4f}",
            f"[dim]Est. Cost:[/]  [green]{breakdown.cost_display}[/]",
        ])

        if breakdown.creator:
            lines.append(f"[dim]Creator:[/]    {breakdown.creator}")
        if breakdown.resource_class:
            lines.append(f"[dim]Class:[/]      {breakdown.resource_class}")

        # Navigation hint
        if breakdown.resource_type:
            lines.extend([
                "",
                f"[dim]Press Enter to navigate to {breakdown.resource_type}s[/]",
            ])

        detail.update("\n".join(lines))
        self._update_footer()

    def _update_pane_styles(self) -> None:
        """Update visual style of panes based on focus."""
        panes = ["#pane-sku", "#pane-breakdown", "#pane-detail"]
        titles = ["#sku-title", "#breakdown-title", "#detail-title"]
        title_text = ["SKU Costs", "Breakdown", "Detail"]

        for i, (pane_id, title_id, text) in enumerate(zip(panes, titles, title_text)):
            pane = self.query_one(pane_id, Vertical)
            title = self.query_one(title_id, Static)

            if i == self._current_pane:
                pane.remove_class("pane-inactive")
                pane.add_class("pane-active")
                title.update(f"[bold #e94560]{text}[/]")
            else:
                pane.remove_class("pane-active")
                pane.add_class("pane-inactive")
                title.update(f"[dim]{text}[/]")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlight."""
        table = event.data_table

        if table.id == "sku-table" and event.row_key and event.row_key.value:
            # Key is the index into self._sku_costs
            try:
                idx = int(event.row_key.value)
                if 0 <= idx < len(self._sku_costs):
                    self._select_sku(self._sku_costs[idx])
            except (ValueError, IndexError):
                pass
        elif table.id == "breakdown-table" and event.row_key and event.row_key.value:
            # Key is the index into self._breakdowns
            try:
                idx = int(event.row_key.value)
                if 0 <= idx < len(self._breakdowns):
                    self._select_breakdown(self._breakdowns[idx])
            except (ValueError, IndexError):
                pass

    # ─── Actions ────────────────────────────────────────────────

    def action_refresh(self) -> None:
        """Refresh data."""
        self.notify_success("Refreshing billing data...")
        self._refresh_data()

    def action_next_pane(self) -> None:
        """Move to next pane."""
        self._current_pane = (self._current_pane + 1) % 3
        self._update_pane_styles()
        self._focus_current_pane()
        self._update_footer()

    def action_prev_pane(self) -> None:
        """Move to previous pane."""
        self._current_pane = (self._current_pane - 1) % 3
        self._update_pane_styles()
        self._focus_current_pane()
        self._update_footer()

    def _focus_current_pane(self) -> None:
        """Focus the current pane's table."""
        if self._current_pane == 0:
            self.query_one("#sku-table", DataTable).focus()
        elif self._current_pane == 1:
            self.query_one("#breakdown-table", DataTable).focus()
        # Pane 2 is detail, no focusable element

    def action_drill_down(self) -> None:
        """Drill down or navigate to resource."""
        if self._current_pane == 0 and self._selected_sku:
            self._current_pane = 1
            self._update_pane_styles()
            self._focus_current_pane()
        elif self._current_pane == 1 and self._selected_breakdown:
            # Navigate to the resource's screen
            self._navigate_to_resource()
        elif self._current_pane == 1:
            self._current_pane = 2
            self._update_pane_styles()

    def _navigate_to_resource(self) -> None:
        """Navigate to the resource's screen."""
        if not self._selected_breakdown:
            return

        b = self._selected_breakdown

        if b.cluster_id:
            self.lazybricks_app.switch_screen("clusters")
            self.notify_success(f"Clusters (cluster: {b.cluster_id[:12]}...)")
        elif b.warehouse_id:
            self.lazybricks_app.switch_screen("warehouses")
            self.notify_success(f"Warehouses (warehouse: {b.warehouse_id[:12]}...)")
        elif b.job_id:
            self.lazybricks_app.switch_screen("jobs")
            self.notify_success(f"Jobs (job: {b.job_id})")
        else:
            self.notify_warning("No resource to navigate to")

    def action_back_up(self) -> None:
        """Back up in hierarchy."""
        if self._current_pane > 0:
            self._current_pane -= 1
            self._update_pane_styles()
            self._focus_current_pane()
            self._update_footer()

    def action_cycle_time_window(self) -> None:
        """Cycle through time windows."""
        self._time_window = self._time_window.next()
        self.notify_success(f"Time window: {self._time_window.display}")
        self._refresh_data()

    def action_cycle_grouping(self) -> None:
        """Cycle through grouping options."""
        self._group_by = self._group_by.next()
        self.notify_success(f"Group by: {self._group_by.display}")
        # Note: Currently grouping is visual only in the breakdown
        # Full re-aggregation would require a modified query
