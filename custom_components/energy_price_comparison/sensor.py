from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    CONF_PRICE_ENTITY,
    CONF_ENERGY_ENTITY,
    CONF_G11_RATE,
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


def _as_float(state: str | None) -> float | None:
    if state in (None, STATE_UNKNOWN, STATE_UNAVAILABLE):
        return None
    try:
        return float(state)
    except (TypeError, ValueError):
        return None


def _get_entry_value(entry: ConfigEntry, key: str, default: Any) -> Any:
    """Read from entry.options -> entry.data -> default."""
    if entry.options and key in entry.options:
        return entry.options[key]
    if entry.data and key in entry.data:
        return entry.data[key]
    return default


class _EntryBackedSensor(SensorEntity):
    """Small base class for sensors backed by ConfigEntry options/data."""

    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, *, unique_suffix: str, name: str) -> None:
        self._entry = entry
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"

    def _read(self, key: str, default: Any) -> Any:
        return _get_entry_value(self._entry, key, default)


class G12DayRateConfigSensor(_EntryBackedSensor):
    _attr_native_unit_of_measurement = "PLN/kWh"
    _attr_icon = "mdi:cash"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, unique_suffix="g12_day_rate", name="G12 day rate (PLN/kWh)")

    @property
    def native_value(self) -> float:
        return float(self._read(CONF_G12_DAY_RATE, DEFAULT_G12_DAY_RATE))


class G12NightRateConfigSensor(_EntryBackedSensor):
    _attr_native_unit_of_measurement = "PLN/kWh"
    _attr_icon = "mdi:cash"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, unique_suffix="g12_night_rate", name="G12 night rate (PLN/kWh)")

    @property
    def native_value(self) -> float:
        return float(self._read(CONF_G12_NIGHT_RATE, DEFAULT_G12_NIGHT_RATE))


