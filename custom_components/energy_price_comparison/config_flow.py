"""Validated configuration, with existing option keys preserved."""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .calculation import finite_number
from .const import DOMAIN
from .tariffs import settings


def schema(values):
    fields = {}
    for key, default in values.items():
        if key == "energy_entity":
            continue
        if key in ("price_entity", "total_energy_entity"):
            validate = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
        elif key.endswith("_start"):
            validate = str
        else:
            validate = vol.Coerce(float)
        fields[vol.Required(key, default=default)] = validate
    return vol.Schema(fields)


def validate_input(values, hass):
    clean, errors = dict(values), {}
    for key, value in values.items():
        if key.endswith("_pln_per_kwh"):
            rate = finite_number(value)
            if rate is None or rate < 0:
                errors[key] = "invalid_rate"
        elif key.endswith("_start"):
            try:
                clean[key] = datetime.strptime(value, "%H:%M").strftime("%H:%M")
            except (TypeError, ValueError):
                errors[key] = "invalid_time"
    state = hass.states.get(values.get("total_energy_entity"))
    if state and (state.attributes.get("unit_of_measurement") not in ("Wh", "kWh", "MWh") or state.attributes.get("state_class") not in ("total", "total_increasing")):
        errors["total_energy_entity"] = "invalid_energy_source"
    for tariff in ("g12", "g12w"):
        for season in ("summer", "winter"):
            keys = [f"{tariff}_day_range_1_start", f"{tariff}_night_range_1_{season}_start", f"{tariff}_day_range_2_{season}_start", f"{tariff}_night_range_2_start"]
            if not any(key in errors for key in keys) and not all(clean[a] < clean[b] for a, b in zip(keys, keys[1:])):
                errors["base"] = "invalid_ranges"
    if clean.get("g12n_day_start") == clean.get("g12n_night_start"):
        errors["base"] = "invalid_ranges"
    return clean, errors


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors = {}
        if user_input is not None:
            user_input, errors = validate_input(user_input, self.hass)
            if not errors:
                return self.async_create_entry(title="Energy Price Comparison", data=user_input)
        values = settings(SimpleNamespace(options={}, data={}))
        values.update(user_input or {})
        return self.async_show_form(step_id="user", data_schema=schema(values), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            user_input, errors = validate_input(user_input, self.hass)
            if not errors:
                return self.async_create_entry(title="", data=user_input)
        values = settings(self.config_entry)
        values.update(user_input or {})
        return self.async_show_form(step_id="init", data_schema=schema(values), errors=errors)
