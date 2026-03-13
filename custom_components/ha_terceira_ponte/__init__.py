"""The ha_terceira_ponte integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import TerceiraPonteClient, TerceiraPonteError
from .const import CONF_CACHE_TTL_SECONDS, DEFAULT_CACHE_TTL_SECONDS, DOMAIN

PLATFORMS: list[Platform] = [Platform.CAMERA]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Terceira Ponte integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Terceira Ponte from a config entry."""
    session = async_get_clientsession(hass)
    client = TerceiraPonteClient(
        session,
        cache_ttl_seconds=entry.options.get(
            CONF_CACHE_TTL_SECONDS,
            DEFAULT_CACHE_TTL_SECONDS,
        ),
    )

    try:
        await client.async_validate_connection()
    except TerceiraPonteError as err:
        raise ConfigEntryNotReady("Could not connect to Terceira Ponte service") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client
    await client.async_register_access()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