class G12ScheduleSummarySensor(_EntryBackedSensor):
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, unique_suffix="g12_schedule_summary", name="G12 schedule summary")

    @property
    def native_value(self) -> str:
        day1 = self._read(CONF_G12_DAY_RANGE_1_START, DEFAULT_G12_DAY_RANGE_1_START)

        day2_s = self._read(CONF_G12_DAY_RANGE_2_SUMMER_START, DEFAULT_G12_DAY_RANGE_2_SUMMER_START)
        day2_w = self._read(CONF_G12_DAY_RANGE_2_WINTER_START, DEFAULT_G12_DAY_RANGE_2_WINTER_START)

        night1_s = self._read(CONF_G12_NIGHT_RANGE_1_SUMMER_START, DEFAULT_G12_NIGHT_RANGE_1_SUMMER_START)
        night1_w = self._read(CONF_G12_NIGHT_RANGE_1_WINTER_START, DEFAULT_G12_NIGHT_RANGE_1_WINTER_START)

        night2 = self._read(CONF_G12_NIGHT_RANGE_2_START, DEFAULT_G12_NIGHT_RANGE_2_START)

        # Readable dashboard string (pure exposure, no calc)
        return (
            f"Summer: Day {day1}–{night1_s}, {day2_s}–{night2}; "
            f"Night {night1_s}–{day2_s}, {night2}–{day1}. "
            f"Winter: Day {day1}–{night1_w}, {day2_w}–{night2}; "
            f"Night {night1_w}–{day2_w}, {night2}–{day1}."
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    price_entity = entry.options.get(CONF_PRICE_ENTITY, entry.data.get(CONF_PRICE_ENTITY))
    energy_entity = entry.options.get(CONF_ENERGY_ENTITY, entry.data.get(CONF_ENERGY_ENTITY))
    g11_rate = float(entry.options.get(CONF_G11_RATE, entry.data.get(CONF_G11_RATE)))

    # Keep these for your existing G11CostTodaySensor attributes:
    g12_day_rate = float(_get_entry_value(entry, CONF_G12_DAY_RATE, DEFAULT_G12_DAY_RATE))
    g12_night_rate = float(_get_entry_value(entry, CONF_G12_NIGHT_RATE, DEFAULT_G12_NIGHT_RATE))

    g12_day_range_1_start = _get_entry_value(entry, CONF_G12_DAY_RANGE_1_START, DEFAULT_G12_DAY_RANGE_1_START)
    g12_day_range_2_summer_start = _get_entry_value(entry, CONF_G12_DAY_RANGE_2_SUMMER_START, DEFAULT_G12_DAY_RANGE_2_SUMMER_START)
    g12_day_range_2_winter_start = _get_entry_value(entry, CONF_G12_DAY_RANGE_2_WINTER_START, DEFAULT_G12_DAY_RANGE_2_WINTER_START)

    g12_night_range_1_summer_start = _get_entry_value(entry, CONF_G12_NIGHT_RANGE_1_SUMMER_START, DEFAULT_G12_NIGHT_RANGE_1_SUMMER_START)
    g12_night_range_1_winter_start = _get_entry_value(entry, CONF_G12_NIGHT_RANGE_1_WINTER_START, DEFAULT_G12_NIGHT_RANGE_1_WINTER_START)
    g12_night_range_2_start = _get_entry_value(entry, CONF_G12_NIGHT_RANGE_2_START, DEFAULT_G12_NIGHT_RANGE_2_START)

    sensors: list[SensorEntity] = [
        # existing sensors
        G11PricePlnPerKwhSensor(hass, price_entity),
        G11CostTodaySensor(
            hass,
            energy_entity,
            g11_rate,
            g12_day_rate=g12_day_rate,
            g12_night_rate=g12_night_rate,
            g12_ranges={
                "day_range_1_start": g12_day_range_1_start,
                "day_range_2_summer_start": g12_day_range_2_summer_start,
                "day_range_2_winter_start": g12_day_range_2_winter_start,
                "night_range_1_summer_start": g12_night_range_1_summer_start,
                "night_range_1_winter_start": g12_night_range_1_winter_start,
                "night_range_2_start": g12_night_range_2_start,
            },
        ),

        # NEW: pure config exposure entities
        G12DayRateConfigSensor(entry),
        G12NightRateConfigSensor(entry),
        G12ScheduleSummarySensor(entry),
    ]

    async_add_entities(sensors)

    # Auto-update when either source changes (your existing behavior)
    @callback
    def _handle_source_change(event: Any) -> None:
        for s in sensors:
            s.async_schedule_update_ha_state(True)

    async_track_state_change_event(hass, [price_entity, energy_entity], _handle_source_change)


class G11PricePlnPerKwhSensor(SensorEntity):
    """Convert PLN/MWh -> PLN/kWh from a source sensor."""

    _attr_name = "Current RCE price (PLN/kWh)"
    _attr_unique_id = "current_rce_price_pln_kwh"
    _attr_native_unit_of_measurement = "PLN/kWh"
    _attr_icon = "mdi:cash"

    def __init__(self, hass: HomeAssistant, source_entity_id: str) -> None:
        self.hass = hass
        self._source = source_entity_id

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "source_entity": self._source,
            "source_unit_expected": "PLN/MWh",
            "conversion": "value_pln_per_kwh = value_pln_per_mwh / 1000",
        }

    @property
    def native_value(self) -> float | None:
        st = self.hass.states.get(self._source)
        if not st:
            return None
        raw = _as_float(st.state)
        if raw is None:
            return None
        return raw / 1000.0


class G11CostTodaySensor(SensorEntity):
    """Compute today's cost using a fixed G11 rate and a daily energy bought sensor."""

    _attr_name = "G11 - Net Cost Today"
    _attr_unique_id = "energy_price_comparison_g11_net_cost_today"
    _attr_native_unit_of_measurement = "PLN"
    _attr_icon = "mdi:cash-multiple"

    def __init__(
        self,
        hass: HomeAssistant,
        energy_entity_id: str,
        g11_rate_pln_per_kwh: float,
        *,
        g12_day_rate: float,
        g12_night_rate: float,
        g12_ranges: dict[str, str],
    ) -> None:
        self.hass = hass
        self._energy = energy_entity_id
        self._rate = g11_rate_pln_per_kwh
        self._g12_day_rate = g12_day_rate
        self._g12_night_rate = g12_night_rate
        self._g12_ranges = g12_ranges

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "energy_entity": self._energy,
            "rate_pln_per_kwh": self._rate,
            "formula": "cost = rate_pln_per_kwh * energy_kwh",
            "g12_day_rate_pln_per_kwh": self._g12_day_rate,
            "g12_night_rate_pln_per_kwh": self._g12_night_rate,
            "g12_time_ranges": self._g12_ranges,
        }

    @property
    def native_value(self) -> float | None:
        st = self.hass.states.get(self._energy)
        if not st:
            return None
        energy_kwh = _as_float(st.state)
        if energy_kwh is None:
            return None
        return round(self._rate * energy_kwh, 4)
