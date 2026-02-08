"""Billing API operations.

Uses the Databricks Statement Execution API to query billing system tables.
Requires a SQL Warehouse for query execution.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from lazybricks.api.client import DatabricksClient
from lazybricks.extensions.billing.models import (
    SkuCostSummary,
    TimeWindow,
    UsageBreakdown,
)
from lazybricks.extensions.billing.queries import (
    ACCESS_CHECK_QUERY,
    BREAKDOWN_QUERY,
    SKU_COST_QUERY,
    TOTAL_COST_QUERY,
)

logger = logging.getLogger(__name__)


class BillingOps:
    """Billing query operations using Statement Execution API."""

    def __init__(self, client: DatabricksClient, config: dict) -> None:
        self._client = client
        self._warehouse_id = config.get("sql_warehouse_id", "")
        self._default_window = config.get("default_window", "7d")

    @property
    def warehouse_id(self) -> str:
        """The SQL warehouse ID for query execution."""
        return self._warehouse_id

    def _execute_query(
        self,
        query: str,
        parameters: Optional[list[dict]] = None,
        timeout_seconds: int = 60,
    ) -> list[dict]:
        """Execute SQL via Statement Execution API.

        Args:
            query: SQL query string with :param placeholders.
            parameters: List of parameter dicts with name, value, type.
            timeout_seconds: Query timeout.

        Returns:
            List of row dicts with column names as keys.
        """
        if not self._warehouse_id:
            logger.error("No SQL warehouse configured for billing queries")
            return []

        try:
            # Build parameters for the API
            params = None
            if parameters:
                params = [
                    {"name": p["name"], "value": str(p["value"]), "type": "STRING"}
                    for p in parameters
                ]

            # Execute statement
            response = self._client.sdk.statement_execution.execute_statement(
                warehouse_id=self._warehouse_id,
                statement=query,
                parameters=params,
                wait_timeout=f"{timeout_seconds}s",
            )

            # Check for errors
            if response.status and response.status.state:
                state = response.status.state.value if hasattr(response.status.state, "value") else str(response.status.state)
                if state == "FAILED":
                    error_msg = ""
                    if response.status.error:
                        error_msg = getattr(response.status.error, "message", str(response.status.error))
                    logger.error(f"Query failed: {error_msg}")
                    return []

            # Extract results
            if not response.result or not response.result.data_array:
                return []

            # Get column names from manifest
            columns = []
            if response.manifest and response.manifest.schema and response.manifest.schema.columns:
                columns = [col.name for col in response.manifest.schema.columns]

            if not columns:
                return []

            # Convert to list of dicts
            rows = []
            for row_data in response.result.data_array:
                row_dict = {}
                for i, col_name in enumerate(columns):
                    if i < len(row_data):
                        row_dict[col_name] = row_data[i]
                    else:
                        row_dict[col_name] = None
                rows.append(row_dict)

            return rows

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []

    def check_access(self) -> tuple[bool, str]:
        """Check if user has access to billing tables.

        Returns:
            Tuple of (success, error_message).
        """
        if not self._warehouse_id:
            return False, "No SQL warehouse configured"

        try:
            rows = self._execute_query(ACCESS_CHECK_QUERY, timeout_seconds=30)
            # If we get any result (even empty), access is OK
            return True, ""
        except Exception as e:
            return False, str(e)

    def get_time_window_bounds(
        self,
        window: TimeWindow,
    ) -> tuple[datetime, datetime]:
        """Calculate start/end timestamps for a time window.

        Returns:
            Tuple of (start, end) datetimes.
        """
        now = datetime.now(timezone.utc)
        end = now
        start = now - timedelta(days=window.days)
        return start, end

    def list_sku_costs(
        self,
        window: TimeWindow,
    ) -> list[SkuCostSummary]:
        """Get SKU-level cost summary for time window.

        Args:
            window: Time window to query.

        Returns:
            List of SkuCostSummary, sorted by cost descending.
        """
        start, end = self.get_time_window_bounds(window)

        params = [
            {"name": "window_start", "value": start.strftime("%Y-%m-%d")},
            {"name": "window_end", "value": end.strftime("%Y-%m-%d")},
        ]

        rows = self._execute_query(SKU_COST_QUERY, params, timeout_seconds=60)

        summaries = []
        for row in rows:
            try:
                summaries.append(SkuCostSummary.from_row(row))
            except Exception as e:
                logger.warning(f"Failed to parse SKU cost row: {e}")

        return summaries

    def get_usage_breakdown(
        self,
        sku_name: str,
        window: TimeWindow,
    ) -> list[UsageBreakdown]:
        """Get usage breakdown by compute target for a specific SKU.

        Args:
            sku_name: SKU to get breakdown for.
            window: Time window to query.

        Returns:
            List of UsageBreakdown, sorted by cost descending.
        """
        start, end = self.get_time_window_bounds(window)

        params = [
            {"name": "sku_name", "value": sku_name},
            {"name": "window_start", "value": start.strftime("%Y-%m-%d")},
            {"name": "window_end", "value": end.strftime("%Y-%m-%d")},
        ]

        rows = self._execute_query(BREAKDOWN_QUERY, params, timeout_seconds=60)

        breakdowns = []
        for row in rows:
            try:
                breakdowns.append(UsageBreakdown.from_row(row))
            except Exception as e:
                logger.warning(f"Failed to parse breakdown row: {e}")

        return breakdowns

    def get_total_cost(
        self,
        window: TimeWindow,
    ) -> Decimal:
        """Get total estimated cost for time window.

        Useful for home screen summary widget.

        Args:
            window: Time window to query.

        Returns:
            Total estimated cost as Decimal.
        """
        start, end = self.get_time_window_bounds(window)

        params = [
            {"name": "window_start", "value": start.strftime("%Y-%m-%d")},
            {"name": "window_end", "value": end.strftime("%Y-%m-%d")},
        ]

        rows = self._execute_query(TOTAL_COST_QUERY, params, timeout_seconds=60)

        if rows and rows[0].get("total_cost"):
            try:
                return Decimal(str(rows[0]["total_cost"]))
            except Exception:
                pass

        return Decimal(0)
