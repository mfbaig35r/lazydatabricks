# LazyDatabricks TUI — Implementation Requirements

> **Audience**: Claude Code (or any implementation agent)
> **Scope**: Build the Textual-based TUI for LazyDatabricks. The data models and API layer are complete.
> **Date**: 2025-02-05

---

## 1. Context & What Already Exists

LazyDatabricks is a keyboard-first TUI for Databricks operations, inspired by lazygit/lazydocker. The philosophy is **read-first, act-second** with an armed-mode safety model.

### Completed Layers (DO NOT MODIFY unless fixing bugs)

```
src/lazydatabricks/
├── models/
│   ├── config.py      # DatabricksProfile, LazyDatabricksConfig, AuthMethod
│   ├── cluster.py     # ClusterState, ClusterFlag, ClusterSummary, ClusterEvent
│   ├── job.py         # RunState, RunResult, TriggerType, JobSummary, RunSummary, RunDetail, TaskSummary
│   ├── warehouse.py   # WarehouseState, WarehouseSize, WarehouseSummary, WarehouseQuery
│   └── health.py      # SparkStatus, HealthSnapshot
├── api/
│   ├── client.py      # DatabricksClient (SDK wrapper, lazy init, profile switching)
│   ├── clusters.py    # ClusterOps (list_all, get, start, terminate, restart, get_events)
│   ├── jobs.py        # JobOps (list_jobs, list_runs, get_run_detail, cancel_run, rerun, run_now)
│   ├── warehouses.py  # WarehouseOps (list_all, get, start, stop, list_queries)
│   ├── logs.py        # LogOps (get_run_logs, get_cluster_driver_logs), LogLine, LogBlock, LogSeverity
│   ├── health.py      # HealthBuilder (build → HealthSnapshot)
│   └── guard.py       # ArmedGuard (arm/disarm, TTL countdown, is_armed)
├── app.py             # CLI entry point (will need TUI launch added)
└── tui/
    └── __init__.py    # Empty placeholder — YOUR WORK GOES HERE
```

### Key Design Contracts

- **All display text is pre-computed on models** — e.g., `cluster.runtime_display`, `job.health_display`, `snapshot.spark_display`. Use these directly; don't reformat in the TUI.
- **All API operations return model objects** — e.g., `ClusterOps.list_all() → list[ClusterSummary]`. Never call the Databricks SDK directly from the TUI.
- **ArmedGuard gates all writes** — Before any destructive action, check `guard.is_armed`. If not armed, show a message "Press A to arm first". The guard auto-disarms after 30s.
- **Read-only by default** — `DatabricksClient.is_read_only` returns True when no guard is armed.

### Dependencies Already Declared

- `textual>=1.0.0` (in pyproject.toml)
- `pytest-asyncio>=0.23.0` (for async test support)

---

## 2. Architecture Requirements

### 2.1 File Structure

Create these files inside `src/lazydatabricks/tui/`:

```
tui/
├── __init__.py
├── app.py              # Main Textual App class
├── screens/
│   ├── __init__.py
│   ├── home.py         # Home/Health screen
│   ├── clusters.py     # Clusters screen
│   ├── jobs.py         # Jobs & Runs screen
│   ├── warehouses.py   # Warehouses screen
│   ├── logs.py         # Log viewer screen
│   └── config.py       # Config & Profiles screen
├── widgets/
│   ├── __init__.py
│   ├── header.py       # App header with armed-mode indicator
│   ├── status_bar.py   # Bottom status bar with keybinds
│   ├── data_table.py   # Reusable enriched DataTable wrapper (if needed)
│   └── log_viewer.py   # Scrollable log widget with severity coloring
└── theme.py            # Color palette, styles
```

### 2.2 App Lifecycle

```python
# In src/lazydatabricks/tui/app.py
class LazyDatabricksApp(textual.app.App):
    """Main application."""
    # Receives a DatabricksClient at construction
    # Owns the ArmedGuard instance
    # Manages screen switching
```

### 2.3 Integration with Existing app.py

Update `src/lazydatabricks/app.py` so that the default command (no subcommand) launches the TUI:

```python
# When no subcommand is given:
from lazydatabricks.tui.app import LazyDatabricksApp
app = LazyDatabricksApp(client=client)
app.run()
```

