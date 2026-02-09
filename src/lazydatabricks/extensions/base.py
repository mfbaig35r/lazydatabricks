"""Base class for LazyDatabricks extensions.

Extensions are optional feature sets that register additional screens,
keybindings, and API operations without modifying core code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from textual.binding import Binding

if TYPE_CHECKING:
    from lazydatabricks.api.client import DatabricksClient


@dataclass
class ExtensionInfo:
    """Metadata about an extension."""
    name: str
    display_name: str
    description: str
    hotkey: str
    requires_sql_warehouse: bool = False


class BaseExtension(ABC):
    """Base class for LazyDatabricks extensions.

    Extensions must implement:
    - info: ExtensionInfo with metadata
    - check_requirements(): Verify extension can load
    - get_screen_class(): Return the Screen class
    - get_ops_class(): Return the Ops class

    Optional overrides:
    - get_bindings(): Additional app-level bindings
    - get_nav_hint(): Footer navigation item
    - get_help_items(): Help overlay content
    """

    def __init__(self, config: dict) -> None:
        """Initialize with extension-specific config.

        Args:
            config: The [extensions.<name>] section from config.
        """
        self.config = config

    @property
    @abstractmethod
    def info(self) -> ExtensionInfo:
        """Return extension metadata."""
        pass

    @abstractmethod
    def check_requirements(self, client: "DatabricksClient") -> tuple[bool, str]:
        """Check if extension can be loaded.

        Called during app startup. If this returns (False, error),
        the extension will be skipped with a warning.

        Args:
            client: The Databricks client instance.

        Returns:
            Tuple of (success, error_message). If success is True,
            error_message is ignored.
        """
        pass

    @abstractmethod
    def get_screen_class(self) -> type:
        """Return the Screen class to register.

        The screen will be installed with name=self.info.name.
        """
        pass

    @abstractmethod
    def get_ops_class(self) -> type:
        """Return the Ops class to instantiate.

        The ops instance will be created with (client, config).
        """
        pass

    def get_bindings(self) -> list[Binding]:
        """Return app-level bindings for this extension.

        Default implementation creates a navigation binding
        using the extension's hotkey.
        """
        return [
            Binding(
                self.info.hotkey,
                f"go_{self.info.name}",
                self.info.display_name,
                show=False,
            )
        ]

    def get_nav_hint(self) -> tuple[str, str]:
        """Return (key, label) for footer navigation."""
        return (self.info.hotkey, self.info.display_name)

    def get_help_items(self) -> list[tuple[str, str]]:
        """Return list of (key, description) for help overlay.

        Default implementation returns basic navigation hint.
        Override to add extension-specific keybindings.
        """
        return [
            (self.info.hotkey, self.info.display_name),
        ]
