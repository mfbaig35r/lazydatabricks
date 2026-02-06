"""Tests for armed mode flow."""

from __future__ import annotations

import pytest

from lazybricks.api.guard import ArmedGuard


class TestArmedModeFlow:
    """Test the armed mode user flow."""

    def test_action_requires_armed(self, armed_guard: ArmedGuard) -> None:
        """Actions should be blocked when disarmed."""
        # Simulating the check that screens do
        can_proceed = armed_guard.is_armed
        assert not can_proceed

    def test_action_allowed_when_armed(self, armed_guard_active: ArmedGuard) -> None:
        """Actions should be allowed when armed."""
        can_proceed = armed_guard_active.is_armed
        assert can_proceed

    def test_toggle_armed_mode(self, armed_guard: ArmedGuard) -> None:
        """Should be able to toggle armed mode."""
        # Start disarmed
        assert not armed_guard.is_armed

        # Arm
        armed_guard.arm()
        assert armed_guard.is_armed

        # Disarm
        armed_guard.disarm()
        assert not armed_guard.is_armed

    def test_armed_mode_countdown(self, armed_guard: ArmedGuard) -> None:
        """Armed mode should have a countdown."""
        armed_guard.arm()

        # Should have remaining seconds
        remaining = armed_guard.remaining_seconds
        assert remaining > 0
        assert remaining <= armed_guard.ttl_seconds

    def test_armed_guard_status_changes(self, armed_guard: ArmedGuard) -> None:
        """Status display should change with state."""
        disarmed_status = armed_guard.status_display
        assert "READ-ONLY" in disarmed_status

        armed_guard.arm()
        armed_status = armed_guard.status_display
        assert "ARMED" in armed_status
        assert "READ-ONLY" not in armed_status
