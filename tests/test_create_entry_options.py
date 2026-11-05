"""The create step must keep every option the setup forms asked for."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import voluptuous as vol

from custom_components.adaptive_cover.config_flow import (
    AUTOMATION_CONFIG,
    CLIMATE_MODE,
    CLIMATE_OPTIONS,
    HORIZONTAL_OPTIONS,
    INTERPOLATION_OPTIONS,
    SLOPED_OPTIONS,
    TILT_OPTIONS,
    VERTICAL_OPTIONS,
    WEATHER_OPTIONS,
    ConfigFlowHandler,
)
from custom_components.adaptive_cover.const import SensorType

# Every schema a create-flow step shows (blind_spot builds its schema at runtime
# from the same constants, so it is covered by the keys below).
SETUP_FORMS = (
    VERTICAL_OPTIONS,
    HORIZONTAL_OPTIONS,
    TILT_OPTIONS,
    SLOPED_OPTIONS,
    CLIMATE_MODE,
    CLIMATE_OPTIONS,
    WEATHER_OPTIONS,
    INTERPOLATION_OPTIONS,
    AUTOMATION_CONFIG,
)


def _keys(schema: vol.Schema) -> set[str]:
    return {str(key) for key in schema.schema}


@pytest.mark.asyncio
async def test_every_setup_field_reaches_the_entry_options():
    """Anything a create-flow form offers must be copied into the entry.

    async_step_update copies keys one by one, so a field added to a form but
    not to that list is silently dropped: the entry reads it as unset, and the
    options flow then shows it at its default rather than what the user chose.
    """
    offered = set().union(*(_keys(form) for form in SETUP_FORMS))
    config = {key: f"value-{key}" for key in offered}

    flow = ConfigFlowHandler()
    flow.type_blind = SensorType.BLIND
    flow.config = {**config, "name": "Test"}
    flow.async_create_entry = MagicMock(side_effect=lambda **kwargs: kwargs)

    entry = await flow.async_step_update()

    assert entry["title"] == "Vertical Test"
    missing = sorted(k for k in offered if entry["options"].get(k) != config[k])
    assert missing == []
