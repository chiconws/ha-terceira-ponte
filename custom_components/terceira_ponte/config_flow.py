"""Config flow for the terceira_ponte integration."""

import logging
from typing import Any, override

import probatio

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client = TerceiraPonteClient(
                async_get_clientsession(self.hass),
                cache_ttl_seconds=DEFAULT_CACHE_TTL_SECONDS,
            )
            try:
                await client.async_validate_connection()
            except TerceiraPonteError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error validating Terceira Ponte")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=NAME, data={})

        return self.async_show_form(
            step_id="user", data_schema=probatio.Schema({}), errors=errors
        )

    @staticmethod
    @callback
    @override
    def async_get_options_flow(config_entry: ConfigEntry) -> TerceiraPonteOptionsFlow:
        """Get the options flow for this handler."""
        return TerceiraPonteOptionsFlow()


class TerceiraPonteOptionsFlow(OptionsFlowWithReload):
    """Handle options flow for Terceira Ponte."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_CACHE_TTL_SECONDS,
                        default=self.config_entry.options.get(
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
