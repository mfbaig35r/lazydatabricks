"""SQL Warehouse operations — list, start, stop, query info."""

from __future__ import annotations

import logging
from typing import Optional

from lazydatabricks.api.client import DatabricksClient
from lazydatabricks.models.warehouse import WarehouseQuery, WarehouseSummary

logger = logging.getLogger(__name__)


class WarehouseOps:
    """SQL Warehouse API operations."""

    def __init__(self, client: DatabricksClient) -> None:
        self._client = client

    def list_all(self) -> list[WarehouseSummary]:
        """List all SQL warehouses.

        Returns:
            List of WarehouseSummary, active first then by name.
        """
        try:
            warehouses = list(self._client.sdk.warehouses.list())
        except Exception as e:
            logger.error(f"Failed to list warehouses: {e}")
            return []

        summaries = []
        for w in warehouses:
            try:
                data = w.as_dict() if hasattr(w, "as_dict") else w.__dict__
                summaries.append(WarehouseSummary.from_api(data, self._client.host))
            except Exception as e:
                logger.warning(f"Failed to parse warehouse: {e}")

        # Sort: running first, then by name
        state_order = {"RUNNING": 0, "STARTING": 1, "STOPPING": 2}
        summaries.sort(key=lambda w: (state_order.get(w.state.value, 9), w.name.lower()))

        return summaries

    def get(self, warehouse_id: str) -> Optional[WarehouseSummary]:
        """Get a single warehouse by ID."""
        try:
            w = self._client.sdk.warehouses.get(id=warehouse_id)
            data = w.as_dict() if hasattr(w, "as_dict") else w.__dict__
            return WarehouseSummary.from_api(data, self._client.host)
        except Exception as e:
            logger.error(f"Failed to get warehouse {warehouse_id}: {e}")
            return None

    def start(self, warehouse_id: str) -> dict:
        """Start a stopped warehouse."""
        if self._client.is_read_only:
            return {"status": "error", "error": "Read-only mode — arm to enable actions"}

        try:
            self._client.sdk.warehouses.start(id=warehouse_id)
            logger.info(f"Start requested for warehouse {warehouse_id}")
            return {"status": "starting", "warehouse_id": warehouse_id}
        except Exception as e:
            logger.error(f"Failed to start warehouse {warehouse_id}: {e}")
            return {"status": "error", "error": str(e)}

    def stop(self, warehouse_id: str) -> dict:
        """Stop a running warehouse."""
        if self._client.is_read_only:
            return {"status": "error", "error": "Read-only mode — arm to enable actions"}

        try:
            self._client.sdk.warehouses.stop(id=warehouse_id)
            logger.info(f"Stop requested for warehouse {warehouse_id}")
            return {"status": "stopping", "warehouse_id": warehouse_id}
        except Exception as e:
            logger.error(f"Failed to stop warehouse {warehouse_id}: {e}")
            return {"status": "error", "error": str(e)}

    def list_queries(self, warehouse_id: str) -> list[WarehouseQuery]:
        """List active queries on a warehouse.

        Note: This uses the Query History API which may have limited
        availability depending on workspace tier.
        """
        try:
            # The SDK's query history API
            from datetime import datetime, timedelta, timezone

            queries = []
            history = self._client.sdk.query_history.list(
                filter_by={
                    "warehouse_ids": [warehouse_id],
                    "statuses": ["RUNNING", "QUEUED"],
                },
                max_results=50,
            )

            for q in history:
                data = q.as_dict() if hasattr(q, "as_dict") else q.__dict__
                queries.append(WarehouseQuery(
                    query_id=data.get("query_id", ""),
                    status=data.get("status", ""),
                    user_name=data.get("user_name", ""),
                    query_text=data.get("query_text", ""),
                    duration_ms=data.get("duration", 0) or 0,
                    warehouse_id=warehouse_id,
                ))

            return queries
        except Exception as e:
            logger.debug(f"Failed to list queries for warehouse {warehouse_id}: {e}")
            return []
