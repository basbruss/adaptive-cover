"""SecurityHandler — closes covers when nobody is home.

Priority: 95 (above weather at ~80, below any future emergency handler
at 100).  Runs only when security mode is toggled ON and no presence
is detected for the config entry's presence entity.

Security position rules
-----------------------
- Climate mode active **and** branch is ``winter`` or ``intermediate``
      → ``min_position``  (keeps the home slightly ventilated / shaded)
- All other cases (no climate, or climate ``summer``)
      → 0 %  (fully closed — maximum protection)

Covers in manual override are skipped: the user's explicit action takes
precedence over the security mode.
"""

from __future__ import annotations

import logging

from ..types import PipelineSnapshot

_LOGGER = logging.getLogger(__name__)

PRIORITY = 95


class SecurityHandler:
    """Pipeline handler that enforces security positioning.

    The handler is stateless — a single instance can be shared across
    coordinator refreshes.
    """

    priority: int = PRIORITY

    # ------------------------------------------------------------------ #
    # Public API                                                            #
    # ------------------------------------------------------------------ #

    def handle(self, snapshot: PipelineSnapshot) -> PipelineSnapshot:
        """Apply security positioning when the conditions are met.

        Modifies *snapshot* in place and returns it.

        No-op conditions (returns snapshot unchanged):
          - ``security_toggle`` is False
          - ``security_active`` is False  (presence detected or no sensor)
        """
        if not snapshot.security_toggle:
            _LOGGER.debug("SecurityHandler: security_toggle is OFF — skipping")
            return snapshot

        if not snapshot.security_active:
            _LOGGER.debug(
                "SecurityHandler: security_active is False (presence detected "
                "or no sensor) — skipping"
            )
            return snapshot

        pos = self._security_position(snapshot)
        _LOGGER.debug(
            "SecurityHandler: security active → override_position=%d "
            "(climate_mode=%s, control_method=%s)",
            pos,
            snapshot.climate_mode,
            snapshot.control_method,
        )
        snapshot.override_position = pos
        snapshot.handler_log.append(
            f"SecurityHandler(priority={PRIORITY}): override={pos}"
        )
        return snapshot

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _security_position(snapshot: PipelineSnapshot) -> int:
        """Determine the target position for security mode.

        Parameters
        ----------
        snapshot:
            The current pipeline snapshot.

        Returns
        -------
        int
            Position to apply (0–100).
        """
        if snapshot.climate_mode and snapshot.control_method in (
            "intermediate",
            "winter",
        ):
            pos = snapshot.min_position or 0
            _LOGGER.debug(
                "SecurityHandler: climate branch=%s → min_position=%d",
                snapshot.control_method,
                pos,
            )
            return pos

        _LOGGER.debug("SecurityHandler: no-climate / summer branch → 0%%")
        return 0
