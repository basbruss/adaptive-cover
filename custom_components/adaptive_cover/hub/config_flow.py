"""Hub config-flow helpers.

Contains shared constants and utilities used by the config-flow
steps that deal with the singleton 'All Blinds' hub entry.

The actual ``ConfigFlowHandler`` and ``OptionsFlowHandler`` classes
live in the top-level ``config_flow.py``.
"""

from __future__ import annotations

from ..const import ALL_BLINDS_TITLE, CONF_IS_HUB

# Default data payload written to ConfigEntry.data when the hub entry
# is created (either manually via the UI or auto-bootstrapped on first
non-hub setup).
HUB_ENTRY_DATA: dict = {
    "name": ALL_BLINDS_TITLE,
    CONF_IS_HUB: True,
}


def is_hub_entry(entry_data: dict) -> bool:
    """Return True when *entry_data* belongs to a hub config entry."""
    return bool(entry_data.get(CONF_IS_HUB))


__all__ = ["HUB_ENTRY_DATA", "is_hub_entry"]
