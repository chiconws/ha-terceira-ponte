"""Tests for integration setup."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.ha_terceira_ponte import async_setup_entry
from custom_components.ha_terceira_ponte.client import CannotConnectError
from custom_components.ha_terceira_ponte.const import DOMAIN
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.mark.asyncio
async def test_setup_entry_raises_when_validation_fails(hass) -> None:
    """Setup should raise ConfigEntryNotReady when validation fails."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Terceira Ponte")
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.ha_terceira_ponte.TerceiraPonteClient.async_validate_connection",
            new=AsyncMock(side_effect=CannotConnectError("boom")),
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new=AsyncMock(),
        ),
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)
