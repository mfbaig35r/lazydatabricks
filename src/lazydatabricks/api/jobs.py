"""Job and Run operations — list, detail, rerun, cancel.

All methods return normalized model objects from lazydatabricks.models.job.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from lazydatabricks.api.client import DatabricksClient
from lazydatabricks.models.job import JobSummary, RunDetail, RunResult, RunState, RunSummary, TaskSummary

logger = logging.getLogger(__name__)


class JobOps:
    """Job and Run API operations."""

    def __init__(self, client: DatabricksClient) -> None:
        self._client = client

    # ─── Jobs ───────────────────────────────────────────────────

    def list_jobs(self, limit: int = 100, name_filter: Optional[str] = None) -> list[JobSummary]:
        """List jobs in the workspace.

        Args:
            limit: Maximum jobs to return.
            name_filter: Optional substring filter on job name.

        Returns:
            List of JobSummary, sorted by name.
        """
        try:
            kwargs = {"limit": limit}
            if name_filter:
                kwargs["name"] = name_filter

            jobs = list(self._client.sdk.jobs.list(**kwargs))
        except Exception as e:
            logger.error(f"Failed to list jobs: {e}")
            return []

        summaries = []
        for j in jobs:
            try:
                data = j.as_dict() if hasattr(j, "as_dict") else j.__dict__
                summaries.append(JobSummary.from_api(data, self._client.host))
            except Exception as e:
                logger.warning(f"Failed to parse job: {e}")

        summaries.sort(key=lambda j: j.name.lower())
        return summaries

    def get_job(self, job_id: int) -> Optional[JobSummary]:
        """Get a single job by ID."""
        try:
            j = self._client.sdk.jobs.get(job_id=job_id)
            data = j.as_dict() if hasattr(j, "as_dict") else j.__dict__
            return JobSummary.from_api(data, self._client.host)
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            return None

    # ─── Runs ───────────────────────────────────────────────────

    def list_runs(
        self,
        job_id: Optional[int] = None,
        active_only: bool = False,
        limit: int = 25,
    ) -> list[RunSummary]:
        """List runs, optionally filtered by job.

        Args:
            job_id: Filter to runs for this job.
            active_only: Only return active (non-terminal) runs.
            limit: Maximum runs to return.

        Returns:
            List of RunSummary, most recent first.
        """
        try:
            kwargs: dict = {"limit": limit}
            if job_id is not None:
                kwargs["job_id"] = job_id
            if active_only:
                kwargs["active_only"] = True

            runs = list(self._client.sdk.jobs.list_runs(**kwargs))
        except Exception as e:
            logger.error(f"Failed to list runs: {e}")
            return []

        summaries = []
        for r in runs:
            try:
                data = r.as_dict() if hasattr(r, "as_dict") else r.__dict__
                summaries.append(RunSummary.from_api(data, self._client.host))
            except Exception as e:
                logger.warning(f"Failed to parse run: {e}")

        # Already sorted by most recent from API, but ensure it
        summaries.sort(key=lambda r: r.started_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return summaries

    def get_run(self, run_id: int) -> Optional[RunSummary]:
        """Get a single run by ID."""
        try:
            r = self._client.sdk.jobs.get_run(run_id=run_id)
            data = r.as_dict() if hasattr(r, "as_dict") else r.__dict__
            return RunSummary.from_api(data, self._client.host)
        except Exception as e:
            logger.error(f"Failed to get run {run_id}: {e}")
            return None

    def get_run_detail(self, run_id: int) -> Optional[RunDetail]:
        """Get extended run detail including output and tasks.

        This makes additional API calls for output/error content.
        """
        try:
            r = self._client.sdk.jobs.get_run(run_id=run_id)
            data = r.as_dict() if hasattr(r, "as_dict") else r.__dict__

            # Build base summary fields
            summary = RunSummary.from_api(data, self._client.host)

            # Try to get output
            full_error = ""
            output_text = ""
            output_truncated = False
            try:
                output = self._client.sdk.jobs.get_run_output(run_id=run_id)
                if output.error:
                    full_error = output.error
                if output.error_trace:
                    full_error = output.error_trace
                if hasattr(output, "notebook_output") and output.notebook_output:
                    output_text = output.notebook_output.result or ""
                    output_truncated = output.notebook_output.truncated or False
            except Exception as e:
                logger.debug(f"Could not fetch output for run {run_id}: {e}")

            # Parse tasks
            tasks = []
            for t in data.get("tasks", []):
                t_state_str = t.get("state", {}).get("life_cycle_state", "UNKNOWN")
                t_result_str = t.get("state", {}).get("result_state")
                try:
                    t_state = RunState(t_state_str)
                except ValueError:
                    t_state = RunState.UNKNOWN
                t_result = None
                if t_result_str:
                    try:
                        t_result = RunResult(t_result_str)
                    except ValueError:
                        t_result = RunResult.UNKNOWN

                tasks.append(TaskSummary(
                    task_key=t.get("task_key", ""),
                    state=t_state,
                    result=t_result,
                    duration_ms=t.get("execution_duration", 0) or 0,
                    error_snippet=(t.get("state", {}).get("state_message", ""))[:200],
                    cluster_id=t.get("existing_cluster_id", ""),
                ))

            return RunDetail(
                # Inherit all RunSummary fields
                run_id=summary.run_id,
                job_id=summary.job_id,
                run_name=summary.run_name,
                state=summary.state,
                result=summary.result,
                state_message=summary.state_message,
                started_at=summary.started_at,
                ended_at=summary.ended_at,
                setup_duration_ms=summary.setup_duration_ms,
                execution_duration_ms=summary.execution_duration_ms,
                trigger=summary.trigger,
                cluster_id=summary.cluster_id,
                notebook_path=summary.notebook_path,
                task_key=summary.task_key,
                error_snippet=summary.error_snippet,
                parameters=summary.parameters,
                run_page_url=summary.run_page_url,
                ui_url=summary.ui_url,
                # Extended fields
                full_error=full_error,
                output_text=output_text,
                output_truncated=output_truncated,
                tasks=tasks,
            )

        except Exception as e:
            logger.error(f"Failed to get run detail {run_id}: {e}")
            return None

    # ─── Actions ────────────────────────────────────────────────

    def cancel_run(self, run_id: int) -> dict:
        """Cancel an active run."""
        if self._client.is_read_only:
            return {"status": "error", "error": "Read-only mode — arm to enable actions"}

        try:
            self._client.sdk.jobs.cancel_run(run_id=run_id)
            logger.info(f"Cancel requested for run {run_id}")
            return {"status": "cancelled", "run_id": run_id}
        except Exception as e:
            logger.error(f"Failed to cancel run {run_id}: {e}")
            return {"status": "error", "error": str(e)}

    def rerun(self, run_id: int) -> dict:
        """Re-run a completed run with the same parameters."""
        if self._client.is_read_only:
            return {"status": "error", "error": "Read-only mode — arm to enable actions"}

        try:
            result = self._client.sdk.jobs.repair_run(run_id=run_id, rerun_all_failed_tasks=True)
            new_run_id = result.repair_id if hasattr(result, "repair_id") else None
            logger.info(f"Rerun requested for run {run_id}, repair_id={new_run_id}")
            return {
                "status": "rerun_submitted",
                "original_run_id": run_id,
                "repair_id": new_run_id,
            }
        except Exception as e:
            logger.error(f"Failed to rerun {run_id}: {e}")
            return {"status": "error", "error": str(e)}

    def run_now(self, job_id: int) -> dict:
        """Trigger a job to run immediately."""
        if self._client.is_read_only:
            return {"status": "error", "error": "Read-only mode — arm to enable actions"}

        try:
            result = self._client.sdk.jobs.run_now(job_id=job_id)
            run_id = result.run_id if hasattr(result, "run_id") else None
            logger.info(f"Run now requested for job {job_id}, run_id={run_id}")
            return {"status": "submitted", "job_id": job_id, "run_id": run_id}
        except Exception as e:
            logger.error(f"Failed to run job {job_id}: {e}")
            return {"status": "error", "error": str(e)}

    # ─── Aggregations (for Health snapshot) ─────────────────────

    def get_active_runs_count(self) -> int:
        """Count of currently active runs across all jobs."""
        try:
            runs = list(self._client.sdk.jobs.list_runs(active_only=True, limit=100))
            return len(runs)
        except Exception:
            return 0

    def get_recent_failures(self, hours: int = 24, limit: int = 10) -> list[RunSummary]:
        """Get runs that failed in the last N hours."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            cutoff_ms = int(cutoff.timestamp() * 1000)

            runs = list(self._client.sdk.jobs.list_runs(
                limit=limit,
                start_time_from=cutoff_ms,
            ))

            failures = []
            for r in runs:
                data = r.as_dict() if hasattr(r, "as_dict") else r.__dict__
                summary = RunSummary.from_api(data, self._client.host)
                if summary.result and summary.result.is_failure:
                    failures.append(summary)

            return failures
        except Exception as e:
            logger.debug(f"Failed to get recent failures: {e}")
            return []
