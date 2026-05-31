"""Hub subpackage for the Adaptive Cover integration.

The 'All Blinds' hub entry is a singleton config entry
(``entry.data['is_hub'] is True``) that exposes aggregate entities
controlling every regular Adaptive Cover entry.

This subpackage contains the platform modules for the hub entry:

  cover       — AdaptiveCoverAll (aggregate cover)  [already in cover.py]
  switch      — AdaptiveControlAllSwitch + AdaptiveSecurityAllSwitch
  select      — AdaptiveControlModeSelect (4-state dropdown)
  scene       — AdaptiveCoverScene (all_open / all_closed)
  config_flow — helpers for hub config-flow steps

Note: the actual platform setup functions (``async_setup_entry``) live
in the top-level platform files (cover.py, switch.py, etc.) and branch
on ``entry.data.get(CONF_IS_HUB)``.  This subpackage provides the
hub-specific entity classes imported by those files.
"""
