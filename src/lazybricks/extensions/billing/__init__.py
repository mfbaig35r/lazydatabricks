"""Billing extension — DBU cost visibility using system billing tables.

Provides a three-pane screen for viewing:
- SKU-level costs (left pane)
- Breakdown by compute target (middle pane)
- Usage detail with navigation (right pane)

Requires:
- SQL Warehouse for query execution
- Access to system.billing.usage and system.billing.list_prices tables

Config (in ~/.lazybricks/config.toml):
    [extensions]
    enabled = ["billing"]

    [extensions.billing]
    sql_warehouse_id = "your-warehouse-id"
    default_window = "7d"  # optional, default is 7d
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lazybricks.extensions.base import BaseExtension, ExtensionInfo
from lazybricks.extensions.billing.api import BillingOps
from lazybricks.extensions.billing.screen import BillingScreen

if TYPE_CHECKING:
    from lazybricks.api.client import DatabricksClient


class BillingExtension(BaseExtension):
    """Billing/Cost visibility extension.

    Shows DBU usage and estimated costs from Databricks system billing tables.
    """

    @property
    def info(self) -> ExtensionInfo:
        return ExtensionInfo(
            name="billing",
            display_name="Billing",
            description="DBU cost visibility using system billing tables",
            hotkey="b",
            requires_sql_warehouse=True,
        )

    def check_requirements(self, client: "DatabricksClient") -> tuple[bool, str]:
        """Check if billing extension can be loaded.

        Verifies:
        1. sql_warehouse_id is configured
        2. The warehouse exists (optional, fail gracefully)

        Note: We don't check billing table access here since that requires
        query execution. Access is checked when the screen loads.
        """
        warehouse_id = self.config.get("sql_warehouse_id", "")

        if not warehouse_id:
            return (
                False,
                "sql_warehouse_id not configured. Add to [extensions.billing] in config.",
            )

        # Optionally verify warehouse exists
        # (skip for now - let the screen handle connection errors)

        return True, ""

    def get_screen_class(self) -> type:
        """Return the BillingScreen class."""
        return BillingScreen

    def get_ops_class(self) -> type:
        """Return the BillingOps class."""
        return BillingOps

    def get_help_items(self) -> list[tuple[str, str]]:
        """Return help items for the billing screen."""
        return [
            ("r", "Refresh"),
            ("Tab", "Next Pane"),
            ("t", "Cycle Time Window"),
            ("g", "Cycle Grouping"),
            ("Enter", "Drill Down / Navigate"),
            ("Esc", "Back Up"),
        ]
