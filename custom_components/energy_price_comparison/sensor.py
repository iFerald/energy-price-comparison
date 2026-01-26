from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for a config entry."""
    async_add_entities([EnergyPriceComparisonExampleSensor()])


class EnergyPriceComparisonExampleSensor(SensorEntity):
    _attr_name = "Energy Price Comparison Example"
    _attr_unique_id = "energy_price_comparison_example"
    _attr_native_unit_of_measurement = "EUR/kWh"

    @property
    def native_value(self):
        return 0.0
