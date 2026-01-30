from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

from .const import (
    DOMAIN,
    CONF_PRICE_ENTITY,
    CONF_ENERGY_ENTITY,
    DEFAULT_PRICE_ENTITY,
    DEFAULT_ENERGY_ENTITY,
    
    CONF_G11_RATE,
    DEFAULT_G11_RATE,
    
    CONF_G12_DAY_RATE,
    CONF_G12_NIGHT_RATE,
    CONF_G12_DAY_RANGE_1_START,
    CONF_G12_DAY_RANGE_2_SUMMER_START,
    CONF_G12_DAY_RANGE_2_WINTER_START,
    CONF_G12_NIGHT_RANGE_1_SUMMER_START,
    CONF_G12_NIGHT_RANGE_1_WINTER_START,
    CONF_G12_NIGHT_RANGE_2_START,

    DEFAULT_G12_DAY_RATE,
    DEFAULT_G12_NIGHT_RATE,
    DEFAULT_G12_DAY_RANGE_1_START,
    DEFAULT_G12_DAY_RANGE_2_SUMMER_START,
    DEFAULT_G12_DAY_RANGE_2_WINTER_START,
    DEFAULT_G12_NIGHT_RANGE_1_SUMMER_START,
    DEFAULT_G12_NIGHT_RANGE_1_WINTER_START,
    DEFAULT_G12_NIGHT_RANGE_2_START,
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
                        
                        # --- G11 ---
                        vol.Required(
                            CONF_G11_RATE,
                            default=DEFAULT_G11_RATE,
                        ): vol.Coerce(float),

                        # --- G12 ---
                        vol.Required(CONF_G12_DAY_RATE, default=DEFAULT_G12_DAY_RATE): vol.Coerce(float),
                        vol.Required(CONF_G12_NIGHT_RATE, default=DEFAULT_G12_NIGHT_RATE): vol.Coerce(float),
        
                        vol.Required(CONF_G12_DAY_RANGE_1_START, default=DEFAULT_G12_DAY_RANGE_1_START): str,
                        vol.Required(CONF_G12_DAY_RANGE_2_SUMMER_START, default=DEFAULT_G12_DAY_RANGE_2_SUMMER_START): str,
                        vol.Required(CONF_G12_DAY_RANGE_2_WINTER_START, default=DEFAULT_G12_DAY_RANGE_2_WINTER_START): str,
        
                        vol.Required(CONF_G12_NIGHT_RANGE_1_SUMMER_START, default=DEFAULT_G12_NIGHT_RANGE_1_SUMMER_START): str,
                        vol.Required(CONF_G12_NIGHT_RANGE_1_WINTER_START, default=DEFAULT_G12_NIGHT_RANGE_1_WINTER_START): str,
                        vol.Required(CONF_G12_NIGHT_RANGE_2_START, default=DEFAULT_G12_NIGHT_RANGE_2_START): str,
                    }
                ),
            )

        return self.async_create_entry(
            title="Energy Price Comparison",
            data=user_input,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Energy Price Comparison."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(self, user_input=None):
        current_price = self._entry.options.get(
            CONF_PRICE_ENTITY,
            self._entry.data.get(CONF_PRICE_ENTITY, DEFAULT_PRICE_ENTITY),
        )
        current_energy = self._entry.options.get(
            CONF_ENERGY_ENTITY,
            self._entry.data.get(CONF_ENERGY_ENTITY, DEFAULT_ENERGY_ENTITY),
        )
        current_rate = self._entry.options.get(
            CONF_G11_RATE,
            self._entry.data.get(CONF_G11_RATE, DEFAULT_G11_RATE),
        )
        current_g12_day_rate = self._entry.options.get(
            CONF_G12_DAY_RATE,
            self._entry.data.get(CONF_G12_DAY_RATE, DEFAULT_G12_DAY_RATE),
        )
        current_g12_night_rate = self._entry.options.get(
            CONF_G12_NIGHT_RATE,
            self._entry.data.get(CONF_G12_NIGHT_RATE, DEFAULT_G12_NIGHT_RATE),
        )
        
        current_g12_day_range_1_start = self._entry.options.get(
            CONF_G12_DAY_RANGE_1_START,
            self._entry.data.get(CONF_G12_DAY_RANGE_1_START, DEFAULT_G12_DAY_RANGE_1_START),
        )
        current_g12_day_range_2_summer_start = self._entry.options.get(
            CONF_G12_DAY_RANGE_2_SUMMER_START,
            self._entry.data.get(CONF_G12_DAY_RANGE_2_SUMMER_START, DEFAULT_G12_DAY_RANGE_2_SUMMER_START),
        )
        current_g12_day_range_2_winter_start = self._entry.options.get(
            CONF_G12_DAY_RANGE_2_WINTER_START,
            self._entry.data.get(CONF_G12_DAY_RANGE_2_WINTER_START, DEFAULT_G12_DAY_RANGE_2_WINTER_START),
        )
        
        current_g12_night_range_1_summer_start = self._entry.options.get(
            CONF_G12_NIGHT_RANGE_1_SUMMER_START,
            self._entry.data.get(CONF_G12_NIGHT_RANGE_1_SUMMER_START, DEFAULT_G12_NIGHT_RANGE_1_SUMMER_START),
        )
        current_g12_night_range_1_winter_start = self._entry.options.get(
            CONF_G12_NIGHT_RANGE_1_WINTER_START,
            self._entry.data.get(CONF_G12_NIGHT_RANGE_1_WINTER_START, DEFAULT_G12_NIGHT_RANGE_1_WINTER_START),
        )
        current_g12_night_range_2_start = self._entry.options.get(
            CONF_G12_NIGHT_RANGE_2_START,
            self._entry.data.get(CONF_G12_NIGHT_RANGE_2_START, DEFAULT_G12_NIGHT_RANGE_2_START),
        )

        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        # Existing
                        vol.Required(CONF_PRICE_ENTITY, default=current_price): str,
                        vol.Required(CONF_ENERGY_ENTITY, default=current_energy): str,
                        vol.Required(CONF_G11_RATE, default=current_rate): vol.Coerce(float),
                
                        # G12 rates
                        vol.Required(CONF_G12_DAY_RATE, default=current_g12_day_rate): vol.Coerce(float),
                        vol.Required(CONF_G12_NIGHT_RATE, default=current_g12_night_rate): vol.Coerce(float),
                
                        # G12 time ranges (HH:MM strings for now)
                        vol.Required(CONF_G12_DAY_RANGE_1_START, default=current_g12_day_range_1_start): str,
                        vol.Required(CONF_G12_DAY_RANGE_2_SUMMER_START, default=current_g12_day_range_2_summer_start): str,
                        vol.Required(CONF_G12_DAY_RANGE_2_WINTER_START, default=current_g12_day_range_2_winter_start): str,
                
                        vol.Required(CONF_G12_NIGHT_RANGE_1_SUMMER_START, default=current_g12_night_range_1_summer_start): str,
                        vol.Required(CONF_G12_NIGHT_RANGE_1_WINTER_START, default=current_g12_night_range_1_winter_start): str,
                        vol.Required(CONF_G12_NIGHT_RANGE_2_START, default=current_g12_night_range_2_start): str,
                    }
                ),
            )

        return self.async_create_entry(title="", data=user_input)
