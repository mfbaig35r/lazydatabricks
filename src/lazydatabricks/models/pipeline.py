"""Pipeline and Update data models.

Normalizes Databricks Delta Live Tables (DLT) API responses into stable structs.
Pipelines have Updates; Updates have events and error details.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class PipelineState(str, Enum):
    """Databricks pipeline lifecycle states."""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    DELETED = "DELETED"
    UNKNOWN = "UNKNOWN"

    @property
    def is_active(self) -> bool:
        return self == PipelineState.RUNNING

    @property
    def display_style(self) -> str:
        return {
            PipelineState.IDLE: "dim",
            PipelineState.RUNNING: "green",
            PipelineState.FAILED: "red bold",
            PipelineState.DELETED: "dim",
        }.get(self, "white")


class UpdateState(str, Enum):
    """Databricks pipeline update states."""
    QUEUED = "QUEUED"
    CREATED = "CREATED"
    WAITING_FOR_RESOURCES = "WAITING_FOR_RESOURCES"
    INITIALIZING = "INITIALIZING"
    SETTING_UP_TABLES = "SETTING_UP_TABLES"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    RESETTING = "RESETTING"
    UNKNOWN = "UNKNOWN"

    @property
    def is_active(self) -> bool:
        return self in (
            UpdateState.QUEUED,
            UpdateState.CREATED,
            UpdateState.WAITING_FOR_RESOURCES,
            UpdateState.INITIALIZING,
            UpdateState.SETTING_UP_TABLES,
            UpdateState.RUNNING,
            UpdateState.STOPPING,
            UpdateState.RESETTING,
        )

    @property
    def is_terminal(self) -> bool:
        return self in (
            UpdateState.COMPLETED,
            UpdateState.FAILED,
            UpdateState.CANCELED,
        )

    @property
    def is_success(self) -> bool:
        return self == UpdateState.COMPLETED

    @property
    def is_failure(self) -> bool:
        return self == UpdateState.FAILED

    @property
    def display_style(self) -> str:
        if self.is_success:
            return "green"
        if self.is_failure:
            return "red bold"
        if self == UpdateState.CANCELED:
            return "yellow dim"
        if self.is_active:
            return "yellow"
        return "dim"


class UpdateCause(str, Enum):
    """What triggered the pipeline update."""
    USER_ACTION = "USER_ACTION"
    SERVICE_UPGRADE = "SERVICE_UPGRADE"
    SCHEMA_CHANGE = "SCHEMA_CHANGE"
    RETRY_ON_FAILURE = "RETRY_ON_FAILURE"
    API_CALL = "API_CALL"
    UNKNOWN = "UNKNOWN"


# ─── Pipeline Summary ────────────────────────────────────────────

@dataclass
class PipelineSummary:
    """Normalized pipeline definition for TUI display."""
    pipeline_id: str
    name: str
    state: PipelineState = PipelineState.UNKNOWN
    creator: str = ""

    # Configuration
    cluster_id: Optional[str] = None
    target_schema: Optional[str] = None  # Unity Catalog target
    catalog: Optional[str] = None
    continuous: bool = False
    development: bool = False

    # Last update info
    last_update_id: Optional[str] = None
    last_update_state: Optional[UpdateState] = None
    last_update_time: Optional[datetime] = None

    # Links
    ui_url: Optional[str] = None

    @property
    def state_display(self) -> str:
        """Display state value."""
        return self.state.value

    @property
    def health_display(self) -> str:
        """Quick health indicator: ✓, ✗, ●, —."""
        if self.last_update_state == UpdateState.COMPLETED:
            return "✓"
        if self.last_update_state and self.last_update_state.is_failure:
            return "✗"
        if self.state.is_active or (self.last_update_state and self.last_update_state.is_active):
            return "●"
        return "—"

    @property
    def target_display(self) -> str:
        """Display target schema/catalog."""
        if self.catalog and self.target_schema:
            return f"{self.catalog}.{self.target_schema}"
        if self.target_schema:
            return self.target_schema
        return "—"

    @property
    def mode_display(self) -> str:
        """Display mode (continuous/triggered, dev/prod)."""
        parts = []
        if self.continuous:
            parts.append("continuous")
        if self.development:
            parts.append("dev")
        return ", ".join(parts) if parts else "triggered"

    @classmethod
    def from_api(cls, data: dict, workspace_host: str = "") -> PipelineSummary:
        """Create from Databricks SDK pipeline dict."""
        pipeline_id = data.get("pipeline_id", "")
        spec = data.get("spec", {})

        # Parse state
        state_str = data.get("state", "UNKNOWN")
        try:
            state = PipelineState(state_str)
        except ValueError:
            state = PipelineState.UNKNOWN

        # Parse last update state
        last_update_state = None
        latest_updates = data.get("latest_updates", [])
        last_update_id = None
        last_update_time = None
        if latest_updates:
            latest = latest_updates[0]
            last_update_id = latest.get("update_id")
            state_str = latest.get("state", "UNKNOWN")
            try:
                last_update_state = UpdateState(state_str)
            except ValueError:
                last_update_state = UpdateState.UNKNOWN
            last_update_time = _epoch_ms_to_dt(latest.get("creation_time"))

        ui_url = f"{workspace_host}/#joblist/pipelines/{pipeline_id}" if workspace_host else None

        return cls(
            pipeline_id=pipeline_id,
            name=spec.get("name", data.get("name", f"pipeline-{pipeline_id[:8]}")),
            state=state,
            creator=data.get("creator_user_name", ""),
            cluster_id=data.get("cluster_id"),
            target_schema=spec.get("target"),
            catalog=spec.get("catalog"),
            continuous=spec.get("continuous", False),
            development=spec.get("development", False),
            last_update_id=last_update_id,
            last_update_state=last_update_state,
            last_update_time=last_update_time,
            ui_url=ui_url,
        )


# ─── Update Summary ────────────────────────────────────────────────

@dataclass
class UpdateSummary:
    """Normalized update summary for TUI display."""
    update_id: str
    pipeline_id: str
    state: UpdateState = UpdateState.UNKNOWN
    cause: UpdateCause = UpdateCause.UNKNOWN

    # Timing
    creation_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Configuration
    full_refresh: bool = False
    full_refresh_selection: list[str] = field(default_factory=list)

    # Cluster
    cluster_id: Optional[str] = None

    @property
    def duration_display(self) -> str:
        """Human-friendly duration."""
        if not self.start_time:
            return "—"

        if self.end_time:
            delta = self.end_time - self.start_time
            total_seconds = int(delta.total_seconds())
        elif self.state.is_active:
            delta = datetime.now(timezone.utc) - self.start_time
            total_seconds = int(delta.total_seconds())
        else:
            return "—"

        if total_seconds < 60:
            return f"{total_seconds}s"
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        if minutes < 60:
            return f"{minutes}m {seconds}s"
        hours = minutes // 60
        return f"{hours}h {minutes % 60}m"

    @property
    def state_display(self) -> str:
        """Display state value."""
        return self.state.value

    @property
    def result_style(self) -> str:
        """Style hint for the result cell."""
        return self.state.display_style

    @classmethod
    def from_api(cls, data: dict, pipeline_id: str = "") -> UpdateSummary:
        """Create from Databricks SDK update dict."""
        # Parse state
        state_str = data.get("state", "UNKNOWN")
        try:
            state = UpdateState(state_str)
        except ValueError:
            state = UpdateState.UNKNOWN

        # Parse cause
        cause_str = data.get("cause", "UNKNOWN")
        try:
            cause = UpdateCause(cause_str)
        except ValueError:
            cause = UpdateCause.UNKNOWN

        # Full refresh selection
        full_refresh_selection = data.get("full_refresh_selection", []) or []

        return cls(
            update_id=data.get("update_id", ""),
            pipeline_id=pipeline_id or data.get("pipeline_id", ""),
            state=state,
            cause=cause,
            creation_time=_epoch_ms_to_dt(data.get("creation_time")),
            start_time=_epoch_ms_to_dt(data.get("start_time")),
            end_time=_epoch_ms_to_dt(data.get("end_time")),
            full_refresh=data.get("full_refresh", False),
            full_refresh_selection=full_refresh_selection,
            cluster_id=data.get("cluster_id"),
        )


# ─── Update Detail (extended, for detail panel) ────────────────────

@dataclass
class UpdateDetail(UpdateSummary):
    """Extended update info for the detail panel.

    Inherits all UpdateSummary fields and adds:
    - Events list
    - Error message
    """
    events: list[dict] = field(default_factory=list)
    error_message: str = ""


# ─── Helpers ────────────────────────────────────────────────────

def _epoch_ms_to_dt(epoch_ms) -> Optional[datetime]:
    """Convert epoch milliseconds to timezone-aware datetime.

    Handles both int and string inputs from the API.
    """
    if epoch_ms is None:
        return None
    try:
        # Convert to int if string
        ms = int(epoch_ms)
        if ms == 0:
            return None
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    except (ValueError, TypeError):
        return None
