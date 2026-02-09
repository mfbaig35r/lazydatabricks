"""Pipeline operations — list, detail, start, stop.

All methods return normalized model objects from lazydatabricks.models.pipeline.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from lazydatabricks.api.client import DatabricksClient
from lazydatabricks.models.pipeline import (
    PipelineSummary,
    UpdateDetail,
    UpdateSummary,
    UpdateState,
)

logger = logging.getLogger(__name__)


class PipelineOps:
    """Pipeline API operations."""

    def __init__(self, client: DatabricksClient) -> None:
        self._client = client

    # ─── Pipelines ───────────────────────────────────────────────

    def list_pipelines(self, limit: int = 100) -> list[PipelineSummary]:
        """List pipelines in the workspace.

        Args:
            limit: Maximum pipelines to return.

        Returns:
            List of PipelineSummary, sorted by name.
        """
        try:
            pipelines = list(self._client.sdk.pipelines.list_pipelines(max_results=limit))
        except Exception as e:
            logger.error(f"Failed to list pipelines: {e}")
            return []

        summaries = []
        for p in pipelines:
            try:
                data = p.as_dict() if hasattr(p, "as_dict") else p.__dict__
                summaries.append(PipelineSummary.from_api(data, self._client.host))
            except Exception as e:
                logger.warning(f"Failed to parse pipeline: {e}")

        summaries.sort(key=lambda p: p.name.lower())
        return summaries

    def get_pipeline(self, pipeline_id: str) -> Optional[PipelineSummary]:
        """Get a single pipeline by ID."""
        try:
            p = self._client.sdk.pipelines.get(pipeline_id=pipeline_id)
            data = p.as_dict() if hasattr(p, "as_dict") else p.__dict__
            return PipelineSummary.from_api(data, self._client.host)
        except Exception as e:
            logger.error(f"Failed to get pipeline {pipeline_id}: {e}")
            return None

    # ─── Updates ───────────────────────────────────────────────

    def list_updates(
        self,
        pipeline_id: str,
        limit: int = 25,
    ) -> list[UpdateSummary]:
        """List updates for a pipeline.

        Args:
            pipeline_id: The pipeline to get updates for.
            limit: Maximum updates to return.

        Returns:
            List of UpdateSummary, most recent first.
        """
        try:
            result = self._client.sdk.pipelines.list_updates(
                pipeline_id=pipeline_id,
                max_results=limit,
            )
            updates = result.updates if hasattr(result, "updates") and result.updates else []
        except Exception as e:
            logger.error(f"Failed to list updates for pipeline {pipeline_id}: {e}")
            return []

        summaries = []
        for u in updates:
            try:
                data = u.as_dict() if hasattr(u, "as_dict") else u.__dict__
                summaries.append(UpdateSummary.from_api(data, pipeline_id))
            except Exception as e:
                logger.warning(f"Failed to parse update: {e}")

        # Already sorted by most recent from API, but ensure it
        # Use a default datetime for None values to ensure stable sorting
        min_dt = datetime(1970, 1, 1, tzinfo=timezone.utc)
        summaries.sort(
            key=lambda u: u.creation_time or u.start_time or u.end_time or min_dt,
            reverse=True,
        )
        return summaries

    def get_update(self, pipeline_id: str, update_id: str) -> Optional[UpdateDetail]:
        """Get extended update detail including events.

        Args:
            pipeline_id: The pipeline ID.
            update_id: The update ID.

        Returns:
            UpdateDetail with events and error message.
        """
        try:
            result = self._client.sdk.pipelines.get_update(
                pipeline_id=pipeline_id,
                update_id=update_id,
            )
            update_data = result.update if hasattr(result, "update") else result
            data = update_data.as_dict() if hasattr(update_data, "as_dict") else update_data.__dict__

            # Build base summary
            summary = UpdateSummary.from_api(data, pipeline_id)

            # Get events if available
            events = []
            try:
                events_result = self._client.sdk.pipelines.list_pipeline_events(
                    pipeline_id=pipeline_id,
                    filter=f"update_id = '{update_id}'",
                    max_results=50,
                )
                if hasattr(events_result, "events") and events_result.events:
                    for e in events_result.events:
                        event_data = e.as_dict() if hasattr(e, "as_dict") else e.__dict__
                        events.append(event_data)
            except Exception as e:
                logger.debug(f"Could not fetch events for update {update_id}: {e}")

            # Extract error message from events
            error_message = ""
            for event in events:
                if event.get("level") == "ERROR" or event.get("event_type") == "update_progress":
                    msg = event.get("message", "")
                    if "FAILED" in msg or "error" in msg.lower():
                        error_message = msg
                        break
                error_detail = event.get("error", {})
                if error_detail:
                    exceptions = error_detail.get("exceptions", [])
                    if exceptions:
                        error_message = exceptions[0].get("message", "")
                        break

            return UpdateDetail(
                # Inherit all UpdateSummary fields
                update_id=summary.update_id,
                pipeline_id=summary.pipeline_id,
                state=summary.state,
                cause=summary.cause,
                creation_time=summary.creation_time,
                start_time=summary.start_time,
                end_time=summary.end_time,
                full_refresh=summary.full_refresh,
                full_refresh_selection=summary.full_refresh_selection,
                cluster_id=summary.cluster_id,
                # Extended fields
                events=events,
                error_message=error_message,
            )

        except Exception as e:
            logger.error(f"Failed to get update detail {update_id}: {e}")
            return None

    # ─── Actions ────────────────────────────────────────────────

    def start_update(self, pipeline_id: str, full_refresh: bool = False) -> dict:
        """Start a pipeline update.

        Args:
            pipeline_id: The pipeline to start.
            full_refresh: Whether to do a full refresh.

        Returns:
            Dict with status and update_id.
        """
        if self._client.is_read_only:
            return {"status": "error", "error": "Read-only mode — arm to enable actions"}

        try:
            result = self._client.sdk.pipelines.start_update(
                pipeline_id=pipeline_id,
                full_refresh=full_refresh,
            )
            update_id = result.update_id if hasattr(result, "update_id") else None
            logger.info(f"Started update for pipeline {pipeline_id}, update_id={update_id}")
            return {"status": "started", "pipeline_id": pipeline_id, "update_id": update_id}
        except Exception as e:
            logger.error(f"Failed to start pipeline {pipeline_id}: {e}")
            return {"status": "error", "error": str(e)}

    def stop(self, pipeline_id: str) -> dict:
        """Stop a running pipeline.

        Args:
            pipeline_id: The pipeline to stop.

        Returns:
            Dict with status.
        """
        if self._client.is_read_only:
            return {"status": "error", "error": "Read-only mode — arm to enable actions"}

        try:
            self._client.sdk.pipelines.stop(pipeline_id=pipeline_id)
            logger.info(f"Stop requested for pipeline {pipeline_id}")
            return {"status": "stopped", "pipeline_id": pipeline_id}
        except Exception as e:
            logger.error(f"Failed to stop pipeline {pipeline_id}: {e}")
            return {"status": "error", "error": str(e)}

    # ─── Aggregations (for Health snapshot) ─────────────────────

    def get_active_pipelines_count(self) -> int:
        """Count of currently running pipelines."""
        try:
            pipelines = list(self._client.sdk.pipelines.list_pipelines(max_results=100))
            return sum(
                1 for p in pipelines
                if hasattr(p, "state") and p.state == "RUNNING"
            )
        except Exception:
            return 0

    def get_failed_pipelines(self, limit: int = 10) -> list[PipelineSummary]:
        """Get pipelines that are in FAILED state."""
        try:
            pipelines = list(self._client.sdk.pipelines.list_pipelines(max_results=limit))
            failed = []
            for p in pipelines:
                data = p.as_dict() if hasattr(p, "as_dict") else p.__dict__
                summary = PipelineSummary.from_api(data, self._client.host)
                if summary.state.name == "FAILED" or (
                    summary.last_update_state and summary.last_update_state.is_failure
                ):
                    failed.append(summary)
            return failed
        except Exception as e:
            logger.debug(f"Failed to get failed pipelines: {e}")
            return []
