"""Health snapshot builder — assembles the Home screen data.

Pulls from clusters, jobs, and warehouses APIs to build
the single-screen "is everything OK?" view.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from lazydatabricks.api.client import DatabricksClient
from lazydatabricks.api.clusters import ClusterOps
from lazydatabricks.api.jobs import JobOps
from lazydatabricks.api.warehouses import WarehouseOps
from lazydatabricks.models.cluster import ClusterFlag, ClusterState
from lazydatabricks.models.health import HealthSnapshot, SparkStatus

logger = logging.getLogger(__name__)


class HealthBuilder:
    """Builds the HealthSnapshot for the Home screen.

    Aggregates data from multiple API calls into a single model.
    Each section is independently try/except'd so partial failures
    don't break the whole snapshot.
    """

    def __init__(self, client: DatabricksClient) -> None:
        self._client = client
        self._clusters = ClusterOps(client)
        self._jobs = JobOps(client)
        self._warehouses = WarehouseOps(client)

    def build(self) -> HealthSnapshot:
        """Build a complete health snapshot.

        Calls multiple APIs in sequence. Each section is isolated
        so a failure in one doesn't prevent the rest from loading.
        """
        snapshot = HealthSnapshot(
            workspace_host=self._client.config.host_short,
            active_profile=self._client.config.profile_name or "(env)",
            cluster_id=self._client.cluster_id,
            snapshot_at=datetime.now(timezone.utc),
        )

        # 1. Connection identity
        self._build_identity(snapshot)

        # 2. Spark connectivity (only if cluster_id is set)
        self._build_spark_status(snapshot)

        # 3. Cluster health
        self._build_cluster_health(snapshot)

        # 4. Job health
        self._build_job_health(snapshot)

        # 5. Warehouse health
        self._build_warehouse_health(snapshot)

        return snapshot

    def _build_identity(self, snapshot: HealthSnapshot) -> None:
        """Populate workspace user identity."""
        try:
            result = self._client.test_connection()
            if result["status"] == "ok":
                snapshot.workspace_user = result.get("user", "")
        except Exception as e:
            logger.debug(f"Identity check failed: {e}")

    def _build_spark_status(self, snapshot: HealthSnapshot) -> None:
        """Check Spark session connectivity (requires databricks-connect)."""
        if not self._client.cluster_id:
            snapshot.spark_status = SparkStatus.NO_CLUSTER
            return

        try:
            # Try to import and use databricks-connect for "Spark-true" health
            from databricks.connect import DatabricksSession

            session = DatabricksSession.builder.remote(
                host=self._client.config.host,
                token=self._client.config.token,
                cluster_id=self._client.cluster_id,
            ).getOrCreate()

            result = session.sql(
                "SELECT current_user() as user, current_catalog() as catalog"
            ).collect()

            row = result[0]
            snapshot.spark_status = SparkStatus.CONNECTED
            snapshot.spark_version = session.version
            snapshot.current_catalog = row["catalog"]
            snapshot.workspace_user = snapshot.workspace_user or row["user"]
            snapshot.validated_at = datetime.now(timezone.utc)

            # Get cluster name for display
            cluster = self._clusters.get(self._client.cluster_id)
            if cluster:
                snapshot.cluster_name = cluster.name
                snapshot.cluster_state = cluster.state.value

        except ImportError:
            # databricks-connect not installed — fall back to API-only check
            logger.debug("databricks-connect not available, using API-only health check")
            cluster = self._clusters.get(self._client.cluster_id)
            if cluster:
                snapshot.cluster_name = cluster.name
                snapshot.cluster_state = cluster.state.value
                if cluster.state == ClusterState.RUNNING:
                    snapshot.spark_status = SparkStatus.CONNECTED  # API-true, not Spark-true
                else:
                    snapshot.spark_status = SparkStatus.DISCONNECTED
            else:
                snapshot.spark_status = SparkStatus.DISCONNECTED

        except Exception as e:
            logger.debug(f"Spark health check failed: {e}")
            snapshot.spark_status = SparkStatus.STALE
            # Still try to get cluster info via API
            try:
                cluster = self._clusters.get(self._client.cluster_id)
                if cluster:
                    snapshot.cluster_name = cluster.name
                    snapshot.cluster_state = cluster.state.value
            except Exception:
                pass

    def _build_cluster_health(self, snapshot: HealthSnapshot) -> None:
        """Aggregate cluster health metrics."""
        try:
            clusters = self._clusters.list_all()
            snapshot.total_clusters = len(clusters)
            snapshot.running_clusters = sum(
                1 for c in clusters if c.state == ClusterState.RUNNING
            )
            snapshot.idle_burn_clusters = sum(
                1 for c in clusters if ClusterFlag.IDLE_BURN in c.flags
            )
        except Exception as e:
            logger.debug(f"Cluster health check failed: {e}")

    def _build_job_health(self, snapshot: HealthSnapshot) -> None:
        """Aggregate job health metrics."""
        try:
            snapshot.active_runs_count = self._jobs.get_active_runs_count()
        except Exception as e:
            logger.debug(f"Active runs count failed: {e}")

        try:
            failures = self._jobs.get_recent_failures(hours=24)
            snapshot.recent_failure_count = len(failures)
            if failures:
                most_recent = failures[0]
                snapshot.last_failure_run_id = most_recent.run_id
                snapshot.last_failure_job_name = most_recent.run_name
                snapshot.last_failure_at = most_recent.ended_at or most_recent.started_at
                snapshot.last_failure_snippet = most_recent.error_snippet
        except Exception as e:
            logger.debug(f"Recent failures check failed: {e}")

    def _build_warehouse_health(self, snapshot: HealthSnapshot) -> None:
        """Aggregate warehouse health metrics."""
        try:
            warehouses = self._warehouses.list_all()
            snapshot.total_warehouses = len(warehouses)
            snapshot.running_warehouses = sum(
                1 for w in warehouses if w.state.is_active
            )
        except Exception as e:
            logger.debug(f"Warehouse health check failed: {e}")
