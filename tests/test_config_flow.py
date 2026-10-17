"""Tests for the terceira_ponte config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.terceira_ponte.const import (
    CONF_CACHE_TTL_SECONDS,
    DEFAULT_CACHE_TTL_SECONDS,
    DOMAIN,
)


@pytest.mark.asyncio
async def test_user_flow_creates_entry(hass) -> None:
    """The user flow should create a config entry after validation."""
    with patch(
        "custom_components.terceira_ponte.config_flow.TerceiraPonteClient.async_validate_connection",
        new=AsyncMock(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )
        assert result["type"] == "form"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={},
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Terceira Ponte"
    assert result2["data"] == {}


@pytest.mark.asyncio
async def test_options_flow_updates_cache_ttl(hass) -> None:
    """The options flow should persist the cache TTL value."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={CONF_CACHE_TTL_SECONDS: DEFAULT_CACHE_TTL_SECONDS},
        title="Terceira Ponte",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_CACHE_TTL_SECONDS: 30},
    )

    assert result2["type"] == "create_entry"
    assert entry.options[CONF_CACHE_TTL_SECONDS] == 30
