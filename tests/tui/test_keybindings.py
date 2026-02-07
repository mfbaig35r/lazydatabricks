"""Tests for keybinding definitions."""

from __future__ import annotations

import pytest

from lazybricks.tui.widgets.status_bar import (
    GLOBAL_BINDINGS,
    HOME_BINDINGS,
    CLUSTERS_BINDINGS,
    JOBS_BINDINGS,
    PIPELINES_BINDINGS,
    LOGS_BINDINGS,
    WAREHOUSES_BINDINGS,
    CONFIG_BINDINGS,
)


class TestKeybindings:
    """Test keybinding consistency."""

    def test_global_bindings_exist(self) -> None:
        """Global bindings should be defined."""
        assert len(GLOBAL_BINDINGS) > 0
        keys = [k for k, _ in GLOBAL_BINDINGS]
        assert "h" in keys  # home
        assert "c" in keys  # clusters
        assert "j" in keys  # jobs
        assert "p" in keys  # pipelines
        assert "w" in keys  # warehouses
        assert "P" in keys  # profiles
        assert "A" in keys  # arm
        assert "?" in keys  # help
        assert "q" in keys  # quit

    def test_home_bindings_include_refresh(self) -> None:
        """Home bindings should include refresh."""
        keys = [k for k, _ in HOME_BINDINGS]
        assert "r" in keys

    def test_clusters_bindings_include_actions(self) -> None:
        """Clusters bindings should include cluster actions."""
        keys = [k for k, _ in CLUSTERS_BINDINGS]
        assert "s" in keys  # start
        assert "t" in keys  # terminate
        assert "R" in keys  # restart

    def test_jobs_bindings_include_navigation(self) -> None:
        """Jobs bindings should include pane navigation."""
        keys = [k for k, _ in JOBS_BINDINGS]
        assert "Tab" in keys
        assert "Enter" in keys
        assert "Esc" in keys

    def test_jobs_bindings_include_actions(self) -> None:
        """Jobs bindings should include job actions."""
        keys = [k for k, _ in JOBS_BINDINGS]
        assert "n" in keys  # run now
        assert "c" in keys  # cancel
        assert "R" in keys  # rerun

    def test_pipelines_bindings_include_navigation(self) -> None:
        """Pipelines bindings should include pane navigation."""
        keys = [k for k, _ in PIPELINES_BINDINGS]
        assert "Tab" in keys
        assert "Enter" in keys
        assert "Esc" in keys

    def test_pipelines_bindings_include_actions(self) -> None:
        """Pipelines bindings should include pipeline actions."""
        keys = [k for k, _ in PIPELINES_BINDINGS]
        assert "s" in keys  # start
        assert "S" in keys  # stop
        assert "f" in keys  # full refresh

    def test_logs_bindings_include_search(self) -> None:
        """Logs bindings should include search."""
        keys = [k for k, _ in LOGS_BINDINGS]
        assert "/" in keys  # search
        assert "n" in keys  # next
        assert "N" in keys  # prev

    def test_logs_bindings_include_filter(self) -> None:
        """Logs bindings should include filter."""
        keys = [k for k, _ in LOGS_BINDINGS]
        assert "f" in keys  # filter

    def test_warehouses_bindings_include_actions(self) -> None:
        """Warehouses bindings should include start/stop."""
        keys = [k for k, _ in WAREHOUSES_BINDINGS]
        assert "s" in keys  # start
        assert "S" in keys  # stop

    def test_config_bindings_include_switch(self) -> None:
        """Config bindings should include profile switch."""
        keys = [k for k, _ in CONFIG_BINDINGS]
        assert "Enter" in keys  # switch
        assert "t" in keys  # test

    def test_all_bindings_have_descriptions(self) -> None:
        """All bindings should have descriptions."""
        all_bindings = [
            GLOBAL_BINDINGS,
            HOME_BINDINGS,
            CLUSTERS_BINDINGS,
            JOBS_BINDINGS,
            PIPELINES_BINDINGS,
            LOGS_BINDINGS,
            WAREHOUSES_BINDINGS,
            CONFIG_BINDINGS,
        ]

        for binding_list in all_bindings:
            for key, desc in binding_list:
                assert key, "Keybinding should have a key"
                assert desc, "Keybinding should have a description"
                assert len(desc) > 0, "Description should not be empty"