Keep existing CLI subcommands (health, clusters, jobs, test) working.

---

## 3. Screen Specifications

### 3.1 Home Screen (default on launch)

**Data source**: `HealthBuilder(client).build() → HealthSnapshot`

**Layout**:
```
┌──────────────────────────────────────────────────┐
│  LazyDatabricks          READ-ONLY    Profile: dev.  │  ← Header (persistent)
├──────────────────────────────────────────────────┤
│                                                  │
│  Workspace:  https://dbc-xxxxx.cloud.databricks  │
│  User:       user@example.com                   │
│  Spark:      ✓ Spark OK — main (v3.5.0)          │
│                                                  │
│  ── Clusters ──────────────────────────────────  │
│  2/5 running · ⚠ 1 idle-burning                  │
│                                                  │
│  ── Jobs ──────────────────────────────────────  │
│  3 active · ✗ 2 failed (24h)                     │
│                                                  │
│  ── Warehouses ────────────────────────────────  │
│  1/2 running                                     │
│                                                  │
│  ── Recent Failures ───────────────────────────  │
│  ✗ etl_daily_pipeline (2h ago): NullPointerExc…  │
│                                                  │
├──────────────────────────────────────────────────┤
│ c:clusters  j:jobs  w:warehouses  l:logs         │  ← Status bar (persistent)
│ r:refresh   A:arm   ?:help  q:quit               │
└──────────────────────────────────────────────────┘
```

**Behavior**:
- Auto-refreshes every 60 seconds (configurable)
- `r` forces immediate refresh
- Sections use the pre-computed display properties from HealthSnapshot
- Clicking/pressing Enter on a section navigates to that screen

### 3.2 Clusters Screen

**Data source**: `ClusterOps(client).list_all() → list[ClusterSummary]`

**Layout**: Master-detail split.

```
┌─────────────────────────────────┬─────────────────┐
│  Clusters                       │  Detail         │
├─────────────────────────────────┤                 │
│ ▸ my-dev-cluster    RUNNING  …  │  Name: my-dev…  │
│   etl-prod-cluster  TERMINATED  │  ID: 0205-…     │
│   shared-analytics  RUNNING  …  │  State: RUNNING │
│                                 │  Workers: 2-8   │
│                                 │  Runtime: 15.4  │
│                                 │  Idle: 25m      │
│                                 │  Flags:         │
│                                 │   ⚠ IDLE_BURN   │
│                                 │                 │
│                                 │  ── Events ──   │
│                                 │  12:30 RESIZED  │
│                                 │  12:00 STARTED  │
├─────────────────────────────────┴─────────────────┤
│ ↑↓:navigate  Enter:detail  s:start  t:terminate   │
│ R:restart  l:logs  r:refresh  Esc:home            │
└───────────────────────────────────────────────────┘
```

**Table columns**: Name, State, Workers, Runtime, Idle Time, Flags

**Key bindings**:
| Key | Action | Armed? |
|-----|--------|--------|
| `↑/↓` or `j/k` | Navigate rows | No |
| `Enter` | Expand detail panel (or toggle) | No |
| `s` | Start selected cluster | **Yes** |
| `t` | Terminate selected cluster | **Yes** |
| `R` | Restart selected cluster | **Yes** |
| `l` | Open driver logs for selected cluster | No |
| `r` | Refresh list | No |
| `Esc` | Back to home | No |

**Armed actions**: If user presses `s`/`t`/`R` while unarmed, show a toast/notification: "Press A to arm first (30s window)". If armed, show a **confirmation dialog** with the cluster name before executing.

### 3.3 Jobs & Runs Screen

**Data source**: `JobOps(client)` — list_jobs, list_runs, get_run_detail

**Layout**: Three-zone — job list left, run list middle, run detail right.

```
┌──────────────────┬──────────────────┬──────────────┐
│  Jobs             │  Runs           │  Detail      │
├──────────────────┤──────────────────┤              │
│ ▸ etl_daily_pipe │ ▸ Run #456 ✗ 2h  │ State: FAIL  │
│   ml_training    │   Run #455 ✓ 1d  │ Duration: …  │
│   dbt_refresh    │   Run #454 ✓ 2d  │ Error:       │
│                  │                  │  NPE at …    │
│                  │                  │              │
│                  │                  │  ── Tasks ── │
│                  │                  │  extract ✓   │
│                  │                  │  transform ✗ │
│                  │                  │  load —      │
├──────────────────┴──────────────────┴──────────────┤
│ ↑↓:navigate  Enter:runs  l:logs  c:cancel          │
│ R:rerun  n:run-now  /:filter  Esc:back             │
└────────────────────────────────────────────────────┘
```

