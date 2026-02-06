"""Tests for Header widget."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from lazybricks.api.guard import ArmedGuard


class TestHeader:
    """Test the Header widget."""

    def test_header_displays_workspace(self) -> None:
        """Header should display workspace info."""
        from lazybricks.tui.widgets.header import Header

        guard = ArmedGuard()
        header = Header(
            guard=guard,
            workspace="test-workspace.cloud.databricks.com",
            profile="default",
        )

        assert header.workspace == "test-workspace.cloud.databricks.com"
        assert header.profile == "default"

    def test_header_armed_state_reactive(self) -> None:
        """Header armed display should be reactive."""
        from lazybricks.tui.widgets.header import Header

        guard = ArmedGuard()
        header = Header(guard=guard)

        # Initially disarmed
        assert not header.is_armed

        # Arm the guard
        guard.arm()

        # The header should reflect this on next update
        # (In real app, this happens via timer)
        header._update_armed_status()
        assert header.is_armed

    def test_header_shows_countdown_when_armed(self) -> None:
        """Header should show countdown when armed."""
        from lazybricks.tui.widgets.header import Header

        guard = ArmedGuard(ttl_seconds=30)
        guard.arm()

        header = Header(guard=guard)
        header._update_armed_status()

        assert "ARMED" in header.armed_display
        # Should contain seconds
        assert "s)" in header.armed_display
