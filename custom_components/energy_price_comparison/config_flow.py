from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

from .const import (
    DOMAIN,
    CONF_PRICE_ENTITY,
    CONF_TOTAL_ENERGY_ENTITY,
    DEFAULT_PRICE_ENTITY,
    DEFAULT_TOTAL_ENERGY_ENTITY,

    # G11
    CONF_G11_RATE,
    DEFAULT_G11_RATE,

    # G12 rates
    CONF_G12_DAY_RATE,
    CONF_G12_NIGHT_RATE,
    DEFAULT_G12_DAY_RATE,
    DEFAULT_G12_NIGHT_RATE,

    # G12 ranges
    CONF_G12_DAY_RANGE_1_START,
    CONF_G12_DAY_RANGE_2_SUMMER_START,
    CONF_G12_NIGHT_RANGE_1_SUMMER_START,
    CONF_G12_DAY_RANGE_2_WINTER_START,
    CONF_G12_NIGHT_RANGE_1_WINTER_START,
    CONF_G12_NIGHT_RANGE_2_START,
    DEFAULT_G12_DAY_RANGE_1_START,
    DEFAULT_G12_DAY_RANGE_2_SUMMER_START,
    DEFAULT_G12_NIGHT_RANGE_1_SUMMER_START,
    DEFAULT_G12_DAY_RANGE_2_WINTER_START,
    DEFAULT_G12_NIGHT_RANGE_1_WINTER_START,
    DEFAULT_G12_NIGHT_RANGE_2_START,

    # G12w rates
    CONF_G12W_DAY_RATE,
    CONF_G12W_NIGHT_RATE,
    DEFAULT_G12W_DAY_RATE,
    DEFAULT_G12W_NIGHT_RATE,

    # G12n rates
    CONF_G12N_DAY_RATE,
    CONF_G12N_NIGHT_RATE,
    DEFAULT_G12N_DAY_RATE,
    DEFAULT_G12N_NIGHT_RATE,

    # G12w ranges
    CONF_G12W_DAY_RANGE_1_START,
    CONF_G12W_DAY_RANGE_2_SUMMER_START,
    CONF_G12W_NIGHT_RANGE_1_SUMMER_START,
    CONF_G12W_DAY_RANGE_2_WINTER_START,
    CONF_G12W_NIGHT_RANGE_1_WINTER_START,
    CONF_G12W_NIGHT_RANGE_2_START,
    DEFAULT_G12W_DAY_RANGE_1_START,
    DEFAULT_G12W_DAY_RANGE_2_SUMMER_START,
    DEFAULT_G12W_NIGHT_RANGE_1_SUMMER_START,
    DEFAULT_G12W_DAY_RANGE_2_WINTER_START,
    DEFAULT_G12W_NIGHT_RANGE_1_WINTER_START,
    DEFAULT_G12W_NIGHT_RANGE_2_START,

    # G12n ranges
    CONF_G12N_DAY_START,
    CONF_G12N_NIGHT_START,
    DEFAULT_G12N_DAY_START,
    DEFAULT_G12N_NIGHT_START,
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
                        # Sensors:
                        vol.Required(CONF_PRICE_ENTITY, default=DEFAULT_PRICE_ENTITY): str,
                        vol.Required(CONF_TOTAL_ENERGY_ENTITY, default=DEFAULT_TOTAL_ENERGY_ENTITY): str,

                        # Tariff rates:
                        vol.Required(CONF_G11_RATE, default=DEFAULT_G11_RATE): vol.Coerce(float),

                        vol.Required(CONF_G12_DAY_RATE, default=DEFAULT_G12_DAY_RATE): vol.Coerce(float),
                        vol.Required(CONF_G12_NIGHT_RATE, default=DEFAULT_G12_NIGHT_RATE): vol.Coerce(float),

                        vol.Required(CONF_G12W_DAY_RATE, default=DEFAULT_G12W_DAY_RATE): vol.Coerce(float),
                        vol.Required(CONF_G12W_NIGHT_RATE, default=DEFAULT_G12W_NIGHT_RATE): vol.Coerce(float),

                        vol.Required(CONF_G12N_DAY_RATE, default=DEFAULT_G12N_DAY_RATE): vol.Coerce(float),
                        vol.Required(CONF_G12N_NIGHT_RATE, default=DEFAULT_G12N_NIGHT_RATE): vol.Coerce(float),

                        # Ranges (HH:MM):
                        vol.Required(CONF_G12_DAY_RANGE_1_START, default=DEFAULT_G12_DAY_RANGE_1_START): str,
                        vol.Required(CONF_G12_NIGHT_RANGE_1_SUMMER_START, default=DEFAULT_G12_NIGHT_RANGE_1_SUMMER_START): str,
                        vol.Required(CONF_G12_DAY_RANGE_2_SUMMER_START, default=DEFAULT_G12_DAY_RANGE_2_SUMMER_START): str,
                        vol.Required(CONF_G12_NIGHT_RANGE_1_WINTER_START, default=DEFAULT_G12_NIGHT_RANGE_1_WINTER_START): str,
                        vol.Required(CONF_G12_DAY_RANGE_2_WINTER_START, default=DEFAULT_G12_DAY_RANGE_2_WINTER_START): str,
                        vol.Required(CONF_G12_NIGHT_RANGE_1_WINTER_START, default=DEFAULT_G12_NIGHT_RANGE_1_WINTER_START): str,
                        vol.Required(CONF_G12_NIGHT_RANGE_2_START, default=DEFAULT_G12_NIGHT_RANGE_2_START): str,

                        vol.Required(CONF_G12W_DAY_RANGE_1_START, default=DEFAULT_G12W_DAY_RANGE_1_START): str,
                        vol.Required(CONF_G12W_NIGHT_RANGE_1_SUMMER_START, default=DEFAULT_G12W_NIGHT_RANGE_1_SUMMER_START): str,
                        vol.Required(CONF_G12W_DAY_RANGE_2_SUMMER_START, default=DEFAULT_G12W_DAY_RANGE_2_SUMMER_START): str,
                        vol.Required(CONF_G12W_NIGHT_RANGE_1_WINTER_START, default=DEFAULT_G12W_NIGHT_RANGE_1_WINTER_START): str,
                        vol.Required(CONF_G12W_DAY_RANGE_2_WINTER_START, default=DEFAULT_G12W_DAY_RANGE_2_WINTER_START): str,
                        vol.Required(CONF_G12W_NIGHT_RANGE_2_START, default=DEFAULT_G12W_NIGHT_RANGE_2_START): str,

                        vol.Required(CONF_G12N_DAY_START, default=DEFAULT_G12N_DAY_START): str,
                        vol.Required(CONF_G12N_NIGHT_START, default=DEFAULT_G12N_NIGHT_START): str,
                    }
                ),
            )

        return self.async_create_entry(title="Energy Price Comparison", data=user_input)

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Energy Price Comparison."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    def _get(self, key, default):
        return self._entry.options.get(key, self._entry.data.get(key, default))

    async def async_step_init(self, user_input=None):
        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        # Sensors:
                        vol.Required(CONF_PRICE_ENTITY, default=self._get(CONF_PRICE_ENTITY, DEFAULT_PRICE_ENTITY)): str,
                        vol.Required(CONF_TOTAL_ENERGY_ENTITY, default=self._get(CONF_TOTAL_ENERGY_ENTITY, DEFAULT_TOTAL_ENERGY_ENTITY)): str,

                        # Tariff rates:
                        vol.Required(CONF_G11_RATE, default=self._get(CONF_G11_RATE, DEFAULT_G11_RATE)): vol.Coerce(float),

                        vol.Required(CONF_G12_DAY_RATE, default=self._get(CONF_G12_DAY_RATE, DEFAULT_G12_DAY_RATE)): vol.Coerce(float),
                        vol.Required(CONF_G12_NIGHT_RATE, default=self._get(CONF_G12_NIGHT_RATE, DEFAULT_G12_NIGHT_RATE)): vol.Coerce(float),

                        vol.Required(CONF_G12W_DAY_RATE, default=self._get(CONF_G12W_DAY_RATE, DEFAULT_G12W_DAY_RATE)): vol.Coerce(float),
                        vol.Required(CONF_G12W_NIGHT_RATE, default=self._get(CONF_G12W_NIGHT_RATE, DEFAULT_G12W_NIGHT_RATE)): vol.Coerce(float),

                        vol.Required(CONF_G12N_DAY_RATE, default=self._get(CONF_G12N_DAY_RATE, DEFAULT_G12N_DAY_RATE)): vol.Coerce(float),
                        vol.Required(CONF_G12N_NIGHT_RATE, default=self._get(CONF_G12N_NIGHT_RATE, DEFAULT_G12N_NIGHT_RATE)): vol.Coerce(float),

                        # Ranges:
                        vol.Required(CONF_G12_DAY_RANGE_1_START, default=self._get(CONF_G12_DAY_RANGE_1_START, DEFAULT_G12_DAY_RANGE_1_START)): str,
                        vol.Required(CONF_G12_NIGHT_RANGE_1_SUMMER_START, default=self._get(CONF_G12_NIGHT_RANGE_1_SUMMER_START, DEFAULT_G12_NIGHT_RANGE_1_SUMMER_START)): str,
                        vol.Required(CONF_G12_DAY_RANGE_2_SUMMER_START, default=self._get(CONF_G12_DAY_RANGE_2_SUMMER_START, DEFAULT_G12_DAY_RANGE_2_SUMMER_START)): str,
                        vol.Required(CONF_G12_NIGHT_RANGE_1_WINTER_START, default=self._get(CONF_G12_NIGHT_RANGE_1_WINTER_START, DEFAULT_G12_NIGHT_RANGE_1_WINTER_START)): str,
                        vol.Required(CONF_G12_DAY_RANGE_2_WINTER_START, default=self._get(CONF_G12_DAY_RANGE_2_WINTER_START, DEFAULT_G12_DAY_RANGE_2_WINTER_START)): str,
                        vol.Required(CONF_G12_NIGHT_RANGE_2_START, default=self._get(CONF_G12_NIGHT_RANGE_2_START, DEFAULT_G12_NIGHT_RANGE_2_START)): str,

                        vol.Required(CONF_G12W_DAY_RANGE_1_START, default=self._get(CONF_G12W_DAY_RANGE_1_START, DEFAULT_G12W_DAY_RANGE_1_START)): str,
                        vol.Required(CONF_G12W_NIGHT_RANGE_1_SUMMER_START, default=self._get(CONF_G12W_NIGHT_RANGE_1_SUMMER_START, DEFAULT_G12W_NIGHT_RANGE_1_SUMMER_START)): str,
                        vol.Required(CONF_G12W_DAY_RANGE_2_SUMMER_START, default=self._get(CONF_G12W_DAY_RANGE_2_SUMMER_START, DEFAULT_G12W_DAY_RANGE_2_SUMMER_START)): str,
                        vol.Required(CONF_G12W_NIGHT_RANGE_1_WINTER_START, default=self._get(CONF_G12W_NIGHT_RANGE_1_WINTER_START, DEFAULT_G12W_NIGHT_RANGE_1_WINTER_START)): str,
                        vol.Required(CONF_G12W_DAY_RANGE_2_WINTER_START, default=self._get(CONF_G12W_DAY_RANGE_2_WINTER_START, DEFAULT_G12W_DAY_RANGE_2_WINTER_START)): str,
                        vol.Required(CONF_G12W_NIGHT_RANGE_2_START, default=self._get(CONF_G12W_NIGHT_RANGE_2_START, DEFAULT_G12W_NIGHT_RANGE_2_START)): str,

                        vol.Required(CONF_G12N_DAY_START, default=self._get(CONF_G12N_DAY_START, DEFAULT_G12N_DAY_START)): str,
                        vol.Required(CONF_G12N_NIGHT_START, default=self._get(CONF_G12N_NIGHT_START, DEFAULT_G12N_NIGHT_START)): str,
                    }
                ),
            )

        return self.async_create_entry(title="", data=user_input)