**Key bindings**:
| Key | Action | Armed? |
|-----|--------|--------|
| `↑/↓` or `j/k` | Navigate current pane | No |
| `Tab` | Move focus between panes (left → middle → right) | No |
| `Enter` | Select job → show runs; select run → show detail | No |
| `l` | Open logs for selected run | No |
| `c` | Cancel selected run | **Yes** |
| `R` | Re-run selected run | **Yes** |
| `n` | Run job now (trigger new run) | **Yes** |
| `/` | Filter jobs by name (inline search) | No |
| `r` | Refresh | No |
| `Esc` | Back one level (detail → runs → jobs → home) | No |

### 3.4 Log Viewer Screen

**Data source**: `LogOps(client)` — get_run_logs, get_cluster_driver_logs

**Layout**: Full-screen scrollable log viewer.

```
┌──────────────────────────────────────────────────┐
│  Logs — Run #456 (etl_daily_pipeline)            │
├──────────────────────────────────────────────────┤
│  [INFO]  2025-02-05 12:00:01  Starting extract…  │
│  [INFO]  2025-02-05 12:00:15  Extract complete…  │
│  [WARN]  2025-02-05 12:01:02  Skipping null ro…  │
│  [ERROR] 2025-02-05 12:02:30  NullPointerExcep…  │
│  [ERROR] 2025-02-05 12:02:30    at com.databri…  │
│  [ERROR] 2025-02-05 12:02:31    at org.apache.…  │
│  …                                               │
│  ▼ (auto-scroll active)                          │
├──────────────────────────────────────────────────┤
│ /:search  n/N:next/prev match  f:filter-severity │
│ G:bottom  g:top  b:bookmark  o:open-in-browser   │
│ Esc:back                                         │
└──────────────────────────────────────────────────┘
```

**Features**:
- **Severity coloring**: ERROR=red, WARN=yellow, INFO=default, DEBUG=dim. Use `LogLine.severity` from the models.
- **Search** (`/`): Inline regex search with match highlighting. `n`/`N` for next/prev match.
- **Filter** (`f`): Cycle through severity filters (ALL → ERROR → WARN+ → INFO+)
- **Auto-scroll**: Stick to bottom when new content arrives. Scrolling up disables auto-scroll, `G` re-enables.
- **Bookmark** (`b`): Toggle bookmark on current line (visual marker, no persistence needed).
- **Open in browser** (`o`): Open the Databricks URL from `LogBlock.fallback_url` in default browser.
- **Wrap**: Long lines should soft-wrap, not horizontal scroll.

### 3.5 Warehouses Screen

**Data source**: `WarehouseOps(client).list_all() → list[WarehouseSummary]`

**Layout**: Simple table with inline detail (similar to clusters but simpler).

**Table columns**: Name, State, Size, Type, Clusters (min-max), Auto-stop, Running Queries

**Key bindings**:
| Key | Action | Armed? |
|-----|--------|--------|
| `↑/↓` or `j/k` | Navigate | No |
| `Enter` | Show detail panel | No |
| `s` | Start warehouse | **Yes** |
| `S` | Stop warehouse | **Yes** |
| `r` | Refresh | No |
| `Esc` | Back to home | No |

### 3.6 Config Screen

**Data source**: `LazyDatabricksConfig`, `DatabricksClient.switch_profile()`

**Layout**:
```
┌──────────────────────────────────────────────────┐
│  Configuration                                   │
├──────────────────────────────────────────────────┤
│                                                  │
│  Active Profile:  dev  ✓                         │
│  Host:           https://dbc-xxxxx.cloud…        │
│  Auth Method:    PAT                             │
│  Cluster ID:     0205-123456-abcde               │
│                                                  │
│  ── Available Profiles ────────────────────────  │
│    ▸ dev        (active)                         │
│      staging                                     │
│      production                                  │
│                                                  │
│  ── Quick Actions ─────────────────────────────  │
│    [t] Test connection                           │
│    [Enter] Switch to selected profile            │
│                                                  │
├──────────────────────────────────────────────────┤
│ ↑↓:select profile  Enter:switch  t:test  Esc:back│
└──────────────────────────────────────────────────┘
```

