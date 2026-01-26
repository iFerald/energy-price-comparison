from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME

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
            schema = vol.Schema(
                {
                    vol.Optional(CONF_NAME, default="Energy Price Comparison"): str,
                    vol.Required(CONF_PRICE_ENTITY, default="sensor.rce_pse_price"): str,
                    vol.Required(CONF_ENERGY_ENTITY, default="sensor.deye_daily_energy_bought"): str,
                    vol.Required(CONF_G11_RATE, default=DEFAULT_G11_RATE): vol.Coerce(float),
                }
            )
            return self.async_show_form(step_id="user", data_schema=schema)

        title = user_input.get(CONF_NAME, "Energy Price Comparison")
        data = {
            CONF_PRICE_ENTITY: user_input[CONF_PRICE_ENTITY],
            CONF_ENERGY_ENTITY: user_input[CONF_ENERGY_ENTITY],
            CONF_G11_RATE: user_input[CONF_G11_RATE],
        }
        return self.async_create_entry(title=title, data=data)
