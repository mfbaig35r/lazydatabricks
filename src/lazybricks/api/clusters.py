"""Cluster operations — list, start, stop, restart, events.

All methods return normalized model objects from lazybricks.models.cluster.
"""

from __future__ import annotations

import logging
from typing import Optional

from lazybricks.api.client import DatabricksClient
from lazybricks.models.cluster import ClusterEvent, ClusterSummary

logger = logging.getLogger(__name__)


class ClusterOps:
    """Cluster API operations."""

    def __init__(self, client: DatabricksClient) -> None:
        self._client = client

    def list_all(self) -> list[ClusterSummary]:
        """List all clusters in the workspace.

        Returns:
            List of ClusterSummary, sorted by state (active first) then name.
        """
        try:
            clusters = list(self._client.sdk.clusters.list())
        except Exception as e:
            logger.error(f"Failed to list clusters: {e}")
            return []

        summaries = []
        for c in clusters:
            try:
                data = c.as_dict() if hasattr(c, "as_dict") else c.__dict__
                summary = ClusterSummary.from_api(data, self._client.host)
                summaries.append(summary)
            except Exception as e:
                logger.warning(f"Failed to parse cluster: {e}")

        # Sort: active clusters first, then by name
        state_order = {"RUNNING": 0, "RESTARTING": 1, "RESIZING": 1, "PENDING": 2}
        summaries.sort(key=lambda c: (state_order.get(c.state.value, 9), c.name.lower()))

        return summaries

    def get(self, cluster_id: str) -> Optional[ClusterSummary]:
        """Get a single cluster by ID."""
        try:
            c = self._client.sdk.clusters.get(cluster_id=cluster_id)
            data = c.as_dict() if hasattr(c, "as_dict") else c.__dict__
            return ClusterSummary.from_api(data, self._client.host)
        except Exception as e:
            logger.error(f"Failed to get cluster {cluster_id}: {e}")
            return None

    def start(self, cluster_id: str) -> dict:
        """Start a terminated cluster.

        Returns:
            {"status": "started"} or {"status": "error", "error": "..."}
        """
        if self._client.is_read_only:
            return {"status": "error", "error": "Read-only mode — arm to enable actions"}

        try:
            self._client.sdk.clusters.start(cluster_id=cluster_id)
            logger.info(f"Start requested for cluster {cluster_id}")
            return {"status": "started", "cluster_id": cluster_id}
        except Exception as e:
            logger.error(f"Failed to start cluster {cluster_id}: {e}")
            return {"status": "error", "error": str(e)}

    def terminate(self, cluster_id: str) -> dict:
        """Terminate a running cluster."""
        if self._client.is_read_only:
            return {"status": "error", "error": "Read-only mode — arm to enable actions"}

        try:
            self._client.sdk.clusters.delete(cluster_id=cluster_id)
            logger.info(f"Terminate requested for cluster {cluster_id}")
            return {"status": "terminated", "cluster_id": cluster_id}
        except Exception as e:
            logger.error(f"Failed to terminate cluster {cluster_id}: {e}")
            return {"status": "error", "error": str(e)}

    def restart(self, cluster_id: str) -> dict:
        """Restart a running cluster (destructive — requires arm)."""
        if self._client.is_read_only:
            return {"status": "error", "error": "Read-only mode — arm to enable actions"}

        try:
            self._client.sdk.clusters.restart(cluster_id=cluster_id)
            logger.info(f"Restart requested for cluster {cluster_id}")
            return {"status": "restarting", "cluster_id": cluster_id}
        except Exception as e:
            logger.error(f"Failed to restart cluster {cluster_id}: {e}")
            return {"status": "error", "error": str(e)}

    def get_events(
        self,
        cluster_id: str,
        limit: int = 50,
    ) -> list[ClusterEvent]:
        """Get recent cluster events.

        Returns:
            List of ClusterEvent, most recent first.
        """
        try:
            from datetime import datetime, timezone

            events_response = self._client.sdk.clusters.events(
                cluster_id=cluster_id,
                limit=limit,
            )
            events = []
            for page in events_response:
                if hasattr(page, "events") and page.events:
                    for e in page.events:
                        ts = datetime.now(timezone.utc)
                        if hasattr(e, "timestamp") and e.timestamp:
                            ts = datetime.fromtimestamp(e.timestamp / 1000.0, tz=timezone.utc)
                        events.append(ClusterEvent(
                            timestamp=ts,
                            event_type=str(e.type.value) if hasattr(e, "type") and e.type else "UNKNOWN",
                            details=str(e.details) if hasattr(e, "details") else "",
                        ))
                # The SDK returns paginated results; we just want the first page
                break

            return events
        except Exception as e:
            logger.error(f"Failed to get events for cluster {cluster_id}: {e}")
            return []
