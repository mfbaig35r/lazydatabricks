"""Armed mode controller — the safety model.

LazyDatabricks defaults to READ-ONLY. Destructive actions (restart, cancel,
terminate) require explicitly arming the system.

Usage:
    guard = ArmedGuard()

    # In TUI: user presses 'A'
    guard.arm()  # Armed for 30 seconds

    # Before any destructive action:
    if guard.is_armed:
        cluster_ops.terminate(cluster_id)
    else:
        show_message("Press A to arm before destructive actions")
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class ArmedGuard:
    """Controls the armed/disarmed safety state.

    - Default: disarmed (read-only)
    - Arm: enabled for `ttl_seconds` (default 30)
    - Auto-disarm after TTL expires
    - Manual disarm available
    """

    ttl_seconds: int = 30
    _armed_at: float = 0.0

    def arm(self) -> None:
        """Arm the system for destructive actions."""
        self._armed_at = time.time()

    def disarm(self) -> None:
        """Manually disarm."""
        self._armed_at = 0.0

    @property
    def is_armed(self) -> bool:
        """Check if currently armed (within TTL)."""
        if self._armed_at == 0.0:
            return False
        elapsed = time.time() - self._armed_at
        if elapsed > self.ttl_seconds:
            self._armed_at = 0.0  # Auto-disarm
            return False
        return True

    @property
    def remaining_seconds(self) -> int:
        """Seconds remaining before auto-disarm. 0 if disarmed."""
        if not self.is_armed:
            return 0
        elapsed = time.time() - self._armed_at
        remaining = self.ttl_seconds - elapsed
        return max(0, int(remaining))

    @property
    def status_display(self) -> str:
        """Status text for TUI display."""
        if self.is_armed:
            return f"🔴 ARMED ({self.remaining_seconds}s)"
        return "🟢 READ-ONLY"
