"""Job and Run data models.

Normalizes Databricks Jobs API responses into stable structs.
Jobs have Runs; Runs have tasks, logs, and error details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class RunState(str, Enum):
    """Databricks run lifecycle states."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    TERMINATING = "TERMINATING"
    TERMINATED = "TERMINATED"
    SKIPPED = "SKIPPED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    BLOCKED = "BLOCKED"
    WAITING_FOR_RETRY = "WAITING_FOR_RETRY"
    QUEUED = "QUEUED"
    UNKNOWN = "UNKNOWN"

    @property
    def is_active(self) -> bool:
        return self in (
            RunState.PENDING, RunState.RUNNING,
            RunState.QUEUED, RunState.BLOCKED,
            RunState.WAITING_FOR_RETRY,
        )

    @property
    def is_terminal(self) -> bool:
        return self in (
            RunState.TERMINATED, RunState.SKIPPED,
            RunState.INTERNAL_ERROR,
        )

    @property
    def display_style(self) -> str:
        return {
            RunState.RUNNING: "green",
            RunState.PENDING: "yellow",
            RunState.QUEUED: "yellow dim",
            RunState.TERMINATED: "white",  # Need result_state for color
            RunState.INTERNAL_ERROR: "red bold",
            RunState.SKIPPED: "dim",
            RunState.BLOCKED: "yellow",
        }.get(self, "white")


