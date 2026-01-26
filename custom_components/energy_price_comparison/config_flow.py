from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN


class EnergyPriceComparisonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Energy Price Comparison."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # Prevent adding multiple instances unless you want to allow it.
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({}),
                description_placeholders={},
            )

        # Create the config entry
        return self.async_create_entry(title="Energy Price Comparison", data={})

    @callback
    def async_get_options_flow(self, config_entry):
        return EnergyPriceComparisonOptionsFlowHandler(config_entry)


class EnergyPriceComparisonOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Energy Price Comparison."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is None:
            return self.async_show_form(step_id="init", data_schema=vol.Schema({}))

        return self.async_create_entry(title="", data=user_input)
