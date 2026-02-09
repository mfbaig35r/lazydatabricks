"""Cluster data models.

Normalizes Databricks cluster API responses into stable structs
that the TUI can render without caring about API version changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ClusterState(str, Enum):
    """Databricks cluster lifecycle states."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RESTARTING = "RESTARTING"
    RESIZING = "RESIZING"
    TERMINATING = "TERMINATING"
    TERMINATED = "TERMINATED"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"

    @property
    def is_active(self) -> bool:
        return self in (ClusterState.RUNNING, ClusterState.RESIZING, ClusterState.RESTARTING)

    @property
    def is_actionable(self) -> bool:
        """Can we start or stop this cluster?"""
        return self in (ClusterState.RUNNING, ClusterState.TERMINATED, ClusterState.ERROR)

    @property
    def display_style(self) -> str:
        """Return a style hint for TUI rendering."""
        return {
            ClusterState.RUNNING: "green",
            ClusterState.TERMINATED: "dim",
            ClusterState.ERROR: "red bold",
            ClusterState.PENDING: "yellow",
            ClusterState.RESTARTING: "yellow",
            ClusterState.RESIZING: "yellow",
            ClusterState.TERMINATING: "yellow dim",
        }.get(self, "white")


class ClusterFlag(str, Enum):
    """Risk / info flags for cluster health."""
    IDLE_BURN = "idle_burn"             # Running with no active jobs
    RECENT_RESTARTS = "recent_restarts"  # Restarted multiple times recently
    UNHEALTHY_DRIVER = "unhealthy_driver"
    SPOT_FALLBACK = "spot_fallback"      # Using on-demand after spot failure
    LONG_RUNNING = "long_running"        # Running for > threshold hours
    AUTO_TERMINATION_OFF = "no_auto_term"


@dataclass
class ClusterSummary:
    """Normalized cluster summary for TUI display."""
    id: str
    name: str
    state: ClusterState
    state_message: str = ""

    # Sizing
    node_type_id: str = ""
    driver_node_type_id: str = ""
    num_workers: int = 0
    autoscale_min: Optional[int] = None
    autoscale_max: Optional[int] = None

    # Timing
    started_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    auto_termination_minutes: Optional[int] = None

    # Metadata
    spark_version: str = ""
    creator: str = ""
    cluster_source: str = ""  # UI, API, JOB

    # Computed
    flags: list[ClusterFlag] = field(default_factory=list)

    # Links
    ui_url: Optional[str] = None

    @property
    def runtime_display(self) -> str:
        """Human-friendly runtime like '2h 14m' or 'terminated'."""
        if self.state == ClusterState.TERMINATED:
            return "terminated"
        if not self.started_at:
            return "—"
        delta = datetime.now(timezone.utc) - self.started_at
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    @property
    def idle_time_display(self) -> str:
        """How long since last activity."""
        if not self.last_activity_at:
            return "—"
        if self.state != ClusterState.RUNNING:
            return "—"
        delta = datetime.now(timezone.utc) - self.last_activity_at
        minutes = int(delta.total_seconds()) // 60
        if minutes < 1:
            return "just now"
        if minutes < 60:
            return f"{minutes}m idle"
        hours = minutes // 60
        return f"{hours}h {minutes % 60}m idle"

    @property
    def workers_display(self) -> str:
        """Show worker count or autoscale range."""
        if self.autoscale_min is not None and self.autoscale_max is not None:
            return f"{self.autoscale_min}–{self.autoscale_max}"
        return str(self.num_workers)

    def compute_flags(self, idle_burn_minutes: int = 30, long_running_hours: int = 12) -> None:
        """Compute risk flags based on current state and thresholds."""
        self.flags.clear()

        if self.state == ClusterState.RUNNING:
            # Idle burn detection
            if self.last_activity_at:
                idle_seconds = (datetime.now(timezone.utc) - self.last_activity_at).total_seconds()
                if idle_seconds > idle_burn_minutes * 60:
                    self.flags.append(ClusterFlag.IDLE_BURN)

            # Long running
            if self.started_at:
                running_hours = (datetime.now(timezone.utc) - self.started_at).total_seconds() / 3600
                if running_hours > long_running_hours:
                    self.flags.append(ClusterFlag.LONG_RUNNING)

            # No auto-termination
            if self.auto_termination_minutes is None or self.auto_termination_minutes == 0:
                self.flags.append(ClusterFlag.AUTO_TERMINATION_OFF)

    @classmethod
    def from_api(cls, data: dict, workspace_host: str = "") -> ClusterSummary:
        """Create from Databricks SDK cluster info dict.

        Accepts the dict form of databricks.sdk.service.compute.ClusterDetails.
        """
        # Parse state
        state_str = data.get("state", "UNKNOWN")
        try:
            state = ClusterState(state_str)
        except ValueError:
            state = ClusterState.UNKNOWN

        # Parse timestamps (Databricks returns epoch millis)
        started_at = _epoch_ms_to_dt(data.get("start_time"))
        terminated_at = _epoch_ms_to_dt(data.get("terminated_time"))
        last_activity_at = _epoch_ms_to_dt(data.get("last_activity_time"))

        # Parse autoscale
        autoscale = data.get("autoscale")
        autoscale_min = autoscale.get("min_workers") if autoscale else None
        autoscale_max = autoscale.get("max_workers") if autoscale else None
        num_workers = data.get("num_workers", 0) if not autoscale else 0

        cluster_id = data.get("cluster_id", "")
        ui_url = f"{workspace_host}/#setting/clusters/{cluster_id}/configuration" if workspace_host else None

        summary = cls(
            id=cluster_id,
            name=data.get("cluster_name", "unnamed"),
            state=state,
            state_message=data.get("state_message", ""),
            node_type_id=data.get("node_type_id", ""),
            driver_node_type_id=data.get("driver_node_type_id", ""),
            num_workers=num_workers,
            autoscale_min=autoscale_min,
            autoscale_max=autoscale_max,
            started_at=started_at,
            terminated_at=terminated_at,
            last_activity_at=last_activity_at,
            auto_termination_minutes=data.get("autotermination_minutes"),
            spark_version=data.get("spark_version", ""),
            creator=data.get("creator_user_name", ""),
            cluster_source=data.get("cluster_source", ""),
            ui_url=ui_url,
        )

        summary.compute_flags()
        return summary


@dataclass
class ClusterEvent:
    """A single cluster event (from events API)."""
    timestamp: datetime
    event_type: str  # e.g., STARTING, RUNNING, RESTARTING, TERMINATING, etc.
    details: str = ""


def _epoch_ms_to_dt(epoch_ms: Optional[int]) -> Optional[datetime]:
    """Convert epoch milliseconds to timezone-aware datetime."""
    if epoch_ms is None or epoch_ms == 0:
        return None
    return datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
