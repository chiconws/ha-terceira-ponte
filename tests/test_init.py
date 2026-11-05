"""Tests for integration setup."""

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.terceira_ponte import async_setup_entry
from custom_components.terceira_ponte.client import TerceiraPonteError
from custom_components.terceira_ponte.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady


@pytest.mark.asyncio
async def test_setup_entry_raises_when_validation_fails(hass: HomeAssistant) -> None:
    """Setup should raise ConfigEntryNotReady when validation fails."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="Terceira Ponte")
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.terceira_ponte.TerceiraPonteClient.async_validate_connection",
            new=AsyncMock(side_effect=TerceiraPonteError("boom")),
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new=AsyncMock(),
        ),
        pytest.raises(ConfigEntryNotReady),
    ):
        await async_setup_entry(hass, entry)