**Behavior**:
- Switching profile calls `client.switch_profile(name)` and refreshes the home screen.
- Show auth method detected for each profile.
- Test connection shows success/failure toast.

---

## 4. Persistent UI Elements

### 4.1 Header Widget

Always visible at top of every screen.

```
LazyDatabricks          🟢 READ-ONLY    Profile: dev
```

When armed:
```
LazyDatabricks          🔴 ARMED (25s)   Profile: dev
```

- The armed countdown should update every second (use `set_interval` or Textual timer).
- Use `ArmedGuard.status_display` for the text.
- Use `ArmedGuard.remaining_seconds` for live countdown.

### 4.2 Status Bar

Always visible at bottom. Context-sensitive — shows keybindings relevant to the current screen.

### 4.3 Global Key Bindings

These work on **every screen**:

| Key | Action |
|-----|--------|
| `c` | Switch to Clusters screen |
| `j` | Switch to Jobs screen |
| `w` | Switch to Warehouses screen |
| `l` | Switch to Logs screen (only if a context exists, else no-op) |
| `h` or `Home` | Switch to Home screen |
| `A` | Toggle armed mode |
| `?` | Show help overlay (keybinding reference) |
| `q` | Quit application |
| `:` | Command palette (Textual built-in, or simple command input) |

**Important**: Screen-specific bindings (like `s` for start on clusters) should only be active on that screen. Global nav keys should not conflict with screen-specific keys — if there's a conflict, screen-specific wins when that screen is focused.

---

## 5. Visual Design

### 5.1 Color Palette

Define in `tui/theme.py`. Use Textual's built-in styling system.

| Purpose | Color |
|---------|-------|
| RUNNING / SUCCESS / CONNECTED | Green |
| ERROR / FAILED / TERMINATED(error) | Red |
| WARNING / IDLE_BURN / STALE | Yellow/Amber |
| PENDING / STARTING | Cyan |
| TERMINATED / STOPPED (normal) | Dim/Grey |
| ARMED indicator | Red background, white text |
| READ-ONLY indicator | Green text |
| Selected row | Reverse/highlight |
| Table headers | Bold |

### 5.2 State Icons

Use the icons already defined on models:
- `SparkStatus.icon` → ✓/✗/⚠/—
- `JobSummary.health_display` → ✓/✗/●/—
- `ClusterFlag` values are display strings

### 5.3 Layout Principles

- **No mouse required** — everything accessible by keyboard
- **Responsive** — tables should use available width, detail panels can collapse on narrow terminals
- **Minimal chrome** — no decorative borders, let content breathe
- Use Textual's `Horizontal`/`Vertical` containers and CSS-like sizing

---

## 6. Data Refresh & Async

### 6.1 Background Refresh

- Home screen: auto-refresh every 60 seconds
- Other screens: auto-refresh every 30 seconds
- All refreshes should be **non-blocking** — use Textual's `work` decorator or `run_worker`
- Show a subtle loading indicator during refresh (e.g., spinner in header)
- Manual refresh (`r`) cancels any pending auto-refresh and starts a new one

### 6.2 API Calls

All API operations (`ClusterOps`, `JobOps`, etc.) are **synchronous** (they use the Databricks SDK which is sync). Wrap them in Textual workers:

```python
@work(thread=True)
def refresh_clusters(self) -> list[ClusterSummary]:
    return self.cluster_ops.list_all()
```

### 6.3 Error Handling

- API errors should show a toast notification, not crash the app
- If auth fails on startup, show a clear error screen with instructions
- Network errors during refresh should show a warning but keep stale data visible

---

## 7. Armed Mode UX Flow

This is critical for safety. Here's the full flow:

