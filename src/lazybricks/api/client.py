"""Core Databricks client — the single entry point for all API calls.

Wraps the Databricks SDK WorkspaceClient and provides:
- Lazy initialization
- Profile switching
- Connection testing
- Centralized error handling

All domain-specific modules (clusters, jobs, warehouses) receive
this client rather than creating their own SDK instances.
"""

from __future__ import annotations

import logging
from typing import Optional

from databricks.sdk import WorkspaceClient

from lazybricks.models.config import LazyBricksConfig

logger = logging.getLogger(__name__)


class DatabricksClient:
    """Central Databricks API client.

    Usage:
        config = LazyBricksConfig.load()
        client = DatabricksClient(config)

        # Use domain-specific wrappers
        from lazybricks.api.clusters import ClusterOps
        clusters = ClusterOps(client)
        summaries = clusters.list_all()
    """

    def __init__(self, config: LazyBricksConfig) -> None:
        self._config = config
        self._sdk: Optional[WorkspaceClient] = None

    @property
    def config(self) -> LazyBricksConfig:
        return self._config

    @property
    def sdk(self) -> WorkspaceClient:
        """Lazily initialize the Databricks SDK client."""
        if self._sdk is None:
            self._sdk = WorkspaceClient(
                host=self._config.host,
                token=self._config.token,
            )
            logger.info(f"SDK client initialized for {self._config.host_short}")
        return self._sdk

    @property
    def host(self) -> str:
        return self._config.host

    @property
    def cluster_id(self) -> Optional[str]:
        return self._config.cluster_id

    @property
    def is_read_only(self) -> bool:
        return self._config.read_only

    def test_connection(self) -> dict:
        """Quick connection test — validates auth + returns identity.

        Returns:
            {"status": "ok", "user": "...", "host": "..."} or
            {"status": "error", "error": "..."}
        """
        try:
            current_user = self.sdk.current_user.me()
            return {
                "status": "ok",
                "user": current_user.user_name or "",
                "display_name": current_user.display_name or "",
                "host": self._config.host_short,
            }
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "host": self._config.host_short,
            }

    def switch_profile(self, profile_name: str) -> DatabricksClient:
        """Return a new client targeting a different profile.

        The old SDK instance is discarded.
        """
        new_config = self._config.switch_profile(profile_name)
        return DatabricksClient(new_config)

    def refresh(self) -> None:
        """Force a fresh SDK client on next call."""
        self._sdk = None
        logger.info("SDK client reset — will reinitialize on next call")
