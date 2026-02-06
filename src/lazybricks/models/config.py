"""Configuration model and profile management.

Handles:
- Environment variable auth (DATABRICKS_HOST / DATABRICKS_TOKEN)
- ~/.databrickscfg profile parsing
- Profile switching at runtime
"""

from __future__ import annotations

import configparser
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class AuthMethod(str, Enum):
    """How we're authenticating to Databricks."""
    PAT = "pat"                   # Personal Access Token
    OAUTH_M2M = "oauth_m2m"      # Service Principal / M2M OAuth
    AZURE_CLI = "azure_cli"      # az login
    ENV = "env"                   # Raw env vars (no profile)
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DatabricksProfile:
    """A single Databricks CLI profile from ~/.databrickscfg."""
    name: str
    host: str
    token: Optional[str] = None
    account_id: Optional[str] = None
    cluster_id: Optional[str] = None
    auth_type: Optional[str] = None

    @property
    def auth_method(self) -> AuthMethod:
        if self.token:
            return AuthMethod.PAT
        if self.auth_type == "azure-cli":
            return AuthMethod.AZURE_CLI
        if self.auth_type == "oauth-m2m":
            return AuthMethod.OAUTH_M2M
        return AuthMethod.UNKNOWN

    @property
    def host_short(self) -> str:
        """Workspace hostname without protocol."""
        return self.host.replace("https://", "").replace("http://", "").rstrip("/")


@dataclass
class LazyBricksConfig:
    """Runtime configuration for LazyBricks.

    Resolves auth from (in priority order):
    1. Explicit overrides (e.g., CLI flags)
    2. Environment variables
    3. ~/.databrickscfg profile
    """
    host: str
    token: str
    cluster_id: Optional[str] = None
    profile_name: Optional[str] = None
    auth_method: AuthMethod = AuthMethod.ENV
    read_only: bool = True  # Safe default

    # Available profiles (populated on load)
    available_profiles: list[DatabricksProfile] = field(default_factory=list)

    @classmethod
    def load(
        cls,
        profile: Optional[str] = None,
        host_override: Optional[str] = None,
        token_override: Optional[str] = None,
        cluster_id_override: Optional[str] = None,
    ) -> LazyBricksConfig:
        """Load configuration with fallback chain.

        Priority: overrides > env vars > profile > DEFAULT profile.
        """
        load_dotenv()

        # Parse all available profiles
        profiles = _parse_databricks_cfg()

        # Determine which profile to use
        target_profile: Optional[DatabricksProfile] = None
        if profile:
            target_profile = next((p for p in profiles if p.name == profile), None)
            if not target_profile:
                raise ValueError(
                    f"Profile '{profile}' not found in ~/.databrickscfg. "
                    f"Available: {[p.name for p in profiles]}"
                )
        elif profiles:
            # Auto-select: prefer "default" profile, otherwise use first available
            target_profile = next(
                (p for p in profiles if p.name.lower() == "default"),
                profiles[0] if profiles else None
            )

        # Resolve values with fallback chain
        host = (
            host_override
            or os.getenv("DATABRICKS_HOST")
            or (target_profile.host if target_profile else None)
        )
        token = (
            token_override
            or os.getenv("DATABRICKS_TOKEN")
            or (target_profile.token if target_profile else None)
        )
        cluster_id = (
            cluster_id_override
            or os.getenv("DATABRICKS_CLUSTER_ID")
            or (target_profile.cluster_id if target_profile else None)
        )

        if not host:
            raise ValueError(
                "No Databricks host found. Set DATABRICKS_HOST, "
                "use a ~/.databrickscfg profile, or pass --host."
            )
        if not token:
            raise ValueError(
                "No Databricks token found. Set DATABRICKS_TOKEN, "
                "use a ~/.databrickscfg profile, or pass --token."
            )

        # Determine auth method
        auth_method = AuthMethod.ENV
        if target_profile:
            auth_method = target_profile.auth_method

        return cls(
            host=host.rstrip("/"),
            token=token,
            cluster_id=cluster_id,
            profile_name=profile or target_profile.name if target_profile else None,
            auth_method=auth_method,
            available_profiles=profiles,
        )

    @property
    def host_short(self) -> str:
        return self.host.replace("https://", "").replace("http://", "").rstrip("/")

    def switch_profile(self, profile_name: str) -> LazyBricksConfig:
        """Return a new config targeting a different profile."""
        return LazyBricksConfig.load(profile=profile_name)


def _parse_databricks_cfg() -> list[DatabricksProfile]:
    """Parse ~/.databrickscfg into a list of profiles."""
    cfg_path = Path.home() / ".databrickscfg"
    if not cfg_path.exists():
        return []

    parser = configparser.ConfigParser()
    parser.read(str(cfg_path))

    profiles = []
    for section in parser.sections():
        host = parser.get(section, "host", fallback="")
        if not host:
            continue

        profiles.append(
            DatabricksProfile(
                name=section,
                host=host,
                token=parser.get(section, "token", fallback=None),
                account_id=parser.get(section, "account_id", fallback=None),
                cluster_id=parser.get(section, "cluster_id", fallback=None),
                auth_type=parser.get(section, "auth_type", fallback=None),
            )
        )

    return profiles
