"""Sensor platform for Energy Price Comparison."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
) -> None:
    """Set up the sensor platform (legacy YAML setup)."""
    async_add_entities([EnergyPriceComparisonExampleSensor()])


class EnergyPriceComparisonExampleSensor(SensorEntity):
    """Example sensor to prove the integration is installed and working."""

    _attr_name = "Energy Price Comparison (Example)"
    _attr_native_unit_of_measurement = "EUR/kWh"

    @property
    def native_value(self):
        return 0.0
