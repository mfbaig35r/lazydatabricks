"""Tests for Home screen."""

from __future__ import annotations

import pytest

from lazydatabricks.models.health import HealthSnapshot, SparkStatus


class TestHomeScreen:
    """Test the Home screen display."""

    def test_health_snapshot_spark_display(
        self, sample_health_snapshot: HealthSnapshot
    ) -> None:
        """Health snapshot should have correct spark display."""
        assert "Spark OK" in sample_health_snapshot.spark_display
        assert sample_health_snapshot.current_catalog in sample_health_snapshot.spark_display

    def test_health_snapshot_cluster_display(
        self, sample_health_snapshot: HealthSnapshot
    ) -> None:
        """Health snapshot should show cluster health."""
        display = sample_health_snapshot.cluster_health_display
        assert "2/3 running" in display
        assert "idle-burning" in display

    def test_health_snapshot_job_display(
        self, sample_health_snapshot: HealthSnapshot
    ) -> None:
        """Health snapshot should show job health."""
        display = sample_health_snapshot.job_health_display
        assert "2 active" in display
        assert "failed" in display

    def test_health_snapshot_failure_display(
        self, sample_health_snapshot: HealthSnapshot
    ) -> None:
        """Health snapshot should show last failure."""
        display = sample_health_snapshot.last_failure_display
        assert "Failed Job" in display
        assert "NullPointerException" in display

    def test_spark_status_disconnected(self) -> None:
        """Spark status should show disconnected properly."""
        snapshot = HealthSnapshot(
            spark_status=SparkStatus.DISCONNECTED,
        )
        assert "disconnected" in snapshot.spark_display.lower()

    def test_spark_status_no_cluster(self) -> None:
        """Spark status should show no cluster configured."""
        snapshot = HealthSnapshot(
            spark_status=SparkStatus.NO_CLUSTER,
        )
        assert "No cluster" in snapshot.spark_display
