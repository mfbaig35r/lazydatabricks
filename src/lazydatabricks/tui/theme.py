"""LazyDatabricks TUI theme — colors and CSS styles.

Defines the visual language for the entire TUI.
"""

from __future__ import annotations

# Color palette
COLORS = {
    # Status colors
    "success": "#00ff00",
    "error": "#ff0000",
    "warning": "#ffaa00",
    "info": "#00aaff",
    "muted": "#666666",

    # Armed mode
    "armed": "#ff4444",
    "disarmed": "#44ff44",

    # Cluster states
    "running": "#00ff00",
    "terminated": "#666666",
    "pending": "#ffaa00",
    "error_state": "#ff0000",

    # Log severities
    "log_error": "#ff4444",
    "log_warn": "#ffaa00",
    "log_info": "#ffffff",
    "log_debug": "#888888",

    # UI chrome
    "header_bg": "#1a1a2e",
    "panel_bg": "#16213e",
    "border": "#0f3460",
    "accent": "#e94560",
    "text": "#eee",
    "text_dim": "#888",
}

# Main application CSS
APP_CSS = """
/* ─── Global ─────────────────────────────────────────── */

Screen {
    background: #0a0a0f;
}

/* ─── Header Widget ─────────────────────────────────── */

#header {
    dock: top;
    height: 3;
    background: #1a1a2e;
    border-bottom: solid #0f3460;
    padding: 0 1;
}

#header-title {
    width: auto;
    color: #e94560;
    text-style: bold;
}

#header-status {
    width: auto;
    margin-left: 2;
}

#header-armed {
    width: auto;
    dock: right;
    margin-right: 1;
}

.armed-active {
    color: #ff4444;
    text-style: bold;
}

.armed-inactive {
    color: #44ff44;
}

/* ─── Status Bar ────────────────────────────────────── */

#status-bar {
    dock: bottom;
    height: 1;
    background: #1a1a2e;
    border-top: solid #0f3460;
    padding: 0 1;
}

.status-key {
    color: #e94560;
    text-style: bold;
}

.status-desc {
    color: #888;
    margin-right: 2;
}

/* ─── Screen Content ────────────────────────────────── */

#screen-content {
    padding: 1 2;
}

/* ─── Data Tables ───────────────────────────────────── */

DataTable {
    height: auto;
    max-height: 100%;
}

DataTable > .datatable--header {
    background: #1a1a2e;
    color: #e94560;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #0f3460;
}

DataTable > .datatable--hover {
    background: #162d50;
}

/* ─── State Styles ─────────────────────────────────── */

.state-running {
    color: #00ff00;
}

.state-terminated {
    color: #666666;
}

.state-pending {
    color: #ffaa00;
}

.state-error {
    color: #ff0000;
    text-style: bold;
}

/* ─── Result Styles ─────────────────────────────────── */

.result-success {
    color: #00ff00;
}

.result-failed {
    color: #ff0000;
    text-style: bold;
}

.result-canceled {
    color: #888888;
}

/* ─── Panels ────────────────────────────────────────── */

.panel {
    border: solid #0f3460;
    padding: 1;
    margin: 1 0;
}

.panel-title {
    color: #e94560;
    text-style: bold;
    margin-bottom: 1;
}

/* ─── Detail Panel ─────────────────────────────────── */

#detail-panel {
    width: 40%;
    dock: right;
    border-left: solid #0f3460;
    padding: 1 2;
    background: #0d0d15;
}

.detail-label {
    color: #888888;
}

.detail-value {
    color: #ffffff;
}

/* ─── Modals / Dialogs ─────────────────────────────── */

ModalScreen {
    align: center middle;
}

#confirm-dialog {
    width: 60;
    height: auto;
    min-height: 10;
    max-height: 20;
    background: #1a1a2e;
    border: thick #e94560;
    padding: 1 2;
}

#confirm-title {
    text-style: bold;
    color: #e94560;
    margin-bottom: 1;
}

#confirm-message {
    margin-bottom: 1;
}

#confirm-buttons {
    align: center bottom;
    height: 3;
}

#confirm-buttons Button {
    margin: 0 1;
}

/* ─── Help Overlay ─────────────────────────────────── */

#help-overlay {
    width: 80;
    height: auto;
    max-height: 80%;
    background: #1a1a2e;
    border: thick #0f3460;
    padding: 2;
}

#help-title {
    text-style: bold;
    color: #e94560;
    text-align: center;
    margin-bottom: 1;
}

.help-section {
    margin-top: 1;
}

.help-section-title {
    color: #e94560;
    text-style: bold;
}

.help-key {
    color: #ffaa00;
    min-width: 8;
}

.help-desc {
    color: #ffffff;
}

/* ─── Log Viewer ────────────────────────────────────── */

#log-viewer {
    height: 100%;
    border: solid #0f3460;
}

.log-line-error {
    color: #ff4444;
}

.log-line-warn {
    color: #ffaa00;
}

.log-line-info {
    color: #ffffff;
}

.log-line-debug {
    color: #666666;
}

.log-line-number {
    color: #444444;
    min-width: 5;
}

.log-bookmark {
    color: #e94560;
}

.log-search-match {
    background: #4a3000;
}

/* ─── Three-Pane Layout (Jobs screen) ───────────────── */

#pane-jobs {
    width: 1fr;
    border-right: solid #0f3460;
}

#pane-runs {
    width: 1fr;
    border-right: solid #0f3460;
}

#pane-detail {
    width: 1fr;
}

.pane-active {
    border: solid #e94560;
}

.pane-inactive {
    border: solid #0f3460;
}

/* ─── Input / Search ────────────────────────────────── */

#search-input {
    dock: bottom;
    height: 3;
    background: #1a1a2e;
    border-top: solid #0f3460;
}

#search-input Input {
    width: 100%;
}

/* ─── Toast Notifications ───────────────────────────── */

Toast {
    background: #1a1a2e;
    border: solid #0f3460;
    padding: 1 2;
}

Toast.-information {
    border: solid #00aaff;
}

Toast.-warning {
    border: solid #ffaa00;
}

Toast.-error {
    border: solid #ff0000;
}
"""
