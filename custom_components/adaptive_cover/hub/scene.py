"""Hub scene entities — re-exports AdaptiveCoverScene.

Actual implementation lives in the top-level scene.py so that HA's
platform loader finds ``async_setup_entry`` in the expected location.
"""

from __future__ import annotations

from ..scene import AdaptiveCoverScene  # noqa: F401 — re-export

__all__ = ["AdaptiveCoverScene"]
