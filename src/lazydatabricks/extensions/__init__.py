"""LazyDatabricks extensions loader and registry.

Extensions are optional feature sets loaded from config.
See base.py for the BaseExtension class.

Config file: ~/.lazydatabricks/config.toml

Example:
    [extensions]
    enabled = ["billing"]

    [extensions.billing]
    sql_warehouse_id = "abc123..."
    default_window = "7d"
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11 fallback

from lazydatabricks.extensions.base import BaseExtension, ExtensionInfo

if TYPE_CHECKING:
    from lazydatabricks.api.client import DatabricksClient

logger = logging.getLogger(__name__)

# Registry of available extensions (populated by register_extension)
AVAILABLE_EXTENSIONS: dict[str, type[BaseExtension]] = {}

# Default config path
CONFIG_PATH = Path.home() / ".lazydatabricks" / "config.toml"


def register_extension(ext_class: type[BaseExtension]) -> type[BaseExtension]:
    """Register an extension class.

    Can be used as a decorator:
        @register_extension
        class MyExtension(BaseExtension):
            ...

    Or called directly:
        register_extension(MyExtension)
    """
    # Create a temporary instance to get the info
    # (info is a property that doesn't need config)
    temp = ext_class.__new__(ext_class)
    temp.config = {}

    try:
        info = temp.info
        AVAILABLE_EXTENSIONS[info.name] = ext_class
        logger.debug(f"Registered extension: {info.name}")
    except Exception as e:
        logger.warning(f"Failed to register extension {ext_class}: {e}")

    return ext_class


def load_lazydatabricks_config(config_path: Path | None = None) -> dict:
    """Load LazyDatabricks config from TOML file.

    Args:
        config_path: Path to config file. Defaults to ~/.lazydatabricks/config.toml.

    Returns:
        Parsed config dict, or empty dict if file doesn't exist.
    """
    path = config_path or CONFIG_PATH

    if not path.exists():
        logger.debug(f"Config file not found: {path}")
        return {}

    try:
        with open(path, "rb") as f:
            config = tomllib.load(f)
        logger.debug(f"Loaded config from {path}")
        return config
    except Exception as e:
        logger.warning(f"Failed to parse config {path}: {e}")
        return {}


def load_extensions(
    client: "DatabricksClient",
    config: dict | None = None,
) -> list[BaseExtension]:
    """Load enabled extensions that pass requirement checks.

    Args:
        client: The Databricks client instance.
        config: Config dict. If None, loads from ~/.lazydatabricks/config.toml.

    Returns:
        List of successfully loaded extension instances.
    """
    if config is None:
        config = load_lazydatabricks_config()

    extensions_config = config.get("extensions", {})
    enabled = extensions_config.get("enabled", [])

    if not enabled:
        logger.debug("No extensions enabled")
        return []

    loaded: list[BaseExtension] = []

    for name in enabled:
        if name not in AVAILABLE_EXTENSIONS:
            logger.warning(f"Unknown extension: {name}")
            continue

        ext_class = AVAILABLE_EXTENSIONS[name]
        ext_config = extensions_config.get(name, {})

        try:
            ext = ext_class(ext_config)
            ok, error = ext.check_requirements(client)

            if not ok:
                logger.warning(f"Extension '{name}' disabled: {error}")
                continue

            loaded.append(ext)
            logger.info(f"Loaded extension: {name}")

        except Exception as e:
            logger.warning(f"Failed to load extension '{name}': {e}")

    return loaded


def get_extension_names() -> list[str]:
    """Return names of all registered extensions."""
    return list(AVAILABLE_EXTENSIONS.keys())


def get_extension_info(name: str) -> ExtensionInfo | None:
    """Get info for a registered extension."""
    if name not in AVAILABLE_EXTENSIONS:
        return None

    ext_class = AVAILABLE_EXTENSIONS[name]
    temp = ext_class.__new__(ext_class)
    temp.config = {}

    try:
        return temp.info
    except Exception:
        return None


# Auto-register built-in extensions
# (imports happen here to avoid circular imports)
def _register_builtin_extensions() -> None:
    """Register built-in extensions.

    Called at module load time. Extensions that fail to import
    are silently skipped (they may have missing dependencies).
    """
    # Billing extension
    try:
        from lazydatabricks.extensions.billing import BillingExtension
        register_extension(BillingExtension)
    except ImportError as e:
        logger.debug(f"Billing extension not available: {e}")


_register_builtin_extensions()