1. User sees `🟢 READ-ONLY` in header at all times
2. User presses `A` → header shows `🔴 ARMED (30s)` with countdown
3. Countdown ticks every second: `🔴 ARMED (29s)`, `🔴 ARMED (28s)`, …
4. User navigates to cluster, presses `t` to terminate
5. Since armed → **confirmation dialog** appears:
   ```
   ┌─────────────────────────────────┐
   │  Terminate cluster?              │
   │                                  │
   │  my-dev-cluster (0205-123456…)   │
   │                                  │
   │  [Enter] Confirm   [Esc] Cancel  │
   └─────────────────────────────────┘
   ```
6. User presses Enter → action executes → toast "Terminating my-dev-cluster…"
7. If TTL expires before action → auto-disarm, back to `🟢 READ-ONLY`
8. User can press `A` again to disarm early (toggle behavior)

---

## 8. Help Overlay

Pressing `?` on any screen shows a modal overlay listing all keybindings:

```
┌─────────────── LazyDatabricks Help ───────────────────┐
│                                                   │
│  Navigation                                       │
│    h     Home screen                              │
│    c     Clusters                                 │
│    j     Jobs & Runs                              │
│    w     Warehouses                               │
│    l     Logs (contextual)                        │
│    Esc   Back / Close                             │
│    q     Quit                                     │
│                                                   │
│  Actions (require armed mode)                     │
│    A     Arm/Disarm (30s window)                  │
│    s     Start (cluster/warehouse)                │
│    t     Terminate cluster                        │
│    S     Stop warehouse                           │
│    R     Restart cluster / Re-run job             │
│    c     Cancel run (on Jobs screen)              │
│    n     Run job now                              │
│                                                   │
│  General                                          │
│    r     Refresh current view                     │
│    /     Search / Filter                          │
│    ?     This help                                │
│    :     Command palette                          │
│                                                   │
│              [Esc] Close                          │
└───────────────────────────────────────────────────┘
```

---

## 9. Testing Requirements

### 9.1 Unit Tests

Create `tests/tui/` with tests for:
- **Widget rendering**: Header shows correct armed/disarmed state
- **Screen data binding**: Screens correctly call API ops and render model data
- **Key bindings**: Pressing keys triggers correct actions
- **Armed mode flow**: Confirm dialog appears only when armed

Use Textual's built-in testing support (`app.run_test()`).

### 9.2 Mock API Layer

Create `tests/conftest.py` with mock implementations:
- `MockClusterOps` returning fixture `ClusterSummary` objects
- `MockJobOps` returning fixture `JobSummary`/`RunSummary` objects
- etc.

This allows testing the TUI without a real Databricks connection.

---

## 10. Acceptance Criteria

The TUI is complete when:

- [ ] `lazydatabricks` (no subcommand) launches the TUI
- [ ] Home screen shows health snapshot and auto-refreshes
- [ ] All 6 screens are navigable via global hotkeys (h/c/j/w/l/config)
- [ ] Clusters screen shows table, detail panel, and supports start/terminate/restart
- [ ] Jobs screen shows job list → run list → run detail navigation
- [ ] Log viewer shows colored, searchable, filterable logs
- [ ] Warehouses screen shows table with start/stop
- [ ] Config screen shows profiles and supports switching
- [ ] Armed mode works end-to-end: A → countdown → action → confirm → execute
- [ ] Confirmation dialogs appear before all destructive actions
- [ ] Toast notifications for action results and errors
- [ ] Help overlay (`?`) works on all screens
- [ ] Status bar updates context-sensitively per screen
- [ ] Auto-refresh works without blocking the UI
- [ ] App handles API errors gracefully (toast, not crash)
- [ ] Existing CLI subcommands still work
- [ ] At least basic unit tests for widgets and key bindings

---

## 11. Implementation Notes

- **Start with the app shell**: Get `LazyDatabricksApp` launching with header, status bar, and home screen. Then add screens one at a time.
- **Use Textual CSS**: Define styles in the App or in external `.tcss` files, not inline.
- **Reuse model display properties**: Every model has computed `.xxx_display` properties. Use them — don't reformat.
- **Don't modify the models or API layers** unless you find a bug. If you need something the model doesn't provide, check if a display property already covers it.
- **Textual version**: We're using `textual>=1.0.0`. Use current Textual API patterns (Screen, Widget, CSS, workers).
- **Python 3.10+**: Use `|` union types, dataclasses, match statements where cleaner.
