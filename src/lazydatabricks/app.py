"""LazyDatabricks application entry point.

Usage:
    lazydatabricks                    # Launch TUI (default)
    lazydatabricks --profile staging  # TUI with specific profile
    lazydatabricks health             # CLI: health snapshot
    lazydatabricks clusters           # CLI: list clusters
    lazydatabricks jobs               # CLI: list jobs
    lazydatabricks test               # CLI: test connection
    lazydatabricks setup billing      # Configure billing extension
"""

from __future__ import annotations

import argparse
import json
import sys

from lazydatabricks.api.client import DatabricksClient
from lazydatabricks.api.health import HealthBuilder
from lazydatabricks.models.config import LazyDatabricksConfig


def create_client(args: argparse.Namespace) -> DatabricksClient:
    """Create a DatabricksClient from CLI args."""
    config = LazyDatabricksConfig.load(
        profile=args.profile,
        host_override=args.host,
        token_override=args.token,
        cluster_id_override=args.cluster_id,
    )
    return DatabricksClient(config)


def cmd_tui(client: DatabricksClient) -> None:
    """Launch the TUI application."""
    from lazydatabricks.tui import run_tui
    run_tui(client)


def cmd_health(client: DatabricksClient) -> None:
    """Print health snapshot to stdout (CLI mode)."""
    builder = HealthBuilder(client)
    snapshot = builder.build()

    print("=" * 60)
    print("  LazyDatabricks — Health Snapshot")
    print("=" * 60)
    print()
    print(f"  Workspace:  {snapshot.workspace_host}")
    print(f"  User:       {snapshot.workspace_user}")
    print(f"  Profile:    {snapshot.active_profile}")
    print(f"  Spark:      {snapshot.spark_display}")
    print()
    print(f"  Clusters:   {snapshot.cluster_health_display}")
    print(f"  Jobs:       {snapshot.job_health_display}")
    print(f"  Warehouses: {snapshot.running_warehouses}/{snapshot.total_warehouses} running")
    print()
    print(f"  Last fail:  {snapshot.last_failure_display}")
    print()
    print("=" * 60)


def cmd_clusters(client: DatabricksClient) -> None:
    """List clusters to stdout (CLI mode)."""
    from lazydatabricks.api.clusters import ClusterOps

    ops = ClusterOps(client)
    clusters = ops.list_all()

    if not clusters:
        print("No clusters found.")
        return

    # Simple table
    print(f"{'Name':<35} {'State':<12} {'Workers':<10} {'Runtime':<10} {'Flags'}")
    print("-" * 85)
    for c in clusters:
        flags = ", ".join(f.value for f in c.flags) if c.flags else ""
        print(f"{c.name[:34]:<35} {c.state.value:<12} {c.workers_display:<10} {c.runtime_display:<10} {flags}")


def cmd_jobs(client: DatabricksClient) -> None:
    """List jobs to stdout (CLI mode)."""
    from lazydatabricks.api.jobs import JobOps

    ops = JobOps(client)
    jobs = ops.list_jobs(limit=50)

    if not jobs:
        print("No jobs found.")
        return

    print(f"{'ID':<10} {'Name':<40} {'Schedule':<20} {'Health'}")
    print("-" * 75)
    for j in jobs:
        print(f"{j.id:<10} {j.name[:39]:<40} {j.schedule_display:<20} {j.health_display}")


def cmd_test(client: DatabricksClient) -> None:
    """Test connection."""
    result = client.test_connection()
    print(json.dumps(result, indent=2))


def cmd_setup(client: DatabricksClient, extension: str) -> None:
    """Set up an extension interactively."""
    from pathlib import Path

    if extension != "billing":
        print(f"Unknown extension: {extension}")
        print("Available extensions: billing")
        sys.exit(1)

    # Set up billing extension
    _setup_billing(client)


