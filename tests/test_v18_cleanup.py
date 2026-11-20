"""Tests for the v1.8.0 leftover device cleanup.

On HA 2026.8+ the lookup must use ``async_get_devices`` (``async_get_device``
is deprecated and breaks in 2027.8); older versions fall back to
``async_get_device``.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from custom_components.adaptive_cover import (
    _V18_LEFTOVER_IDENTIFIER,
    _cleanup_v18_leftover_device,
)

_DR_GET = "custom_components.adaptive_cover.dr.async_get"


class _NewRegistry:
    """Registry with the HA 2026.8+ API."""

    def __init__(self, devices):
        self.devices = devices
        self.removed = []
        self.async_get_device = MagicMock(side_effect=AssertionError("deprecated"))

    def async_get_devices(
        self, *, identifiers=None, connections=None, config_entry_id=None
    ):
        assert identifiers == {_V18_LEFTOVER_IDENTIFIER}
        return self.devices

    def async_remove_device(self, device_id):
        self.removed.append(device_id)


class _OldRegistry:
    """Registry before HA 2026.8 (no async_get_devices)."""

    def __init__(self, device):
        self.device = device
        self.removed = []

    def async_get_device(self, identifiers=None, connections=None):
        assert identifiers == {_V18_LEFTOVER_IDENTIFIER}
        return self.device

    def async_remove_device(self, device_id):
        self.removed.append(device_id)


def _run(registry):
    with patch(_DR_GET, return_value=registry):
        _cleanup_v18_leftover_device(MagicMock())
    return registry.removed


def test_new_api_removes_every_leftover():
    """HA 2026.8+: every leftover is removed, async_get_device is not used."""
    reg = _NewRegistry([SimpleNamespace(id="a"), SimpleNamespace(id="b")])
    assert _run(reg) == ["a", "b"]
    reg.async_get_device.assert_not_called()


def test_new_api_no_leftover_is_noop():
    """HA 2026.8+: nothing to remove."""
    assert _run(_NewRegistry([])) == []


def test_old_api_fallback_removes_leftover():
    """Before HA 2026.8: fallback to async_get_device removes the leftover."""
    assert _run(_OldRegistry(SimpleNamespace(id="x"))) == ["x"]


def test_old_api_fallback_no_leftover_is_noop():
    """Before HA 2026.8: nothing to remove."""
    assert _run(_OldRegistry(None)) == []
