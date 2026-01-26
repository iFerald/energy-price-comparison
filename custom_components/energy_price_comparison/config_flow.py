from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

from .const import (
    DOMAIN,
    CONF_PRICE_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_G11_RATE,
    DEFAULT_G11_RATE,
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_PRICE_ENTITY,
                            default="sensor.rce_pse_price",
                        ): str,
                        vol.Required(
                            CONF_ENERGY_ENTITY,
                            default="sensor.deye_daily_energy_bought",
                        ): str,
                        vol.Required(
                            CONF_G11_RATE,
                            default=DEFAULT_G11_RATE,
                        ): vol.Coerce(float),
                    }
                ),
            )

        return self.async_create_entry(
            title="Energy Price Comparison",
            data=user_input,
        )

    async def async_step_options(self, user_input=None):
        return await OptionsFlowHandler(self.hass, self.context["entry_id"]).async_step_init(user_input)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, hass, entry_id):
        self.hass = hass
        self.entry = hass.config_entries.async_get_entry(entry_id)

    async def async_step_init(self, user_input=None):
        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_PRICE_ENTITY,
                            default=self.entry.data[CONF_PRICE_ENTITY],
                        ): str,
                        vol.Required(
                            CONF_ENERGY_ENTITY,
                            default=self.entry.data[CONF_ENERGY_ENTITY],
                        ): str,
                        vol.Required(
                            CONF_G11_RATE,
                            default=self.entry.data[CONF_G11_RATE],
                        ): vol.Coerce(float),
                    }
                ),
            )

        return self.async_create_entry(title="", data=user_input)
