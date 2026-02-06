"""Health snapshot model.

The single-screen "is everything OK?" view that LazyBricks opens with.
Combines Spark connectivity, cluster state, and recent job health.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class SparkStatus(str, Enum):
    """Spark session connectivity status."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    STALE = "stale"          # API says running, but SELECT 1 fails
    NO_CLUSTER = "no_cluster"  # No cluster configured
    UNKNOWN = "unknown"

    @property
    def display_style(self) -> str:
        return {
            SparkStatus.CONNECTED: "green bold",
            SparkStatus.DISCONNECTED: "red",
            SparkStatus.STALE: "yellow",
            SparkStatus.NO_CLUSTER: "dim",
        }.get(self, "white")

    @property
    def icon(self) -> str:
        return {
            SparkStatus.CONNECTED: "✓",
            SparkStatus.DISCONNECTED: "✗",
            SparkStatus.STALE: "⚠",
            SparkStatus.NO_CLUSTER: "—",
        }.get(self, "?")


@dataclass
class HealthSnapshot:
    """Home screen health summary — the first thing you see."""

    # Identity
    workspace_host: str = ""
    workspace_user: str = ""
    active_profile: str = ""

    # Spark connectivity
    spark_status: SparkStatus = SparkStatus.UNKNOWN
    spark_version: str = ""
    current_catalog: str = ""
    cluster_id: Optional[str] = None
    cluster_name: Optional[str] = None
    cluster_state: Optional[str] = None

    # Session validation
    validated_at: Optional[datetime] = None
    ttl_remaining_seconds: int = 0
    last_reconnect_at: Optional[datetime] = None

    # Job health (quick summary)
    active_runs_count: int = 0
    recent_failure_count: int = 0  # Failures in last 24h
    last_failure_run_id: Optional[int] = None
    last_failure_job_name: str = ""
    last_failure_at: Optional[datetime] = None
    last_failure_snippet: str = ""

    # Cluster health (quick summary)
    total_clusters: int = 0
    running_clusters: int = 0
    idle_burn_clusters: int = 0  # Running + idle

    # Warehouse health
    total_warehouses: int = 0
    running_warehouses: int = 0

    # Timestamps
    snapshot_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def spark_display(self) -> str:
        """One-line Spark status."""
        icon = self.spark_status.icon
        if self.spark_status == SparkStatus.CONNECTED:
            return f"{icon} Spark OK — {self.current_catalog} (v{self.spark_version})"
        if self.spark_status == SparkStatus.NO_CLUSTER:
            return f"{icon} No cluster configured"
        if self.spark_status == SparkStatus.STALE:
            return f"{icon} Spark stale — cluster may be restarting"
        return f"{icon} Spark disconnected"

    @property
    def cluster_health_display(self) -> str:
        """One-line cluster summary."""
        parts = [f"{self.running_clusters}/{self.total_clusters} running"]
        if self.idle_burn_clusters > 0:
            parts.append(f"⚠ {self.idle_burn_clusters} idle-burning")
        return " · ".join(parts)

    @property
    def job_health_display(self) -> str:
        """One-line job health."""
        parts = [f"{self.active_runs_count} active"]
        if self.recent_failure_count > 0:
            parts.append(f"✗ {self.recent_failure_count} failed (24h)")
        return " · ".join(parts)

    @property
    def last_failure_display(self) -> str:
        """Most recent failure summary."""
        if not self.last_failure_at:
            return "No recent failures"
        age = datetime.now(timezone.utc) - self.last_failure_at
        hours = int(age.total_seconds()) // 3600
        if hours < 1:
            minutes = int(age.total_seconds()) // 60
            ago = f"{minutes}m ago"
        elif hours < 24:
            ago = f"{hours}h ago"
        else:
            ago = f"{hours // 24}d ago"

        name = self.last_failure_job_name or f"run-{self.last_failure_run_id}"
        snippet = self.last_failure_snippet[:100] if self.last_failure_snippet else ""
        return f"✗ {name} ({ago}){': ' + snippet if snippet else ''}"
