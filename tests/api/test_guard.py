"""Tests for ArmedGuard safety model."""

from __future__ import annotations

import time

import pytest

from lazybricks.api.guard import ArmedGuard


class TestArmedGuard:
    """Test the ArmedGuard safety mechanism."""

    def test_initial_state_disarmed(self, armed_guard: ArmedGuard) -> None:
        """Guard should start disarmed."""
        assert not armed_guard.is_armed
        assert armed_guard.remaining_seconds == 0

    def test_arm(self, armed_guard: ArmedGuard) -> None:
        """Guard can be armed."""
        armed_guard.arm()
        assert armed_guard.is_armed
        assert armed_guard.remaining_seconds > 0
        assert armed_guard.remaining_seconds <= 30

    def test_disarm(self, armed_guard_active: ArmedGuard) -> None:
        """Guard can be manually disarmed."""
        assert armed_guard_active.is_armed
        armed_guard_active.disarm()
        assert not armed_guard_active.is_armed
        assert armed_guard_active.remaining_seconds == 0

    def test_status_display_disarmed(self, armed_guard: ArmedGuard) -> None:
        """Status display shows read-only when disarmed."""
        display = armed_guard.status_display
        assert "READ-ONLY" in display

    def test_status_display_armed(self, armed_guard_active: ArmedGuard) -> None:
        """Status display shows armed with countdown."""
        display = armed_guard_active.status_display
        assert "ARMED" in display
        assert "s)" in display  # seconds indicator

    def test_auto_disarm_after_ttl(self) -> None:
        """Guard auto-disarms after TTL expires."""
        # Use a very short TTL for testing
        guard = ArmedGuard(ttl_seconds=1)
        guard.arm()
        assert guard.is_armed

        # Wait for TTL to expire
        time.sleep(1.1)
        assert not guard.is_armed
        assert guard.remaining_seconds == 0

    def test_remaining_seconds_decreases(self, armed_guard: ArmedGuard) -> None:
        """Remaining seconds should decrease over time."""
        armed_guard.arm()
        initial = armed_guard.remaining_seconds

        time.sleep(0.1)
        after_delay = armed_guard.remaining_seconds

        assert after_delay <= initial

    def test_re_arming_resets_timer(self, armed_guard: ArmedGuard) -> None:
        """Re-arming should reset the timer."""
        armed_guard.arm()
        time.sleep(0.5)

        # Re-arm
        armed_guard.arm()
        remaining = armed_guard.remaining_seconds

        # Should be close to full TTL again
        assert remaining >= 29

    def test_custom_ttl(self) -> None:
        """Guard respects custom TTL."""
        guard = ArmedGuard(ttl_seconds=60)
        guard.arm()
        assert guard.remaining_seconds <= 60
        assert guard.remaining_seconds > 50  # Some buffer for test execution
