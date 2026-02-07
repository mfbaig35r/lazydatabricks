"""Pipelines screen — three-pane hierarchy for Pipelines → Updates → Detail.

Navigation:
- Tab moves between panes
- Enter drills down
- Esc backs up
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Static
from textual import work

from lazybricks.models.pipeline import PipelineSummary, UpdateSummary, UpdateState
from lazybricks.tui.screens.base import BaseScreen
from lazybricks.tui.widgets.footer_bar import HintItem


class PipelinesScreen(BaseScreen):
    """Pipelines management screen with three-pane layout."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("tab", "next_pane", "Next Pane"),
        ("shift+tab", "prev_pane", "Prev Pane"),
        ("enter", "drill_down", "Select"),
        ("escape", "back_up", "Back"),
        ("s", "start_update", "Start"),
        ("S", "stop_pipeline", "Stop"),
        ("f", "full_refresh", "Full Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._pipelines: list[PipelineSummary] = []
        self._updates: list[UpdateSummary] = []
        self._selected_pipeline: PipelineSummary | None = None
        self._selected_update: UpdateSummary | None = None
        self._current_pane = 0  # 0=pipelines, 1=updates, 2=detail

    def get_context_actions(self) -> list[HintItem]:
        """Pipelines screen context actions - varies by pane and selection."""
        actions = [
            HintItem("r", "Refresh"),
            HintItem("Tab", "Pane"),
        ]

        if self._current_pane == 0:
            # Pipelines pane
            actions.append(HintItem("Enter", "Updates"))
            if self._selected_pipeline:
                if self._selected_pipeline.state.is_active:
                    actions.append(HintItem("S", "Stop", destructive=True))
                else:
                    actions.append(HintItem("s", "Start", destructive=True))
                    actions.append(HintItem("f", "Full Refresh", destructive=True))
        elif self._current_pane == 1:
            # Updates pane
            actions.append(HintItem("Enter", "Detail"))
            actions.append(HintItem("Esc", "Back"))
            if self._selected_pipeline:
                if self._selected_pipeline.state.is_active:
                    actions.append(HintItem("S", "Stop", destructive=True))
                else:
                    actions.append(HintItem("s", "Start", destructive=True))
        else:
            # Detail pane
            actions.append(HintItem("Esc", "Back"))

        return actions

    def compose(self) -> ComposeResult:
        yield Container(
            Horizontal(
                Vertical(
                    Static("[bold #e94560]Pipelines[/]", id="pipelines-title"),
                    DataTable(id="pipelines-table"),
                    id="pane-pipelines",
                    classes="pane-active",
                ),
                Vertical(
                    Static("[dim]Updates[/]", id="updates-title"),
                    DataTable(id="updates-table"),
                    id="pane-updates",
                    classes="pane-inactive",
                ),
                Vertical(
                    Static("[dim]Detail[/]", id="detail-title"),
                    Static("", id="update-detail"),
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
        pipelines_table = self.query_one("#pipelines-table", DataTable)
        pipelines_table.cursor_type = "row"
        pipelines_table.add_columns("Name", "State", "Target", "Last Update")

        updates_table = self.query_one("#updates-table", DataTable)
        updates_table.cursor_type = "row"
        updates_table.add_columns("Update ID", "Started", "Duration", "State")

        self._refresh_data()

    def _refresh_data(self) -> None:
        """Refresh pipelines list."""
        self._load_pipelines()

    @work(thread=True, exclusive=True)
    def _load_pipelines(self) -> None:
        """Load pipelines in background."""
        try:
            pipelines = self.lazybricks_app.pipeline_ops.list_pipelines(limit=100)
            self.app.call_from_thread(self._update_pipelines_table, pipelines)
        except Exception as e:
            self.app.call_from_thread(self.notify_error, f"Failed to load pipelines: {e}")

    def _update_pipelines_table(self, pipelines: list[PipelineSummary]) -> None:
        """Update the pipelines table."""
        self._pipelines = pipelines
        table = self.query_one("#pipelines-table", DataTable)
        table.clear()

        for pipeline in pipelines:
            health_style = self._get_health_style(pipeline)
            state_style = pipeline.state.display_style
            last_update = "—"
            if pipeline.last_update_time:
                last_update = pipeline.last_update_time.strftime("%m/%d %H:%M")

            table.add_row(
                pipeline.name[:40],
                f"[{state_style}]{pipeline.state_display}[/]",
                pipeline.target_display[:20],
                f"[{health_style}]{last_update}[/]",
                key=pipeline.pipeline_id,
            )

        if pipelines:
            table.move_cursor(row=0)
            self._select_pipeline(pipelines[0])

    def _get_health_style(self, pipeline: PipelineSummary) -> str:
        """Get style for pipeline health indicator."""
        if pipeline.health_display == "✓":
            return "green"
        elif pipeline.health_display == "✗":
            return "red"
        elif pipeline.health_display == "●":
            return "yellow"
        return "dim"

    def _select_pipeline(self, pipeline: PipelineSummary) -> None:
        """Select a pipeline and load its updates."""
        self._selected_pipeline = pipeline
        self._load_updates(pipeline.pipeline_id)

    @work(thread=True)
    def _load_updates(self, pipeline_id: str) -> None:
        """Load updates for a pipeline."""
        try:
            updates = self.lazybricks_app.pipeline_ops.list_updates(
                pipeline_id=pipeline_id, limit=25
            )
            self.app.call_from_thread(self._update_updates_table, updates)
        except Exception as e:
            self.app.call_from_thread(self.notify_error, f"Failed to load updates: {e}")

    def _update_updates_table(self, updates: list[UpdateSummary]) -> None:
        """Update the updates table."""
        self._updates = updates
        table = self.query_one("#updates-table", DataTable)
        table.clear()

        for update in updates:
            result_style = self._get_result_style(update)
            started = update.start_time.strftime("%m/%d %H:%M") if update.start_time else "—"

            # Truncate update ID for display
            update_id_short = update.update_id[:12] if update.update_id else "—"

            table.add_row(
                update_id_short,
                started,
                update.duration_display,
                f"[{result_style}]{update.state_display}[/]",
                key=update.update_id,
            )

        if updates:
            table.move_cursor(row=0)
            self._select_update(updates[0])

    def _get_result_style(self, update: UpdateSummary) -> str:
        """Get style for update result."""
        if update.state == UpdateState.COMPLETED:
            return "green"
        elif update.state.is_failure:
            return "red bold"
        elif update.state.is_active:
            return "yellow"
        elif update.state == UpdateState.CANCELED:
            return "yellow dim"
        return "dim"

    def _select_update(self, update: UpdateSummary) -> None:
        """Select an update and show detail."""
        self._selected_update = update
        self._update_detail(update)

    def _update_detail(self, update: UpdateSummary) -> None:
        """Update the detail panel."""
        detail = self.query_one("#update-detail", Static)

        result_style = self._get_result_style(update)
        started = update.start_time.strftime("%Y-%m-%d %H:%M:%S") if update.start_time else "—"
        created = update.creation_time.strftime("%Y-%m-%d %H:%M:%S") if update.creation_time else "—"

        lines = [
            f"[bold #e94560]Update {update.update_id[:16]}...[/]",
            "",
            f"[dim]Pipeline:[/]  {update.pipeline_id[:20]}...",
            f"[dim]State:[/]     [{result_style}]{update.state.value}[/]",
            f"[dim]Cause:[/]     {update.cause.value}",
            f"[dim]Created:[/]   {created}",
            f"[dim]Started:[/]   {started}",
            f"[dim]Duration:[/]  {update.duration_display}",
        ]

        if update.full_refresh:
            lines.append("[dim]Mode:[/]      [yellow]FULL REFRESH[/]")
            if update.full_refresh_selection:
                lines.append(f"[dim]Tables:[/]    {', '.join(update.full_refresh_selection[:3])}")

        if update.cluster_id:
            lines.append(f"[dim]Cluster:[/]   {update.cluster_id}")

        detail.update("\n".join(lines))

        # Update footer with context-aware actions
        self._update_footer()

    def _update_pane_styles(self) -> None:
        """Update visual style of panes based on focus."""
        panes = ["#pane-pipelines", "#pane-updates", "#pane-detail"]
        titles = ["#pipelines-title", "#updates-title", "#detail-title"]
        title_text = ["Pipelines", "Updates", "Detail"]

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

        if table.id == "pipelines-table" and event.row_key and event.row_key.value:
            pipeline = next(
                (p for p in self._pipelines if p.pipeline_id == event.row_key.value),
                None,
            )
            if pipeline:
                self._select_pipeline(pipeline)
        elif table.id == "updates-table" and event.row_key and event.row_key.value:
            update = next(
                (u for u in self._updates if u.update_id == event.row_key.value),
                None,
            )
            if update:
                self._select_update(update)

    def action_refresh(self) -> None:
        """Refresh data."""
        self.notify_success("Refreshing pipelines...")
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
            self.query_one("#pipelines-table", DataTable).focus()
        elif self._current_pane == 1:
            self.query_one("#updates-table", DataTable).focus()
        # Pane 2 is detail, no focusable element

    def action_drill_down(self) -> None:
        """Drill down into selection."""
        if self._current_pane == 0 and self._selected_pipeline:
            self._current_pane = 1
            self._update_pane_styles()
            self._focus_current_pane()
        elif self._current_pane == 1 and self._selected_update:
            self._current_pane = 2
            self._update_pane_styles()

    def action_back_up(self) -> None:
        """Back up in hierarchy.

        Always consumes the escape key to prevent app-level pop.
        """
        if self._current_pane > 0:
            self._current_pane -= 1
            self._update_pane_styles()
            self._focus_current_pane()
            self._update_footer()
        # Don't propagate to app level even when at pane 0

    def action_start_update(self) -> None:
        """Start pipeline update."""
        if not self._selected_pipeline:
            return

        if self._selected_pipeline.state.is_active:
            self.notify_warning("Pipeline is already running")
            return

        if not self.require_armed("starting pipeline update"):
            return

        self._do_start_update(self._selected_pipeline.pipeline_id, full_refresh=False)

    def action_full_refresh(self) -> None:
        """Start pipeline with full refresh."""
        if not self._selected_pipeline:
            return

        if self._selected_pipeline.state.is_active:
            self.notify_warning("Pipeline is already running")
            return

        if not self.require_armed("starting full refresh"):
            return

        self._do_start_update(self._selected_pipeline.pipeline_id, full_refresh=True)

    @work(thread=True)
    def _do_start_update(self, pipeline_id: str, full_refresh: bool = False) -> None:
        """Start pipeline in background."""
        self.lazybricks_app.client.config.read_only = False
        try:
            result = self.lazybricks_app.pipeline_ops.start_update(
                pipeline_id, full_refresh=full_refresh
            )
            if result.get("status") == "started":
                msg = "Full refresh" if full_refresh else "Update"
                self.app.call_from_thread(
                    self.notify_success,
                    f"{msg} started - update {result.get('update_id', '')[:12]}",
                )
                self.app.call_from_thread(self._refresh_data)
            else:
                self.app.call_from_thread(
                    self.notify_error, result.get("error", "Failed to start")
                )
        finally:
            self.lazybricks_app.client.config.read_only = True

    def action_stop_pipeline(self) -> None:
        """Stop the selected pipeline."""
        if not self._selected_pipeline:
            return

        if not self._selected_pipeline.state.is_active:
            self.notify_warning("Pipeline is not running")
            return

        if not self.require_armed("stopping pipeline"):
            return

        self._do_stop_pipeline(self._selected_pipeline.pipeline_id)

    @work(thread=True)
    def _do_stop_pipeline(self, pipeline_id: str) -> None:
        """Stop pipeline in background."""
        self.lazybricks_app.client.config.read_only = False
        try:
            result = self.lazybricks_app.pipeline_ops.stop(pipeline_id)
            if result.get("status") == "stopped":
                self.app.call_from_thread(self.notify_success, "Pipeline stop requested")
                self.app.call_from_thread(self._refresh_data)
            else:
                self.app.call_from_thread(
                    self.notify_error, result.get("error", "Failed to stop")
                )
        finally:
            self.lazybricks_app.client.config.read_only = True
