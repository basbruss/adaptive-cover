"""This module provides a logging adapter that adds a configuration name to log messages."""

import logging


class ConfigContextAdapter(logging.LoggerAdapter):
    """A logging adapter that adds a configuration name to log messages."""

    def __init__(self, logger, extra=None):
        """Initialize the ConfigContextAdapter.

        Args:
            logger (logging.Logger): The logger instance to which this adapter is attached.
            extra (dict, optional): Additional context information. Defaults to None.

        """
        super().__init__(logger, extra or {})
        self.config_name = None

    def set_config_name(self, config_name):
        """Set the configuration name.

        Args:
            config_name (str): The name of the configuration to set.

        """
        self.config_name = config_name

    def process(self, msg, kwargs):
        """Process the log message and add the configuration name if set.

        Args:
            msg (str): The log message.
            kwargs (dict): Additional keyword arguments.

        Returns:
            tuple: The processed log message and keyword arguments.

        """
        if self.config_name:
            return f"[{self.config_name}] {msg}", kwargs
        else:
            return f"[Unknown] {msg}", kwargs
