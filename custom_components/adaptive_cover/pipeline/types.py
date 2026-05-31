"""Typed snapshot passed through the pipeline handler chain."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from ..coordinator import AdaptiveDataUpdateCoordinator


@dataclass
class PipelineSnapshot:
    """Immutable-ish view of coordinator state for one pipeline pass.

    Attributes
    ----------
    hass:
        The Home Assistant instance.
    coordinator:
        The Adaptive Cover coordinator for this config entry.
    calculated_position:
        The raw adaptive position produced by the sun/climate calculation
        (0–100).  Handlers may replace this value.
    security_toggle:
        Whether security mode is currently enabled on this coordinator.
    security_active:
        True when security mode is ON **and** no presence is detected.
        Computed by the coordinator's ``security_active`` property.
    climate_mode:
        Whether climate mode is active on this entry.
    control_method:
        Current climate branch: ``"summer"``, ``"winter"``, or
        ``"intermediate"``.
    min_position:
        Configured ``CONF_MIN_POSITION`` value (may be ``None``).
    override_position:
        Set by a handler to replace ``calculated_position``.  ``None``
        means "no override — use ``calculated_position``".
    skip_move:
        Set to ``True`` by a handler to suppress any cover movement
        entirely for this cycle.
    """

    hass: "HomeAssistant"
    coordinator: "AdaptiveDataUpdateCoordinator"

    # --- inputs (set by coordinator before entering the chain) ---
    calculated_position: int = 0
    security_toggle: bool = False
    security_active: bool = False
    climate_mode: bool = False
    control_method: str = "intermediate"
    min_position: int | None = None

    # --- outputs (written by handlers) ---
    override_position: int | None = None
    skip_move: bool = False

    # --- metadata ---
    handler_log: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Helpers                                                               #
    # ------------------------------------------------------------------ #

    @property
    def effective_position(self) -> int:
        """Return the position that should actually be applied.

        Returns ``override_position`` if a handler set one, otherwise
        ``calculated_position``.
        """
        if self.override_position is not None:
            return self.override_position
        return self.calculated_position
