from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .coordinator import EnergyCoordinator, PERIODS, TARIFFS
from .calculation import finite_number

from .const import (
    CONF_PRICE_ENTITY,
    CONF_TOTAL_ENERGY_ENTITY,
    DEFAULT_TOTAL_ENERGY_ENTITY,
    CONF_G11_RATE,
    DEFAULT_G11_RATE,
    # G12 rates + ranges
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
    # G12w rates + ranges
    CONF_G12W_DAY_RATE,
    CONF_G12W_NIGHT_RATE,
    DEFAULT_G12W_DAY_RATE,
    DEFAULT_G12W_NIGHT_RATE,
    CONF_G12W_DAY_RANGE_1_START,
    CONF_G12W_DAY_RANGE_2_SUMMER_START,
    CONF_G12W_DAY_RANGE_2_WINTER_START,
    CONF_G12W_NIGHT_RANGE_1_SUMMER_START,
    CONF_G12W_NIGHT_RANGE_1_WINTER_START,
    CONF_G12W_NIGHT_RANGE_2_START,
    DEFAULT_G12W_DAY_RANGE_1_START,
    DEFAULT_G12W_DAY_RANGE_2_SUMMER_START,
    DEFAULT_G12W_DAY_RANGE_2_WINTER_START,
    DEFAULT_G12W_NIGHT_RANGE_1_SUMMER_START,
    DEFAULT_G12W_NIGHT_RANGE_1_WINTER_START,
    DEFAULT_G12W_NIGHT_RANGE_2_START,
    # G12n rates + ranges
    CONF_G12N_DAY_RATE,
    CONF_G12N_NIGHT_RATE,
    DEFAULT_G12N_DAY_RATE,
    DEFAULT_G12N_NIGHT_RATE,
    CONF_G12N_DAY_START,
    CONF_G12N_NIGHT_START,
    DEFAULT_G12N_DAY_START,
    DEFAULT_G12N_NIGHT_START,
)


def _as_float(state: str | None) -> float | None:
    return finite_number(state)


def _get_entry_value(entry: ConfigEntry, key: str, default: Any) -> Any:
    """Read from entry.options -> entry.data -> default."""
    if entry.options and key in entry.options:
        return entry.options[key]
    if entry.data and key in entry.data:
        return entry.data[key]
    return default


class _EntryBackedSensor(SensorEntity):
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, *, unique_suffix: str, name: str) -> None:
        self._entry = entry
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"

    def _read(self, key: str, default: Any) -> Any:
        return _get_entry_value(self._entry, key, default)


class _RateConfigSensor(_EntryBackedSensor):
    _attr_native_unit_of_measurement = "PLN/kWh"
    _attr_icon = "mdi:cash"

    def __init__(self, entry: ConfigEntry, *, unique_suffix: str, name: str, key: str, default: float) -> None:
        super().__init__(entry, unique_suffix=unique_suffix, name=name)
        self._key = key
        self._default = default

    @property
    def native_value(self) -> float:
        return float(self._read(self._key, self._default))


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
        return (
            f"Summer: Day {day1}–{night1_s}, {day2_s}–{night2}; "
            f"Night {night1_s}–{day2_s}, {night2}–{day1}. "
            f"Winter: Day {day1}–{night1_w}, {day2_w}–{night2}; "
            f"Night {night1_w}–{day2_w}, {night2}–{day1}."
        )


