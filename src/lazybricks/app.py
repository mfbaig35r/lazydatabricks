"""LazyBricks application entry point.

Usage:
    lazybricks                    # Launch TUI (default)
    lazybricks --profile staging  # TUI with specific profile
    lazybricks health             # CLI: health snapshot
    lazybricks clusters           # CLI: list clusters
    lazybricks jobs               # CLI: list jobs
    lazybricks test               # CLI: test connection
"""

from __future__ import annotations

import argparse
import json
import sys

from lazybricks.api.client import DatabricksClient
from lazybricks.api.health import HealthBuilder
from lazybricks.models.config import LazyBricksConfig


def create_client(args: argparse.Namespace) -> DatabricksClient:
    """Create a DatabricksClient from CLI args."""
    config = LazyBricksConfig.load(
        profile=args.profile,
        host_override=args.host,
        token_override=args.token,
        cluster_id_override=args.cluster_id,
    )
    return DatabricksClient(config)


def cmd_tui(client: DatabricksClient) -> None:
    """Launch the TUI application."""
    from lazybricks.tui import run_tui
    run_tui(client)


def cmd_health(client: DatabricksClient) -> None:
    """Print health snapshot to stdout (CLI mode)."""
    builder = HealthBuilder(client)
    snapshot = builder.build()

    print("=" * 60)
    print("  LazyBricks — Health Snapshot")
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
    from lazybricks.api.clusters import ClusterOps

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
    from lazybricks.api.jobs import JobOps

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


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="LazyBricks — keyboard-first TUI for Databricks",
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

    args = parser.parse_args()

    try:
        client = create_client(args)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    # Default to TUI when no command specified
    command = args.command or "tui"

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
