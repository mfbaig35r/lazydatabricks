"""Tests for Clusters screen."""

from __future__ import annotations

import pytest

from lazybricks.models.cluster import ClusterSummary, ClusterState, ClusterFlag


class TestClustersScreen:
    """Test the Clusters screen model behavior."""

    def test_cluster_state_display_styles(self) -> None:
        """Cluster states should have correct display styles."""
        assert ClusterState.RUNNING.display_style == "green"
        assert ClusterState.TERMINATED.display_style == "dim"
        assert ClusterState.ERROR.display_style == "red bold"
        assert ClusterState.PENDING.display_style == "yellow"

    def test_cluster_is_active(self) -> None:
        """is_active should correctly identify running states."""
        assert ClusterState.RUNNING.is_active
        assert ClusterState.RESIZING.is_active
        assert ClusterState.RESTARTING.is_active
        assert not ClusterState.TERMINATED.is_active
        assert not ClusterState.PENDING.is_active

    def test_cluster_is_actionable(self) -> None:
        """is_actionable should correctly identify states where actions are valid."""
        assert ClusterState.RUNNING.is_actionable
        assert ClusterState.TERMINATED.is_actionable
        assert ClusterState.ERROR.is_actionable
        assert not ClusterState.PENDING.is_actionable

    def test_cluster_workers_display_autoscale(
        self, sample_clusters: list[ClusterSummary]
    ) -> None:
        """Workers display should show autoscale range."""
        etl_cluster = sample_clusters[0]  # Has autoscale
        assert etl_cluster.workers_display == "2–8"

    def test_cluster_workers_display_fixed(
        self, sample_clusters: list[ClusterSummary]
    ) -> None:
        """Workers display should show fixed count."""
        dev_cluster = sample_clusters[1]  # Fixed workers
        assert dev_cluster.workers_display == "2"

    def test_cluster_runtime_display_terminated(
        self, sample_clusters: list[ClusterSummary]
    ) -> None:
        """Terminated cluster should show terminated in runtime."""
        dev_cluster = sample_clusters[1]
        assert dev_cluster.runtime_display == "terminated"

    def test_cluster_flags(self, sample_clusters: list[ClusterSummary]) -> None:
        """Clusters should have correct flags."""
        etl_cluster = sample_clusters[0]
        assert ClusterFlag.LONG_RUNNING in etl_cluster.flags

        idle_cluster = sample_clusters[2]
        assert ClusterFlag.IDLE_BURN in idle_cluster.flags
