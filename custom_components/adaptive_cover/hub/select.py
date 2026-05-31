"""Hub select entity — re-exports AdaptiveControlModeSelect.

Actual implementation lives in the top-level select.py so that HA's
platform loader finds ``async_setup_entry`` in the expected location.
"""

from __future__ import annotations

from ..select import AdaptiveControlModeSelect  # noqa: F401 — re-export

__all__ = ["AdaptiveControlModeSelect"]