def _setup_billing(client: DatabricksClient) -> None:
    """Interactive setup for billing extension."""
    from pathlib import Path
    from lazydatabricks.api.warehouses import WarehouseOps

    print()
    print("=" * 50)
    print("  LazyDatabricks — Billing Extension Setup")
    print("=" * 50)
    print()
    print("The billing extension requires a SQL Warehouse")
    print("to query system.billing tables.")
    print()

    # List warehouses
    ops = WarehouseOps(client)
    warehouses = ops.list_all()

    if not warehouses:
        print("No SQL Warehouses found in this workspace.")
        print("Create a warehouse first, then run this command again.")
        sys.exit(1)

    print("Available SQL Warehouses:")
    print()
    for i, w in enumerate(warehouses, 1):
        state = w.state.value
        size = w.size_display if hasattr(w, 'size_display') else w.size
        print(f"  [{i}] {w.name:<30} ({state}, {size})")
    print()

    # Get user selection
    while True:
        try:
            choice = input(f"Select warehouse [1-{len(warehouses)}]: ").strip()
            if not choice:
                print("Setup cancelled.")
                return
            idx = int(choice) - 1
            if 0 <= idx < len(warehouses):
                selected = warehouses[idx]
                break
            print(f"Please enter a number between 1 and {len(warehouses)}")
        except ValueError:
            print("Please enter a valid number")
        except (KeyboardInterrupt, EOFError):
            print("\nSetup cancelled.")
            return

    # Write config
    config_dir = Path.home() / ".lazydatabricks"
    config_path = config_dir / "config.toml"

    config_dir.mkdir(parents=True, exist_ok=True)

    # Load existing config or start fresh
    existing_config = {}
    if config_path.exists():
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        with open(config_path, "rb") as f:
            existing_config = tomllib.load(f)

    # Update config
    if "extensions" not in existing_config:
        existing_config["extensions"] = {}

    extensions = existing_config["extensions"]

    # Add billing to enabled list
    enabled = extensions.get("enabled", [])
    if "billing" not in enabled:
        enabled.append("billing")
    extensions["enabled"] = enabled

    # Set billing config
    if "billing" not in extensions:
        extensions["billing"] = {}
    extensions["billing"]["sql_warehouse_id"] = selected.id

    # Write TOML manually (tomllib is read-only)
    with open(config_path, "w") as f:
        f.write("# LazyDatabricks Configuration\n\n")
        f.write("[extensions]\n")
        f.write(f"enabled = {extensions['enabled']!r}\n\n")
        f.write("[extensions.billing]\n")
        f.write(f'sql_warehouse_id = "{selected.id}"\n')

    print()
    print(f"✓ Billing extension configured!")
    print(f"  Warehouse: {selected.name} ({selected.id})")
    print(f"  Config: {config_path}")
    print()
    print("Run 'lazydatabricks' and press 'b' to open Billing.")
    print()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LazyDatabricks — keyboard-first TUI for Databricks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Auth options
    parser.add_argument("--profile", "-p", help="Databricks CLI profile name")
    parser.add_argument("--host", help="Databricks workspace URL")
    parser.add_argument("--token", help="Databricks PAT")
    parser.add_argument("--cluster-id", help="Default cluster ID")

    # Subcommands (CLI mode — TUI is default)
    sub = parser.add_subparsers(dest="command", help="Command to run (default: TUI)")
    sub.add_parser("tui", help="Launch TUI (default)")
    sub.add_parser("health", help="Show health snapshot (CLI)")
    sub.add_parser("clusters", help="List clusters (CLI)")
    sub.add_parser("jobs", help="List jobs (CLI)")
    sub.add_parser("test", help="Test connection (CLI)")

    # Setup command for extensions
    setup_parser = sub.add_parser("setup", help="Configure an extension")
    setup_parser.add_argument("extension", help="Extension to set up (e.g., billing)")

    args = parser.parse_args()

    try:
        client = create_client(args)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Default to TUI when no command specified
    command = args.command or "tui"

    # Handle setup separately (needs extension arg)
    if command == "setup":
        cmd_setup(client, args.extension)
        return

    commands = {
        "tui": cmd_tui,
        "health": cmd_health,
        "clusters": cmd_clusters,
        "jobs": cmd_jobs,
        "test": cmd_test,
    }

    handler = commands.get(command)
    if handler:
        handler(client)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
