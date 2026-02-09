"""Log fetching — best-effort access to run output and cluster logs.

This is the "killer feature" of LazyDatabricks, but also the most
constrained by Databricks API limitations.

v1 strategy:
1. Run output/error trace via Jobs API (most reliable)
2. Cluster driver logs when available
3. "Open in Databricks UI" fallback link always provided

v2 aspirations:
- DBFS log tailing for cluster driver logs
- Streaming via long-poll or websocket (if Databricks ever supports it)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from lazydatabricks.api.client import DatabricksClient

logger = logging.getLogger(__name__)


class LogSeverity(str, Enum):
    """Log line severity levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"

    @property
    def display_style(self) -> str:
        return {
            LogSeverity.ERROR: "red bold",
            LogSeverity.WARN: "yellow",
            LogSeverity.INFO: "white",
            LogSeverity.DEBUG: "dim",
        }.get(self, "white")


@dataclass
class LogLine:
    """A single parsed log line."""
    line_number: int
    text: str
    severity: LogSeverity = LogSeverity.UNKNOWN
    timestamp: Optional[datetime] = None
    source: str = ""  # "run_output", "driver_log", "error_trace"
    bookmarked: bool = False


@dataclass
class LogBlock:
    """A block of log lines from a single source."""
    source: str  # "run_output", "error_trace", "driver_stdout", "driver_stderr"
    lines: list[LogLine] = field(default_factory=list)
    raw_text: str = ""
    truncated: bool = False
    fallback_url: str = ""  # "Open in Databricks" link

    @property
    def line_count(self) -> int:
        return len(self.lines)

    def filter_by_severity(self, *severities: LogSeverity) -> list[LogLine]:
        """Return lines matching any of the given severity levels."""
        return [l for l in self.lines if l.severity in severities]

    def search(self, pattern: str) -> list[LogLine]:
        """Search lines by regex pattern."""
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
            return [l for l in self.lines if compiled.search(l.text)]
        except re.error:
            # Fall back to substring match
            pattern_lower = pattern.lower()
            return [l for l in self.lines if pattern_lower in l.text.lower()]


# Regex patterns for severity detection
_SEVERITY_PATTERNS = [
    (re.compile(r'\b(ERROR|FATAL|SEVERE)\b', re.IGNORECASE), LogSeverity.ERROR),
    (re.compile(r'\b(WARN(?:ING)?)\b', re.IGNORECASE), LogSeverity.WARN),
    (re.compile(r'\b(INFO)\b', re.IGNORECASE), LogSeverity.INFO),
    (re.compile(r'\b(DEBUG|TRACE)\b', re.IGNORECASE), LogSeverity.DEBUG),
]

# Common log timestamp patterns
_TIMESTAMP_PATTERN = re.compile(
    r'(\d{4}[-/]\d{2}[-/]\d{2}[\sT]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)'
)


def _parse_severity(text: str) -> LogSeverity:
    """Detect severity from a log line."""
    for pattern, severity in _SEVERITY_PATTERNS:
        if pattern.search(text):
            return severity
    return LogSeverity.UNKNOWN


def _parse_log_lines(raw: str, source: str) -> list[LogLine]:
    """Parse raw text into structured LogLine objects."""
    lines = []
    for i, text in enumerate(raw.splitlines(), start=1):
        if not text.strip():
            continue

        severity = _parse_severity(text)

        # Try to extract timestamp
        timestamp = None
        ts_match = _TIMESTAMP_PATTERN.search(text)
        if ts_match:
            try:
                ts_str = ts_match.group(1)
                # Normalize common formats
                ts_str = ts_str.replace("/", "-").replace("T", " ").rstrip("Z")
                if "+" not in ts_str and "-" not in ts_str[10:]:
                    ts_str += "+00:00"
                timestamp = datetime.fromisoformat(ts_str)
            except (ValueError, IndexError):
                pass

        lines.append(LogLine(
            line_number=i,
            text=text,
            severity=severity,
            timestamp=timestamp,
            source=source,
        ))

    return lines


