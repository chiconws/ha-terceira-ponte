"""The terceira_ponte integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import TerceiraPonteClient, TerceiraPonteError
from .const import CONF_CACHE_TTL_SECONDS, DEFAULT_CACHE_TTL_SECONDS

PLATFORMS: list[Platform] = [Platform.CAMERA]

type TerceiraPonteConfigEntry = ConfigEntry[TerceiraPonteClient]


async def async_setup_entry(hass: HomeAssistant, entry: TerceiraPonteConfigEntry) -> bool:
    """Set up Terceira Ponte from a config entry."""
    client = TerceiraPonteClient(
        async_get_clientsession(hass),
        cache_ttl_seconds=entry.options.get(
            CONF_CACHE_TTL_SECONDS,
            DEFAULT_CACHE_TTL_SECONDS,
        ),
    )

    try:
        await client.async_validate_connection()
    except TerceiraPonteError as err:
        raise ConfigEntryNotReady("Could not connect to Terceira Ponte service") from err

    entry.runtime_data = client
    await client.async_register_access()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TerceiraPonteConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
