"""Config flow for the ha_terceira_ponte integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .client import TerceiraPonteClient, TerceiraPonteError
from .const import (
    CONF_CACHE_TTL_SECONDS,
    DEFAULT_CACHE_TTL_SECONDS,
    DOMAIN,
    MAX_CACHE_TTL_SECONDS,
    MIN_CACHE_TTL_SECONDS,
    NAME,
)

_LOGGER = logging.getLogger(__name__)


class TerceiraPonteConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Terceira Ponte."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = TerceiraPonteClient(
                session,
                cache_ttl_seconds=DEFAULT_CACHE_TTL_SECONDS,
            )

            try:
                await client.async_validate_connection()
            except TerceiraPonteError:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({}),
                    errors={"base": "cannot_connect"},
                )
            except Exception:
                _LOGGER.exception("Unexpected error validating Terceira Ponte")
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({}),
                    errors={"base": "unknown"},
                )

            return self.async_create_entry(title=NAME, data={})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Get the options flow for this handler."""
        return TerceiraPonteOptionsFlow(config_entry)


class TerceiraPonteOptionsFlow(OptionsFlow):
    """Handle options flow for Terceira Ponte."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None):
        """Manage the options."""
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                options=user_input,
            )
            await self.hass.config_entries.async_reload(self._config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CACHE_TTL_SECONDS,
                        default=self._config_entry.options.get(
                            CONF_CACHE_TTL_SECONDS,
                            DEFAULT_CACHE_TTL_SECONDS,
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_CACHE_TTL_SECONDS,
                            max=MAX_CACHE_TTL_SECONDS,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    )
                }
            ),
        )