class LogOps:
    """Log fetching operations."""

    def __init__(self, client: DatabricksClient) -> None:
        self._client = client

    def get_run_logs(self, run_id: int) -> list[LogBlock]:
        """Get all available logs for a run.

        Tries multiple sources in order:
        1. Run output (notebook result)
        2. Error trace (if failed)
        3. Cluster driver logs (if accessible)

        Always includes a fallback URL.

        Returns:
            List of LogBlock objects from different sources.
        """
        blocks: list[LogBlock] = []

        # Get run info for context
        try:
            run = self._client.sdk.jobs.get_run(run_id=run_id)
            run_data = run.as_dict() if hasattr(run, "as_dict") else run.__dict__
            fallback_url = run_data.get("run_page_url", "")
        except Exception as e:
            logger.error(f"Failed to get run {run_id}: {e}")
            return [LogBlock(
                source="error",
                raw_text=f"Failed to fetch run: {e}",
                lines=[LogLine(line_number=1, text=f"Failed to fetch run: {e}", severity=LogSeverity.ERROR, source="error")],
            )]

        # Source 1: Run output
        try:
            output = self._client.sdk.jobs.get_run_output(run_id=run_id)

            # Error trace (most useful for failures)
            if output.error_trace:
                lines = _parse_log_lines(output.error_trace, "error_trace")
                blocks.append(LogBlock(
                    source="error_trace",
                    lines=lines,
                    raw_text=output.error_trace,
                    fallback_url=fallback_url,
                ))

            # Error message
            if output.error and not output.error_trace:
                lines = _parse_log_lines(output.error, "error")
                blocks.append(LogBlock(
                    source="error",
                    lines=lines,
                    raw_text=output.error,
                    fallback_url=fallback_url,
                ))

            # Notebook output
            if hasattr(output, "notebook_output") and output.notebook_output:
                result = output.notebook_output.result or ""
                if result:
                    lines = _parse_log_lines(result, "run_output")
                    blocks.append(LogBlock(
                        source="run_output",
                        lines=lines,
                        raw_text=result,
                        truncated=output.notebook_output.truncated or False,
                        fallback_url=fallback_url,
                    ))

            # Logs (some job types return logs in metadata)
            if hasattr(output, "logs") and output.logs:
                lines = _parse_log_lines(output.logs, "run_logs")
                blocks.append(LogBlock(
                    source="run_logs",
                    lines=lines,
                    raw_text=output.logs,
                    fallback_url=fallback_url,
                ))

        except Exception as e:
            logger.debug(f"Could not fetch run output for {run_id}: {e}")

        # Source 2: Cluster driver logs (if we know the cluster)
        cluster_id = run_data.get("cluster_instance", {}).get("cluster_id", "")
        if cluster_id:
            driver_blocks = self.get_cluster_driver_logs(cluster_id)
            blocks.extend(driver_blocks)

        # Always include fallback
        if not blocks:
            blocks.append(LogBlock(
                source="no_logs",
                lines=[LogLine(
                    line_number=1,
                    text="No logs available via API. Use the link below to view in Databricks UI.",
                    severity=LogSeverity.INFO,
                    source="no_logs",
                )],
                raw_text="No logs available via API.",
                fallback_url=fallback_url,
            ))

        return blocks

    def get_cluster_driver_logs(self, cluster_id: str) -> list[LogBlock]:
        """Attempt to fetch cluster driver logs.

        This is best-effort — availability depends on cluster config,
        log delivery settings, and permissions.

        Returns:
            List of LogBlock (stdout + stderr if available).
        """
        blocks: list[LogBlock] = []

        try:
            # Try the cluster log delivery API
            log_response = self._client.sdk.clusters.get(cluster_id=cluster_id)
            log_data = log_response.as_dict() if hasattr(log_response, "as_dict") else log_response.__dict__

            # Build fallback URL
            host = self._client.host
            fallback_url = f"{host}/#setting/clusters/{cluster_id}/driverLogs"

            # Check if cluster has log delivery configured
            log_conf = log_data.get("cluster_log_conf")
            if log_conf:
                blocks.append(LogBlock(
                    source="driver_log_info",
                    lines=[LogLine(
                        line_number=1,
                        text=f"Cluster logs configured: {log_conf}. View in Databricks UI.",
                        severity=LogSeverity.INFO,
                        source="driver_log_info",
                    )],
                    raw_text=f"Log delivery configured: {log_conf}",
                    fallback_url=fallback_url,
                ))
            else:
                blocks.append(LogBlock(
                    source="driver_log_info",
                    lines=[LogLine(
                        line_number=1,
                        text="No log delivery configured. View driver logs in Databricks UI.",
                        severity=LogSeverity.INFO,
                        source="driver_log_info",
                    )],
                    fallback_url=fallback_url,
                ))

        except Exception as e:
            logger.debug(f"Could not access driver logs for cluster {cluster_id}: {e}")

        return blocks
