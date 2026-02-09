# Changelog

All notable changes to LazyDatabricks will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-02-06

### Added

**TUI Application**
- Full Textual-based terminal UI with keyboard-first navigation
- Home screen with health dashboard (workspace identity, Spark status, cluster/job/warehouse summaries)
- Clusters screen with DataTable listing and detail panel
- Jobs screen with three-pane hierarchy (Jobs → Runs → Detail)
- Logs screen with severity coloring, search, and filtering
- Warehouses screen with SQL warehouse management
- Config screen for profile switching and connection testing

**Safety Model (Armed Mode)**
- Default read-only mode for safe browsing
- Press `A` to arm for 30 seconds
- Visual countdown indicator in header
- Auto-disarm after TTL expires
- All destructive actions require armed mode

**Screens & Navigation**
- Global keybindings: h (home), c (clusters), j (jobs), w (warehouses), A (arm), ? (help), q (quit)
- Screen-specific keybindings for all actions
- Help overlay (?) showing all keybindings
- Toast notifications for feedback

**Cluster Operations**
- List all clusters with state, workers, runtime, idle time, flags
- Start terminated clusters (requires armed)
- Terminate running clusters (requires armed)
- Restart running clusters (requires armed)
- View cluster events and logs

**Job Operations**
- List jobs with schedule and health indicator
- List runs for selected job
- View run detail with tasks, duration, errors
- Run job now (requires armed)
- Cancel active run (requires armed)
- Rerun completed run (requires armed)
- View run logs with full log viewer

**Log Viewer**
- Severity coloring (ERROR=red, WARN=yellow, INFO=white, DEBUG=dim)
- Search (/) with match highlighting
- Navigate matches (n/N)
- Filter by severity (f cycles: ALL → ERROR → WARN+ → INFO+)
- Scroll navigation (G=bottom, g=top)
- Open in browser fallback

**Warehouse Operations**
- List SQL warehouses with state, size, type, sessions
- Start stopped warehouse (requires armed)
- Stop running warehouse (requires armed)

**Configuration**
- Support for Databricks SDK configuration (env vars, ~/.databrickscfg, CLI flags)
- Multiple profile support
- Profile switching at runtime
- Connection testing

**CLI Mode**
- `lazydatabricks` - Launch TUI (default)
- `lazydatabricks health` - Print health snapshot
- `lazydatabricks clusters` - List clusters
- `lazydatabricks jobs` - List jobs
- `lazydatabricks test` - Test connection

**Testing**
- 40 unit tests covering ArmedGuard, model display properties, keybindings
- Mock fixtures for API layer

### Technical Details

**Architecture**
- Models layer with pre-computed display properties
- API layer wrapping Databricks SDK
- TUI layer with Textual screens and widgets
- Clean separation of concerns

**Dependencies**
- databricks-sdk>=0.38.0
- textual>=1.0.0
- python-dotenv>=1.0.0
- httpx>=0.27.0

## [0.1.0] - 2025-01-XX

### Added
- Initial API client layer (DatabricksClient)
- Model definitions (Cluster, Job, Run, Warehouse, Health)
- ArmedGuard safety model
- CLI subcommands (health, clusters, jobs, test)
- Configuration loading from env/profiles
