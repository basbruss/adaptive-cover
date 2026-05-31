"""Hub switch entities — re-exports AdaptiveControlAllSwitch and AdaptiveSecurityAllSwitch.

Actual implementation lives in the top-level switch.py so that HA's
platform loader finds ``async_setup_entry`` in the expected location.
"""

from __future__ import annotations

from ..switch import (  # noqa: F401 — re-export
    AdaptiveControlAllSwitch,
    AdaptiveSecurityAllSwitch,
)

__all__ = ["AdaptiveControlAllSwitch", "AdaptiveSecurityAllSwitch"]
