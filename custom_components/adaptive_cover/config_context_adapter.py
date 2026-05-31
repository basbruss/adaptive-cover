"""Logging adapter that prefixes messages with the integration instance name."""

from __future__ import annotations

import logging


class ConfigContextAdapter(logging.LoggerAdapter):
    """Add the config entry name as a prefix to all log messages.

    Usage:
        logger = ConfigContextAdapter(logging.getLogger(__name__))
        logger.set_config_name("My Blind")
        logger.debug("Sun in window: %s", True)
        # → logs: "[My Blind] Sun in window: True"
    """

    def __init__(self, logger: logging.Logger, extra: dict | None = None) -> None:
        """Initialise the adapter with an optional name prefix."""
        super().__init__(logger, extra or {})
        self._config_name: str | None = None

    def set_config_name(self, name: str | None) -> None:
        """Store the config-entry name used as log prefix."""
        self._config_name = name

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        """Prepend the config-entry name to every log message."""
        if self._config_name:
            msg = f"[{self._config_name}] {msg}"
        return msg, kwargs
