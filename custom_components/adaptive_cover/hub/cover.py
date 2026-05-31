"""Hub cover entity — re-exports AdaptiveCoverAll from the top-level cover module.

This module exists so that the hub/ subpackage is self-documenting and
all hub entity classes can be imported from ``hub.*``.

The actual implementation lives in
``custom_components.adaptive_cover.cover.AdaptiveCoverAll``
because HA resolves ``async_setup_entry`` from the *top-level*
platform file, not from a subpackage.
"""

from __future__ import annotations

from ..cover import AdaptiveCoverAll  # noqa: F401 — re-export

__all__ = ["AdaptiveCoverAll"]
