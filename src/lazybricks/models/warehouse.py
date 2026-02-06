"""SQL Warehouse data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class WarehouseState(str, Enum):
    """SQL Warehouse lifecycle states."""
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    DELETING = "DELETING"
    DELETED = "DELETED"
    UNKNOWN = "UNKNOWN"

    @property
    def is_active(self) -> bool:
        return self in (WarehouseState.RUNNING, WarehouseState.STARTING)

    @property
    def display_style(self) -> str:
        return {
            WarehouseState.RUNNING: "green",
            WarehouseState.STOPPED: "dim",
            WarehouseState.STARTING: "yellow",
            WarehouseState.STOPPING: "yellow dim",
            WarehouseState.DELETED: "red dim",
        }.get(self, "white")


class WarehouseSize(str, Enum):
    """SQL Warehouse T-shirt sizes."""
    XXSMALL = "2X-Small"
    XSMALL = "X-Small"
    SMALL = "Small"
    MEDIUM = "Medium"
    LARGE = "Large"
    XLARGE = "X-Large"
    XXLARGE = "2X-Large"
    XXXLARGE = "3X-Large"
    XXXXLARGE = "4X-Large"
    UNKNOWN = "Unknown"


@dataclass
class WarehouseSummary:
    """Normalized SQL Warehouse summary."""
    id: str
    name: str
    state: WarehouseState
    size: str = ""
    cluster_size: str = ""

    # Capacity
    min_num_clusters: int = 1
    max_num_clusters: int = 1
    num_active_sessions: int = 0
    num_clusters: int = 0

    # Type
    warehouse_type: str = ""  # PRO, CLASSIC, etc.
    enable_serverless: bool = False

    # Timing
    auto_stop_mins: int = 0
    started_at: Optional[datetime] = None

    # Metadata
    creator: str = ""

    # Links
    ui_url: Optional[str] = None

    @property
    def size_display(self) -> str:
        """Size with cluster scaling info."""
        base = self.size or self.cluster_size
        if self.max_num_clusters > 1:
            return f"{base} ({self.min_num_clusters}–{self.max_num_clusters} clusters)"
        return base

    @property
    def type_display(self) -> str:
        if self.enable_serverless:
            return "Serverless"
        return self.warehouse_type or "Classic"

    @classmethod
    def from_api(cls, data: dict, workspace_host: str = "") -> WarehouseSummary:
        """Create from Databricks SDK warehouse dict."""
        state_str = data.get("state", "UNKNOWN")
        try:
            state = WarehouseState(state_str)
        except ValueError:
            state = WarehouseState.UNKNOWN

        wh_id = data.get("id", "")
        ui_url = f"{workspace_host}/sql/warehouses/{wh_id}" if workspace_host else None

        return cls(
            id=wh_id,
            name=data.get("name", "unnamed"),
            state=state,
            size=data.get("cluster_size", ""),
            cluster_size=data.get("cluster_size", ""),
            min_num_clusters=data.get("min_num_clusters", 1),
            max_num_clusters=data.get("max_num_clusters", 1),
            num_active_sessions=data.get("num_active_sessions", 0),
            num_clusters=data.get("num_clusters", 0),
            warehouse_type=data.get("warehouse_type", ""),
            enable_serverless=data.get("enable_serverless_compute", False),
            auto_stop_mins=data.get("auto_stop_mins", 0),
            creator=data.get("creator_name", ""),
            ui_url=ui_url,
        )


@dataclass
class WarehouseQuery:
    """An active query running on a SQL warehouse."""
    query_id: str
    status: str = ""
    user_name: str = ""
    query_text: str = ""
    started_at: Optional[datetime] = None
    duration_ms: int = 0
    warehouse_id: str = ""

    @property
    def duration_display(self) -> str:
        total_seconds = self.duration_ms // 1000
        if total_seconds < 60:
            return f"{total_seconds}s"
        minutes = total_seconds // 60
        return f"{minutes}m {total_seconds % 60}s"

    @property
    def query_preview(self) -> str:
        """First 80 chars of query text."""
        text = self.query_text.replace("\n", " ").strip()
        if len(text) > 80:
            return text[:77] + "..."
        return text
