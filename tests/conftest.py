"""Pytest fixtures for LazyBricks tests.

Provides mock fixtures for API layer to avoid hitting real Databricks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from lazybricks.api.client import DatabricksClient
from lazybricks.api.guard import ArmedGuard
from lazybricks.models.cluster import ClusterSummary, ClusterState, ClusterFlag
from lazybricks.models.config import LazyBricksConfig, DatabricksProfile, AuthMethod
from lazybricks.models.health import HealthSnapshot, SparkStatus
from lazybricks.models.job import JobSummary, RunSummary, RunState, RunResult, TriggerType
from lazybricks.models.warehouse import WarehouseSummary, WarehouseState


# ─── Configuration Fixtures ──────────────────────────────────────


@pytest.fixture
def mock_config() -> LazyBricksConfig:
    """Create a mock LazyBricksConfig."""
    return LazyBricksConfig(
        host="https://test-workspace.cloud.databricks.com",
        token="dapi_test_token",
        cluster_id="test-cluster-123",
        profile_name="test-profile",
        auth_method=AuthMethod.PAT,
        read_only=True,
        available_profiles=[
            DatabricksProfile(
                name="test-profile",
                host="https://test-workspace.cloud.databricks.com",
                token="dapi_test_token",
                cluster_id="test-cluster-123",
            ),
            DatabricksProfile(
                name="staging",
                host="https://staging.cloud.databricks.com",
                token="dapi_staging_token",
            ),
        ],
    )


@pytest.fixture
def mock_client(mock_config: LazyBricksConfig) -> MagicMock:
    """Create a mock DatabricksClient."""
    client = MagicMock(spec=DatabricksClient)
    client.config = mock_config
    client.host = mock_config.host
    client.is_read_only = mock_config.read_only
    client.test_connection.return_value = {
        "status": "ok",
        "user": "test-user@example.com",
    }
    return client


# ─── ArmedGuard Fixtures ─────────────────────────────────────────


@pytest.fixture
def armed_guard() -> ArmedGuard:
    """Create a fresh ArmedGuard instance."""
    return ArmedGuard(ttl_seconds=30)


@pytest.fixture
def armed_guard_active() -> ArmedGuard:
    """Create an ArmedGuard that is already armed."""
    guard = ArmedGuard(ttl_seconds=30)
    guard.arm()
    return guard


# ─── Model Fixtures ──────────────────────────────────────────────


@pytest.fixture
def sample_clusters() -> list[ClusterSummary]:
    """Create sample cluster data for testing."""
    now = datetime.now(timezone.utc)
    return [
        ClusterSummary(
            id="cluster-001",
            name="Production ETL",
            state=ClusterState.RUNNING,
            node_type_id="m5.xlarge",
            num_workers=4,
            autoscale_min=2,
            autoscale_max=8,
            started_at=now,
            last_activity_at=now,
            spark_version="13.3.x-scala2.12",
            creator="user@example.com",
            flags=[ClusterFlag.LONG_RUNNING],
            ui_url="https://test-workspace.cloud.databricks.com/#setting/clusters/cluster-001",
        ),
        ClusterSummary(
            id="cluster-002",
            name="Dev Cluster",
            state=ClusterState.TERMINATED,
            node_type_id="m5.large",
            num_workers=2,
            spark_version="14.0.x-scala2.12",
            creator="dev@example.com",
        ),
        ClusterSummary(
            id="cluster-003",
            name="Idle Cluster",
            state=ClusterState.RUNNING,
            node_type_id="m5.large",
            num_workers=2,
            started_at=now,
            flags=[ClusterFlag.IDLE_BURN],
        ),
    ]


@pytest.fixture
def sample_jobs() -> list[JobSummary]:
    """Create sample job data for testing."""
    now = datetime.now(timezone.utc)
    return [
        JobSummary(
            id=101,
            name="Daily ETL Pipeline",
            creator="user@example.com",
            schedule_cron="0 6 * * *",
            schedule_paused=False,
            last_run_state=RunState.TERMINATED,
            last_run_result=RunResult.SUCCESS,
            last_run_at=now,
            active_runs_count=0,
            ui_url="https://test-workspace.cloud.databricks.com/#job/101",
        ),
        JobSummary(
            id=102,
            name="Hourly Sync",
            creator="user@example.com",
            schedule_cron="0 * * * *",
            last_run_state=RunState.RUNNING,
            active_runs_count=1,
            ui_url="https://test-workspace.cloud.databricks.com/#job/102",
        ),
        JobSummary(
            id=103,
            name="Failed Job",
            creator="other@example.com",
            last_run_state=RunState.TERMINATED,
            last_run_result=RunResult.FAILED,
            last_run_at=now,
            ui_url="https://test-workspace.cloud.databricks.com/#job/103",
        ),
    ]


@pytest.fixture
def sample_runs() -> list[RunSummary]:
    """Create sample run data for testing."""
    now = datetime.now(timezone.utc)
    return [
        RunSummary(
            run_id=1001,
            job_id=101,
            run_name="Daily ETL Pipeline",
            state=RunState.TERMINATED,
            result=RunResult.SUCCESS,
            started_at=now,
            execution_duration_ms=300000,
            trigger=TriggerType.PERIODIC,
            notebook_path="/ETL/daily_pipeline",
        ),
        RunSummary(
            run_id=1002,
            job_id=102,
            run_name="Hourly Sync",
            state=RunState.RUNNING,
            started_at=now,
            trigger=TriggerType.PERIODIC,
        ),
        RunSummary(
            run_id=1003,
            job_id=103,
            run_name="Failed Job",
            state=RunState.TERMINATED,
            result=RunResult.FAILED,
            started_at=now,
            execution_duration_ms=60000,
            error_snippet="NullPointerException in task 0",
        ),
    ]


@pytest.fixture
def sample_warehouses() -> list[WarehouseSummary]:
    """Create sample warehouse data for testing."""
    return [
        WarehouseSummary(
            id="wh-001",
            name="Production Warehouse",
            state=WarehouseState.RUNNING,
            size="Medium",
            min_num_clusters=1,
            max_num_clusters=4,
            num_active_sessions=5,
            num_clusters=2,
            enable_serverless=True,
            auto_stop_mins=15,
            creator="admin@example.com",
        ),
        WarehouseSummary(
            id="wh-002",
            name="Dev Warehouse",
            state=WarehouseState.STOPPED,
            size="Small",
            min_num_clusters=1,
            max_num_clusters=1,
            enable_serverless=False,
        ),
    ]


@pytest.fixture
def sample_health_snapshot() -> HealthSnapshot:
    """Create a sample health snapshot for testing."""
    now = datetime.now(timezone.utc)
    return HealthSnapshot(
        workspace_host="test-workspace.cloud.databricks.com",
        workspace_user="test-user@example.com",
        active_profile="test-profile",
        spark_status=SparkStatus.CONNECTED,
        spark_version="13.3.x",
        current_catalog="main",
        cluster_id="cluster-001",
        cluster_name="Production ETL",
        cluster_state="RUNNING",
        validated_at=now,
        active_runs_count=2,
        recent_failure_count=1,
        last_failure_job_name="Failed Job",
        last_failure_at=now,
        last_failure_snippet="NullPointerException",
        total_clusters=3,
        running_clusters=2,
        idle_burn_clusters=1,
        total_warehouses=2,
        running_warehouses=1,
        snapshot_at=now,
    )


# ─── Mock Operations Fixtures ────────────────────────────────────


@pytest.fixture
def mock_cluster_ops(mock_client: MagicMock, sample_clusters: list[ClusterSummary]) -> MagicMock:
    """Create a mock ClusterOps."""
    ops = MagicMock()
    ops.list_all.return_value = sample_clusters
    ops.get.return_value = sample_clusters[0]
    ops.start.return_value = {"status": "started", "cluster_id": "cluster-002"}
    ops.terminate.return_value = {"status": "terminated", "cluster_id": "cluster-001"}
    ops.restart.return_value = {"status": "restarting", "cluster_id": "cluster-001"}
    return ops


@pytest.fixture
def mock_job_ops(
    mock_client: MagicMock,
    sample_jobs: list[JobSummary],
    sample_runs: list[RunSummary],
) -> MagicMock:
    """Create a mock JobOps."""
    ops = MagicMock()
    ops.list_jobs.return_value = sample_jobs
    ops.list_runs.return_value = sample_runs
    ops.get_job.return_value = sample_jobs[0]
    ops.get_run.return_value = sample_runs[0]
    ops.cancel_run.return_value = {"status": "cancelled", "run_id": 1002}
    ops.rerun.return_value = {"status": "rerun_submitted", "original_run_id": 1003}
    ops.run_now.return_value = {"status": "submitted", "job_id": 101, "run_id": 1004}
    return ops


@pytest.fixture
def mock_warehouse_ops(
    mock_client: MagicMock,
    sample_warehouses: list[WarehouseSummary],
) -> MagicMock:
    """Create a mock WarehouseOps."""
    ops = MagicMock()
    ops.list_all.return_value = sample_warehouses
    ops.get.return_value = sample_warehouses[0]
    ops.start.return_value = {"status": "started", "warehouse_id": "wh-002"}
    ops.stop.return_value = {"status": "stopped", "warehouse_id": "wh-001"}
    return ops


@pytest.fixture
def mock_health_builder(sample_health_snapshot: HealthSnapshot) -> MagicMock:
    """Create a mock HealthBuilder."""
    builder = MagicMock()
    builder.build.return_value = sample_health_snapshot
    return builder
