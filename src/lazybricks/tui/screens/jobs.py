"""Jobs screen — three-pane hierarchy for Jobs → Runs → Detail.

Navigation:
- Tab moves between panes
- Enter drills down
- Esc backs up
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import DataTable, Static
from textual.worker import work

from lazybricks.models.job import JobSummary, RunSummary, RunDetail, RunState, RunResult
from lazybricks.tui.screens.base import BaseScreen
from lazybricks.tui.widgets.status_bar import JOBS_BINDINGS


class JobsScreen(BaseScreen):
    """Jobs management screen with three-pane layout."""

    SCREEN_BINDINGS = JOBS_BINDINGS

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("tab", "next_pane", "Next Pane"),
        ("shift+tab", "prev_pane", "Prev Pane"),
        ("enter", "drill_down", "Select"),
        ("escape", "back_up", "Back"),
        ("n", "run_now", "Run Now"),
        ("c", "cancel_run", "Cancel"),
        ("R", "rerun", "Rerun"),
        ("l", "view_logs", "Logs"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._jobs: list[JobSummary] = []
        self._runs: list[RunSummary] = []
        self._selected_job: JobSummary | None = None
        self._selected_run: RunSummary | None = None
        self._current_pane = 0  # 0=jobs, 1=runs, 2=detail

    def compose(self) -> ComposeResult:
        yield Container(
            Horizontal(
                Vertical(
                    Static("[bold #e94560]Jobs[/]", id="jobs-title"),
                    DataTable(id="jobs-table"),
                    id="pane-jobs",
                    classes="pane-active",
                ),
                Vertical(
                    Static("[dim]Runs[/]", id="runs-title"),
                    DataTable(id="runs-table"),
                    id="pane-runs",
                    classes="pane-inactive",
                ),
                Vertical(
                    Static("[dim]Detail[/]", id="detail-title"),
                    Static("", id="run-detail"),
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
        jobs_table = self.query_one("#jobs-table", DataTable)
        jobs_table.cursor_type = "row"
        jobs_table.add_columns("Name", "Schedule", "Health")

        runs_table = self.query_one("#runs-table", DataTable)
        runs_table.cursor_type = "row"
        runs_table.add_columns("Run ID", "Started", "Duration", "Result")

        self._refresh_data()

    def _refresh_data(self) -> None:
        """Refresh jobs list."""
        self._load_jobs()

    @work(thread=True, exclusive=True)
    def _load_jobs(self) -> None:
        """Load jobs in background."""
        try:
            jobs = self.lazybricks_app.job_ops.list_jobs(limit=100)
            self.call_from_thread(self._update_jobs_table, jobs)
        except Exception as e:
            self.call_from_thread(self.notify_error, f"Failed to load jobs: {e}")

    def _update_jobs_table(self, jobs: list[JobSummary]) -> None:
        """Update the jobs table."""
        self._jobs = jobs
        table = self.query_one("#jobs-table", DataTable)
        table.clear()

        for job in jobs:
            health_style = self._get_health_style(job)
            table.add_row(
                job.name[:40],
                job.schedule_display[:20],
                f"[{health_style}]{job.health_display}[/]",
                key=str(job.id),
            )

        if jobs:
            table.move_cursor(row=0)
            self._select_job(jobs[0])

    def _get_health_style(self, job: JobSummary) -> str:
        """Get style for job health indicator."""
        if job.health_display == "✓":
            return "green"
        elif job.health_display == "✗":
            return "red"
        elif job.health_display == "●":
            return "yellow"
        return "dim"

    def _select_job(self, job: JobSummary) -> None:
        """Select a job and load its runs."""
        self._selected_job = job
        self._load_runs(job.id)

    @work(thread=True)
    def _load_runs(self, job_id: int) -> None:
        """Load runs for a job."""
        try:
            runs = self.lazybricks_app.job_ops.list_runs(job_id=job_id, limit=25)
            self.call_from_thread(self._update_runs_table, runs)
        except Exception as e:
            self.call_from_thread(self.notify_error, f"Failed to load runs: {e}")

    def _update_runs_table(self, runs: list[RunSummary]) -> None:
        """Update the runs table."""
        self._runs = runs
        table = self.query_one("#runs-table", DataTable)
        table.clear()

        for run in runs:
            result_style = self._get_result_style(run)
            started = run.started_at.strftime("%m/%d %H:%M") if run.started_at else "—"

            table.add_row(
                str(run.run_id),
                started,
                run.duration_display,
                f"[{result_style}]{run.result_display}[/]",
                key=str(run.run_id),
            )

        if runs:
            table.move_cursor(row=0)
            self._select_run(runs[0])

    def _get_result_style(self, run: RunSummary) -> str:
        """Get style for run result."""
        if run.result == RunResult.SUCCESS:
            return "green"
        elif run.result and run.result.is_failure:
            return "red bold"
        elif run.state.is_active:
            return "yellow"
        return "dim"

    def _select_run(self, run: RunSummary) -> None:
        """Select a run and show detail."""
        self._selected_run = run
        self._update_detail(run)

    def _update_detail(self, run: RunSummary) -> None:
        """Update the detail panel."""
        detail = self.query_one("#run-detail", Static)

        result_style = self._get_result_style(run)
        started = run.started_at.strftime("%Y-%m-%d %H:%M:%S") if run.started_at else "—"

        lines = [
            f"[bold #e94560]Run {run.run_id}[/]",
            "",
            f"[dim]Job ID:[/]   {run.job_id}",
            f"[dim]State:[/]    [{result_style}]{run.state.value}[/]",
            f"[dim]Result:[/]   [{result_style}]{run.result_display}[/]",
            f"[dim]Started:[/]  {started}",
            f"[dim]Duration:[/] {run.duration_display}",
            f"[dim]Trigger:[/]  {run.trigger.value}",
        ]

        if run.notebook_path:
            lines.append(f"[dim]Notebook:[/] {run.notebook_path}")

        if run.error_snippet:
            lines.append("")
            lines.append("[red]Error:[/]")
            lines.append(f"  {run.error_snippet[:200]}")

        detail.update("\n".join(lines))

    def _update_pane_styles(self) -> None:
        """Update visual style of panes based on focus."""
        panes = ["#pane-jobs", "#pane-runs", "#pane-detail"]
        titles = ["#jobs-title", "#runs-title", "#detail-title"]
        title_text = ["Jobs", "Runs", "Detail"]

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

        if table.id == "jobs-table" and event.row_key and event.row_key.value:
            job = next((j for j in self._jobs if str(j.id) == event.row_key.value), None)
            if job:
                self._select_job(job)
        elif table.id == "runs-table" and event.row_key and event.row_key.value:
            run = next((r for r in self._runs if str(r.run_id) == event.row_key.value), None)
            if run:
                self._select_run(run)

    def action_refresh(self) -> None:
        """Refresh data."""
        self.notify_success("Refreshing jobs...")
        self._refresh_data()

    def action_next_pane(self) -> None:
        """Move to next pane."""
        self._current_pane = (self._current_pane + 1) % 3
        self._update_pane_styles()
        self._focus_current_pane()

    def action_prev_pane(self) -> None:
        """Move to previous pane."""
        self._current_pane = (self._current_pane - 1) % 3
        self._update_pane_styles()
        self._focus_current_pane()

    def _focus_current_pane(self) -> None:
        """Focus the current pane's table."""
        if self._current_pane == 0:
            self.query_one("#jobs-table", DataTable).focus()
        elif self._current_pane == 1:
            self.query_one("#runs-table", DataTable).focus()
        # Pane 2 is detail, no focusable element

    def action_drill_down(self) -> None:
        """Drill down into selection."""
        if self._current_pane == 0 and self._selected_job:
            self._current_pane = 1
            self._update_pane_styles()
            self._focus_current_pane()
        elif self._current_pane == 1 and self._selected_run:
            self._current_pane = 2
            self._update_pane_styles()

    def action_back_up(self) -> None:
        """Back up in hierarchy."""
        if self._current_pane > 0:
            self._current_pane -= 1
            self._update_pane_styles()
            self._focus_current_pane()

    def action_run_now(self) -> None:
        """Trigger job to run immediately."""
        if not self._selected_job:
            return

        if not self.require_armed("triggering job run"):
            return

        self._do_run_now(self._selected_job.id)

    @work(thread=True)
    def _do_run_now(self, job_id: int) -> None:
        """Run job in background."""
        self.lazybricks_app.client.config.read_only = False
        try:
            result = self.lazybricks_app.job_ops.run_now(job_id)
            if result.get("status") == "submitted":
                self.call_from_thread(self.notify_success, f"Job triggered - run {result.get('run_id')}")
                self.call_from_thread(self._refresh_data)
            else:
                self.call_from_thread(self.notify_error, result.get("error", "Failed to trigger"))
        finally:
            self.lazybricks_app.client.config.read_only = True

    def action_cancel_run(self) -> None:
        """Cancel the selected run."""
        if not self._selected_run:
            return

        if not self._selected_run.state.is_active:
            self.notify_warning("Can only cancel active runs")
            return

        if not self.require_armed("canceling run"):
            return

        self._do_cancel_run(self._selected_run.run_id)

    @work(thread=True)
    def _do_cancel_run(self, run_id: int) -> None:
        """Cancel run in background."""
        self.lazybricks_app.client.config.read_only = False
        try:
            result = self.lazybricks_app.job_ops.cancel_run(run_id)
            if result.get("status") == "cancelled":
                self.call_from_thread(self.notify_success, "Run cancellation requested")
                self.call_from_thread(self._refresh_data)
            else:
                self.call_from_thread(self.notify_error, result.get("error", "Failed to cancel"))
        finally:
            self.lazybricks_app.client.config.read_only = True

    def action_rerun(self) -> None:
        """Rerun the selected run."""
        if not self._selected_run:
            return

        if self._selected_run.state.is_active:
            self.notify_warning("Cannot rerun an active run")
            return

        if not self.require_armed("rerunning job"):
            return

        self._do_rerun(self._selected_run.run_id)

    @work(thread=True)
    def _do_rerun(self, run_id: int) -> None:
        """Rerun in background."""
        self.lazybricks_app.client.config.read_only = False
        try:
            result = self.lazybricks_app.job_ops.rerun(run_id)
            if result.get("status") == "rerun_submitted":
                self.call_from_thread(self.notify_success, "Rerun submitted")
                self.call_from_thread(self._refresh_data)
            else:
                self.call_from_thread(self.notify_error, result.get("error", "Failed to rerun"))
        finally:
            self.lazybricks_app.client.config.read_only = True

    def action_view_logs(self) -> None:
        """View logs for selected run."""
        if not self._selected_run:
            self.notify_warning("Select a run first")
            return

        from lazybricks.tui.screens.logs import LogsScreen
        self.app.push_screen(LogsScreen(run_id=self._selected_run.run_id))