class G12wScheduleSummarySensor(_EntryBackedSensor):
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, unique_suffix="g12w_schedule_summary", name="G12w schedule summary")

    @property
    def native_value(self) -> str:
        day1 = self._read(CONF_G12W_DAY_RANGE_1_START, DEFAULT_G12W_DAY_RANGE_1_START)
        day2_s = self._read(CONF_G12W_DAY_RANGE_2_SUMMER_START, DEFAULT_G12W_DAY_RANGE_2_SUMMER_START)
        day2_w = self._read(CONF_G12W_DAY_RANGE_2_WINTER_START, DEFAULT_G12W_DAY_RANGE_2_WINTER_START)
        night1_s = self._read(CONF_G12W_NIGHT_RANGE_1_SUMMER_START, DEFAULT_G12W_NIGHT_RANGE_1_SUMMER_START)
        night1_w = self._read(CONF_G12W_NIGHT_RANGE_1_WINTER_START, DEFAULT_G12W_NIGHT_RANGE_1_WINTER_START)
        night2 = self._read(CONF_G12W_NIGHT_RANGE_2_START, DEFAULT_G12W_NIGHT_RANGE_2_START)
        return (
            "Weekends: Night 00:00–24:00. "
            f"Summer (Mon–Fri): Day {day1}–{night1_s}, {day2_s}–{night2}; "
            f"Night {night1_s}–{day2_s}, {night2}–{day1}. "
            f"Winter (Mon–Fri): Day {day1}–{night1_w}, {day2_w}–{night2}; "
            f"Night {night1_w}–{day2_w}, {night2}–{day1}."
        )


class G12nScheduleSummarySensor(_EntryBackedSensor):
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, unique_suffix="g12n_schedule_summary", name="G12n schedule summary")

    @property
    def native_value(self) -> str:
        day_start = self._read(CONF_G12N_DAY_START, DEFAULT_G12N_DAY_START)
        night_start = self._read(CONF_G12N_NIGHT_START, DEFAULT_G12N_NIGHT_START)
        return (
            f"Mon–Sat: Day {day_start}–{night_start} (wrap); Night {night_start}–{day_start}. "
            "Sunday: Night 00:00–24:00."
        )


class G11PricePlnPerKwhSensor(SensorEntity):
    _attr_name = "Current RCE price (PLN/kWh)"
    _attr_unique_id = "current_rce_price_pln_kwh"
    _attr_native_unit_of_measurement = "PLN/kWh"
    _attr_icon = "mdi:cash"
    _attr_should_poll = False

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


class ComparisonCostSensor(CoordinatorEntity, SensorEntity):
    _attr_native_unit_of_measurement = "PLN"
    _attr_icon = "mdi:cash-clock"

    def __init__(self, coordinator, entry, tariff, period):
        super().__init__(coordinator)
        self._key = (tariff, period)
        label = {"today": "Today", "week": "This Week", "month": "This Month", "year": "This Year", "last_year": "Last Year"}[period]
        suffix = {"today": "today", "week": "this_week", "month": "this_month", "year": "this_year", "last_year": "last_year"}[period]
        prefix = "rce_api" if tariff == "rce" else tariff
        self._attr_unique_id = f"{entry.entry_id}_{prefix}_net_cost_{suffix}"
        display = {"rce": "RCE (PSE API)", "g12n": "G12n", "g12w": "G12w"}.get(tariff, tariff.upper())
        self._attr_name = f"{display} - Net Cost {label}"

    @property
    def native_value(self):
        return self.coordinator.data[self._key]["value"]

    @property
    def extra_state_attributes(self):
        return self.coordinator.data[self._key]["attributes"]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = EnergyCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    sensors = [ComparisonCostSensor(coordinator, entry, tariff, period) for tariff in TARIFFS for period in PERIODS]
    price = G11PricePlnPerKwhSensor(hass, _get_entry_value(entry, CONF_PRICE_ENTITY, None))
    sensors.append(price)
    for tariff, label in (("g11", "G11"), ("g12", "G12"), ("g12w", "G12w"), ("g12n", "G12n")):
        bands = ("",) if tariff == "g11" else ("day_", "night_")
        for band in bands:
            key = f"{tariff}_{band}rate_pln_per_kwh"
            sensors.append(_RateConfigSensor(entry, unique_suffix=f"{tariff}_{band}rate", name=f"{label} {band.replace('_', ' ')}rate (PLN/kWh)", key=key, default=coordinator.cfg[key]))
    sensors.extend([G12ScheduleSummarySensor(entry), G12wScheduleSummarySensor(entry), G12nScheduleSummarySensor(entry)])
    async_add_entities(sensors)

    @callback
    def update_price(event):
        if price.hass is not None and price.entity_id is not None:
            price.async_write_ha_state()

    if price._source:
        entry.async_on_unload(async_track_state_change_event(hass, [price._source], update_price))