class RunResult(str, Enum):
    """Databricks run result states (only set when lifecycle = TERMINATED)."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEDOUT = "TIMEDOUT"
    CANCELED = "CANCELED"
    MAXIMUM_CONCURRENT_RUNS_REACHED = "MAXIMUM_CONCURRENT_RUNS_REACHED"
    EXCLUDED = "EXCLUDED"
    SUCCESS_WITH_FAILURES = "SUCCESS_WITH_FAILURES"
    UPSTREAM_FAILED = "UPSTREAM_FAILED"
    UPSTREAM_CANCELED = "UPSTREAM_CANCELED"
    UNKNOWN = "UNKNOWN"

    @property
    def is_success(self) -> bool:
        return self == RunResult.SUCCESS

    @property
    def is_failure(self) -> bool:
        return self in (RunResult.FAILED, RunResult.TIMEDOUT, RunResult.UPSTREAM_FAILED)

    @property
    def display_style(self) -> str:
        if self.is_success:
            return "green"
        if self.is_failure:
            return "red bold"
        if self == RunResult.CANCELED:
            return "yellow dim"
        return "dim"


class TriggerType(str, Enum):
    """What triggered the run."""
    PERIODIC = "PERIODIC"       # Scheduled
    ONE_TIME = "ONE_TIME"       # Manual / API
    RETRY = "RETRY"
    CONTINUOUS = "CONTINUOUS"
    FILE_ARRIVAL = "FILE_ARRIVAL"
    UNKNOWN = "UNKNOWN"


# ─── Job Summary ────────────────────────────────────────────────

@dataclass
class JobSummary:
    """Normalized job definition for TUI display."""
    id: int
    name: str
    creator: str = ""

    # Schedule
    schedule_cron: Optional[str] = None
    schedule_timezone: Optional[str] = None
    schedule_paused: bool = False

    # Metadata
    tags: dict[str, str] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    max_concurrent_runs: int = 1

    # Computed from recent runs
    last_run_state: Optional[RunState] = None
    last_run_result: Optional[RunResult] = None
    last_run_at: Optional[datetime] = None
    active_runs_count: int = 0

    # Links
    ui_url: Optional[str] = None

    @property
    def schedule_display(self) -> str:
        if not self.schedule_cron:
            return "manual"
        if self.schedule_paused:
            return f"{self.schedule_cron} (paused)"
        return self.schedule_cron

    @property
    def health_display(self) -> str:
        """Quick health indicator: ✓, ✗, ●, —."""
        if self.last_run_result == RunResult.SUCCESS:
            return "✓"
        if self.last_run_result and self.last_run_result.is_failure:
            return "✗"
        if self.last_run_state and self.last_run_state.is_active:
            return "●"
        return "—"

    @classmethod
    def from_api(cls, data: dict, workspace_host: str = "") -> JobSummary:
        """Create from Databricks SDK job dict."""
        job_id = data.get("job_id", 0)
        settings = data.get("settings", {})
        schedule = settings.get("schedule")

        ui_url = f"{workspace_host}/#job/{job_id}" if workspace_host else None

        return cls(
            id=job_id,
            name=settings.get("name", f"job-{job_id}"),
            creator=data.get("creator_user_name", ""),
            schedule_cron=schedule.get("quartz_cron_expression") if schedule else None,
            schedule_timezone=schedule.get("timezone_id") if schedule else None,
            schedule_paused=(
                schedule.get("pause_status", "UNPAUSED") == "PAUSED"
                if schedule else False
            ),
            tags=settings.get("tags", {}),
            created_at=_epoch_ms_to_dt(data.get("created_time")),
            max_concurrent_runs=settings.get("max_concurrent_runs", 1),
            ui_url=ui_url,
        )


# ─── Run Summary ────────────────────────────────────────────────

@dataclass
class RunSummary:
    """Normalized run summary for TUI display."""
    run_id: int
    job_id: int
    run_name: str = ""

    # State
    state: RunState = RunState.UNKNOWN
    result: Optional[RunResult] = None
    state_message: str = ""

    # Timing
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    setup_duration_ms: int = 0
    execution_duration_ms: int = 0

    # Context
    trigger: TriggerType = TriggerType.UNKNOWN
    cluster_id: str = ""
    notebook_path: str = ""
    task_key: str = ""

    # Error info (the "failure signature")
    error_snippet: str = ""

    # Parameters
    parameters: dict[str, str] = field(default_factory=dict)

    # Links
    run_page_url: str = ""
    ui_url: Optional[str] = None

    @property
    def duration_display(self) -> str:
        """Human-friendly duration."""
        total_ms = self.execution_duration_ms or 0
        if total_ms == 0 and self.started_at:
            # Still running — compute from wall clock
            if self.state.is_active:
                delta = datetime.now(timezone.utc) - self.started_at
                total_ms = int(delta.total_seconds() * 1000)
            else:
                return "—"

        total_seconds = total_ms // 1000
        if total_seconds < 60:
            return f"{total_seconds}s"
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        if minutes < 60:
            return f"{minutes}m {seconds}s"
        hours = minutes // 60
        return f"{hours}h {minutes % 60}m"

    @property
    def result_display(self) -> str:
        """Combined state + result for display."""
        if self.state.is_active:
            return self.state.value
        if self.result:
            return self.result.value
        return self.state.value

    @property
    def result_style(self) -> str:
        """Style hint for the result cell."""
        if self.result:
            return self.result.display_style
        return self.state.display_style

    @classmethod
    def from_api(cls, data: dict, workspace_host: str = "") -> RunSummary:
        """Create from Databricks SDK run dict."""
        state_obj = data.get("state", {})

        # Parse lifecycle state
        lifecycle_str = state_obj.get("life_cycle_state", "UNKNOWN")
        try:
            state = RunState(lifecycle_str)
        except ValueError:
            state = RunState.UNKNOWN

        # Parse result state
        result = None
        result_str = state_obj.get("result_state")
        if result_str:
            try:
                result = RunResult(result_str)
            except ValueError:
                result = RunResult.UNKNOWN

        # Parse trigger
        trigger_str = data.get("trigger", "UNKNOWN")
        try:
            trigger = TriggerType(trigger_str)
        except ValueError:
            trigger = TriggerType.UNKNOWN

        # Extract first task info (for single-task jobs)
        tasks = data.get("tasks", [])
        task_key = ""
        notebook_path = ""
        cluster_id_val = ""
        if tasks:
            first_task = tasks[0]
            task_key = first_task.get("task_key", "")
            nb_task = first_task.get("notebook_task", {})
            notebook_path = nb_task.get("notebook_path", "")
            cluster_id_val = first_task.get("existing_cluster_id", "")

        # Extract error snippet
        error_snippet = ""
        state_message = state_obj.get("state_message", "")
        if result in (RunResult.FAILED, RunResult.TIMEDOUT):
            error_snippet = state_message[:200] if state_message else ""

        # Parameters
        params: dict[str, str] = {}
        job_params = data.get("job_parameters", [])
        for p in job_params:
            if isinstance(p, dict):
                params[p.get("name", "")] = p.get("value", "")

        run_id = data.get("run_id", 0)

        return cls(
            run_id=run_id,
            job_id=data.get("job_id", 0),
            run_name=data.get("run_name", ""),
            state=state,
            result=result,
            state_message=state_message,
            started_at=_epoch_ms_to_dt(data.get("start_time")),
            ended_at=_epoch_ms_to_dt(data.get("end_time")),
            setup_duration_ms=data.get("setup_duration", 0) or 0,
            execution_duration_ms=data.get("execution_duration", 0) or 0,
            trigger=trigger,
            cluster_id=cluster_id_val or data.get("cluster_instance", {}).get("cluster_id", ""),
            notebook_path=notebook_path,
            task_key=task_key,
            error_snippet=error_snippet,
            parameters=params,
            run_page_url=data.get("run_page_url", ""),
            ui_url=data.get("run_page_url"),
        )


# ─── Run Detail (extended, for detail panel) ────────────────────

@dataclass
class RunDetail(RunSummary):
    """Extended run info for the detail panel.

    Inherits all RunSummary fields and adds:
    - Full error output
    - All task details (for multi-task workflows)
    - Output
    """
    full_error: str = ""
    output_text: str = ""
    output_truncated: bool = False
    tasks: list[TaskSummary] = field(default_factory=list)


@dataclass
class TaskSummary:
    """A single task within a multi-task workflow run."""
    task_key: str
    state: RunState = RunState.UNKNOWN
    result: Optional[RunResult] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_ms: int = 0
    error_snippet: str = ""
    cluster_id: str = ""


# ─── Helpers ────────────────────────────────────────────────────

def _epoch_ms_to_dt(epoch_ms: Optional[int]) -> Optional[datetime]:
    """Convert epoch milliseconds to timezone-aware datetime."""
    if epoch_ms is None or epoch_ms == 0:
        return None
    return datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
