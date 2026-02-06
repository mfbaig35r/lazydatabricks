# LazyBricks 🧱

A keyboard-first TUI for Databricks — **lazygit for your data platform**.

> Status → Logs → Action in seconds, not clicks.

## Design Principles

- **Read-first, act-second.** Default is safe visibility; destructive actions require explicit arming.
- **Spark-true, not API-true.** "Is my cluster usable?" matters more than "does the API say RUNNING?"
- **Logs are the primary artifact.** One keystroke, not seven clicks.

## Quick Start

```bash
# Install
pip install lazybricks

# Or from source
pip install -e ".[dev]"

# Configure (uses same env vars / .databrickscfg as Databricks SDK)
export DATABRICKS_HOST=https://adb-xxx.azuredatabricks.net
export DATABRICKS_TOKEN=dapi...

# Launch TUI (default)
lazybricks

# Or use specific profile
lazybricks --profile staging

# CLI mode (non-interactive)
lazybricks health      # Health snapshot
lazybricks clusters    # List clusters
lazybricks jobs        # List jobs
lazybricks test        # Test connection
```

## TUI Overview

LazyBricks provides a keyboard-driven interface with five main screens:

- **Home (h)** — Health dashboard showing workspace identity, Spark connectivity, cluster/job/warehouse summaries
- **Clusters (c)** — List and manage compute clusters with start/terminate/restart actions
- **Jobs (j)** — Three-pane hierarchy: Jobs → Runs → Detail with run now/cancel/rerun actions
- **Warehouses (w)** — SQL warehouse management with start/stop actions
- **Config** — Profile switching and connection testing

## Safety Model: Armed Mode

LazyBricks defaults to **READ-ONLY** mode. All destructive actions require explicitly arming:

1. Press `A` to arm (30-second timer starts)
2. Header shows red "ARMED (Xs)" countdown
3. Execute destructive action (e.g., `t` to terminate cluster)
4. System auto-disarms after 30 seconds

Destructive actions include:
- Cluster: start, terminate, restart
- Job: run now, cancel, rerun
- Warehouse: start, stop

## Keybindings

### Global Navigation

| Key | Action |
|-----|--------|
| `h` | Home screen |
| `c` | Clusters screen |
| `j` | Jobs screen |
| `w` | Warehouses screen |
| `A` | Toggle armed mode (30s) |
| `?` | Show help overlay |
| `q` | Quit |
| `Esc` | Back / Close modal |

### Home Screen

| Key | Action |
|-----|--------|
| `r` | Refresh health data |

### Clusters Screen

| Key | Action |
|-----|--------|
| `s` | Start cluster (requires armed) |
| `t` | Terminate cluster (requires armed) |
| `R` | Restart cluster (requires armed) |
| `l` | View cluster logs (opens browser) |
| `r` | Refresh |
| `Enter` | Open in Databricks UI |

### Jobs Screen

| Key | Action |
|-----|--------|
| `Tab` | Switch between panes (Jobs → Runs → Detail) |
| `Enter` | Drill down into selection |
| `Esc` | Back up in hierarchy |
| `n` | Run job now (requires armed) |
| `c` | Cancel run (requires armed) |
| `R` | Rerun (requires armed) |
| `l` | View run logs |
| `r` | Refresh |

### Logs Screen

| Key | Action |
|-----|--------|
| `/` | Start search |
| `n` | Next search match |
| `N` | Previous search match |
| `f` | Cycle filter (ALL → ERROR → WARN+ → INFO+) |
| `G` | Go to bottom |
| `g` | Go to top |
| `o` | Open in browser (fallback) |
| `Esc` | Close logs |

### Warehouses Screen

| Key | Action |
|-----|--------|
| `s` | Start warehouse (requires armed) |
| `S` | Stop warehouse (requires armed) |
| `r` | Refresh |
| `Enter` | Open in Databricks UI |

### Config Screen

| Key | Action |
|-----|--------|
| `Enter` | Switch to selected profile |
| `t` | Test connection |

## Architecture

```
src/lazybricks/
├── models/       # Data models — stable internal structs
│   ├── cluster.py    # ClusterSummary, ClusterState, ClusterFlag
│   ├── job.py        # JobSummary, RunSummary, RunDetail
│   ├── warehouse.py  # WarehouseSummary, WarehouseState
│   ├── health.py     # HealthSnapshot, SparkStatus
│   └── config.py     # LazyBricksConfig, DatabricksProfile
├── api/          # API client layer
│   ├── client.py     # DatabricksClient (SDK wrapper)
│   ├── clusters.py   # ClusterOps
│   ├── jobs.py       # JobOps
│   ├── warehouses.py # WarehouseOps
│   ├── health.py     # HealthBuilder
│   ├── logs.py       # LogOps
│   └── guard.py      # ArmedGuard (safety model)
└── tui/          # Textual TUI
    ├── app.py        # LazyBricksApp main class
    ├── theme.py      # Colors and CSS
    ├── screens/      # Screen implementations
    │   ├── home.py
    │   ├── clusters.py
    │   ├── jobs.py
    │   ├── logs.py
    │   ├── warehouses.py
    │   └── config.py
    └── widgets/      # Reusable widgets
        ├── header.py
        ├── status_bar.py
        ├── help_overlay.py
        └── confirm_dialog.py
```

## Configuration

LazyBricks uses the same configuration as the Databricks SDK:

1. **Environment variables** (highest priority)
   ```bash
   export DATABRICKS_HOST=https://adb-xxx.azuredatabricks.net
   export DATABRICKS_TOKEN=dapi...
   export DATABRICKS_CLUSTER_ID=0123-456789-abcdef  # optional
   ```

2. **~/.databrickscfg profiles**
   ```ini
   [DEFAULT]
   host = https://adb-xxx.azuredatabricks.net
   token = dapi...
   cluster_id = 0123-456789-abcdef

   [staging]
   host = https://adb-yyy.azuredatabricks.net
   token = dapi...
   ```

3. **CLI flags**
   ```bash
   lazybricks --host https://... --token dapi... --cluster-id 0123...
   lazybricks --profile staging
   ```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Type checking
mypy src/lazybricks

# Linting
ruff check src/lazybricks
```

## Requirements

- Python 3.10+
- Databricks workspace with API access

## License

MIT
