"""Billing data models.

Defines cost summary and usage breakdown structures for the Billing screen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Optional


class TimeWindow(str, Enum):
    """Time window for billing queries."""
    DAY_1 = "24h"
    DAY_7 = "7d"
    DAY_30 = "30d"

    @property
    def days(self) -> int:
        return {"24h": 1, "7d": 7, "30d": 30}[self.value]

    @property
    def display(self) -> str:
        return {"24h": "24 hours", "7d": "7 days", "30d": "30 days"}[self.value]

    def next(self) -> "TimeWindow":
        """Cycle to next time window."""
        windows = [TimeWindow.DAY_1, TimeWindow.DAY_7, TimeWindow.DAY_30]
        idx = windows.index(self)
        return windows[(idx + 1) % len(windows)]


class GroupBy(str, Enum):
    """Grouping dimension for usage breakdown."""
    CLUSTER = "cluster_id"
    WAREHOUSE = "warehouse_id"
    JOB = "job_id"
    WORKSPACE = "workspace_id"

    @property
    def display(self) -> str:
        return self.value.replace("_id", "").title()

    def next(self) -> "GroupBy":
        """Cycle to next grouping."""
        groups = [GroupBy.CLUSTER, GroupBy.WAREHOUSE, GroupBy.JOB, GroupBy.WORKSPACE]
        idx = groups.index(self)
        return groups[(idx + 1) % len(groups)]


@dataclass
class SkuCostSummary:
    """SKU-level cost summary for left pane."""
    sku_name: str
    usage_type: str
    billing_origin_product: str
    total_dbu: Decimal
    unit_price_effective: Decimal
    estimated_cost: Decimal
    unit_price_list: Optional[Decimal] = None
    unit_price_promo: Optional[Decimal] = None
    discount_pct: Optional[Decimal] = None

    @property
    def cost_display(self) -> str:
        """Format cost with dollar sign."""
        return f"${self.estimated_cost:,.2f}"

    @property
    def dbu_display(self) -> str:
        """Format DBUs with K suffix for thousands."""
        if self.total_dbu >= 1000:
            return f"{self.total_dbu / 1000:,.1f}K"
        return f"{self.total_dbu:,.1f}"

    @property
    def discount_display(self) -> str:
        """Format discount percentage."""
        if self.discount_pct is None:
            return "—"
        return f"{self.discount_pct * 100:.0f}%"

    @property
    def price_display(self) -> str:
        """Format unit price."""
        return f"${self.unit_price_effective:.4f}"

    @classmethod
    def from_row(cls, row: dict) -> "SkuCostSummary":
        """Create from query result row."""
        return cls(
            sku_name=row.get("sku_name") or "",
            usage_type=row.get("usage_type") or "",
            billing_origin_product=row.get("billing_origin_product") or "",
            total_dbu=_to_decimal(row.get("total_dbu")),
            unit_price_effective=_to_decimal(row.get("unit_price_effective")),
            estimated_cost=_to_decimal(row.get("estimated_cost")),
            unit_price_list=_to_decimal(row.get("unit_price_list")),
            unit_price_promo=_to_decimal(row.get("unit_price_promo")),
            discount_pct=_to_decimal(row.get("discount_pct")),
        )


@dataclass
class UsageBreakdown:
    """Usage breakdown by compute target for middle pane."""
    workspace_id: str
    cluster_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    job_id: Optional[str] = None
    job_run_id: Optional[str] = None
    pipeline_id: Optional[str] = None
    notebook_id: Optional[str] = None
    creator: Optional[str] = None
    resource_class: Optional[str] = None
    total_dbu: Decimal = field(default_factory=lambda: Decimal(0))
    unit_price_effective: Decimal = field(default_factory=lambda: Decimal(0))
    estimated_cost: Decimal = field(default_factory=lambda: Decimal(0))

    @property
    def resource_id(self) -> Optional[str]:
        """Return the primary resource identifier."""
        return self.cluster_id or self.warehouse_id or self.job_id or self.pipeline_id or self.notebook_id

    @property
    def resource_type(self) -> Optional[str]:
        """Return the type of resource."""
        if self.cluster_id:
            return "cluster"
        if self.warehouse_id:
            return "warehouse"
        if self.job_id:
            return "job"
        if self.pipeline_id:
            return "pipeline"
        if self.notebook_id:
            return "notebook"
        return None

    @property
    def resource_display(self) -> str:
        """Display name for the resource."""
        if self.cluster_id:
            return self.cluster_id[:16]
        if self.warehouse_id:
            return self.warehouse_id[:16]
        if self.job_id:
            return f"job-{self.job_id}"
        if self.pipeline_id:
            return f"pipeline-{self.pipeline_id[:8]}"
        if self.notebook_id:
            return f"notebook-{self.notebook_id[:8]}"
        if self.creator:
            return f"[{self.creator[:16]}]"
        return "[unknown]"

    @property
    def cost_display(self) -> str:
        """Format cost with dollar sign."""
        return f"${self.estimated_cost:,.2f}"

    @property
    def dbu_display(self) -> str:
        """Format DBUs."""
        if self.total_dbu >= 1000:
            return f"{self.total_dbu / 1000:,.1f}K"
        return f"{self.total_dbu:,.1f}"

    @classmethod
    def from_row(cls, row: dict) -> "UsageBreakdown":
        """Create from query result row."""
        return cls(
            workspace_id=str(row.get("workspace_id") or ""),
            cluster_id=row.get("cluster_id"),
            warehouse_id=row.get("warehouse_id"),
            job_id=str(row.get("job_id")) if row.get("job_id") else None,
            job_run_id=str(row.get("job_run_id")) if row.get("job_run_id") else None,
            pipeline_id=row.get("pipeline_id"),
            notebook_id=row.get("notebook_id"),
            creator=row.get("creator"),
            resource_class=row.get("resource_class"),
            total_dbu=_to_decimal(row.get("total_dbu")),
            unit_price_effective=_to_decimal(row.get("unit_price_effective")),
            estimated_cost=_to_decimal(row.get("estimated_cost")),
        )


def _to_decimal(value) -> Decimal:
    """Safely convert a value to Decimal."""
    if value is None:
        return Decimal(0)
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(0)
