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

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.components.recorder.statistics import statistics_during_period

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


def _is_summer(local_dt: datetime) -> bool:
    dst = local_dt.dst()
    return bool(dst and dst != timedelta(0))


def _is_day_tariff_g12(local_dt: datetime, cfg: dict[str, str]) -> bool:
    summer = _is_summer(local_dt)

    day1 = cfg["day_range_1_start"]
    day2 = cfg["day_range_2_summer_start"] if summer else cfg["day_range_2_winter_start"]
    night1 = cfg["night_range_1_summer_start"] if summer else cfg["night_range_1_winter_start"]
    night2 = cfg["night_range_2_start"]

    hm = local_dt.strftime("%H:%M")
    return (day1 <= hm < night1) or (day2 <= hm < night2)


def _is_day_tariff_g12w(local_dt: datetime, cfg: dict[str, str]) -> bool:
    if local_dt.weekday() >= 5:  # Sat/Sun
        return False
    return _is_day_tariff_g12(local_dt, cfg)


def _is_day_tariff_g12n(local_dt: datetime, cfg: dict[str, str]) -> bool:
    if local_dt.weekday() == 6:  # Sunday
        return False
    day_start = cfg["day_start"]
    night_start = cfg["night_start"]
    hm = local_dt.strftime("%H:%M")
    return (hm >= day_start) or (hm < night_start)


def _period_range_local(now_local: datetime, period: str) -> tuple[datetime, datetime]:
    start_of_today = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_year = start_of_today.replace(month=1, day=1)

    if period == "week":
        start = start_of_today - timedelta(days=start_of_today.weekday())  # Monday
        return start, now_local
    if period == "month":
        start = start_of_today.replace(day=1)
        return start, now_local
    if period == "year":
        return start_of_year, now_local
    if period == "last_year":
        start_last_year = start_of_year.replace(year=start_of_year.year - 1)
        return start_last_year, start_of_year

    raise ValueError(f"unknown period: {period}")


async def _fetch_history_states(
    hass: HomeAssistant,
    entity_id: str,
    start_utc: datetime,
    end_utc: datetime,
) -> list[tuple[datetime, float]]:
    if hass is None:
        return []

    def _job():
        return get_significant_states(
            hass=hass,
            start_time=start_utc,
            end_time=end_utc,
            entity_ids=[entity_id],
            significant_changes_only=False,
            minimal_response=False,
        )

    data = await get_instance(hass).async_add_executor_job(_job)
    states = data.get(entity_id, [])
    points: list[tuple[datetime, float]] = []

    for st in states:
        v = _as_float(st.state)
        if v is None:
            continue
        ts = st.last_updated or st.last_changed
        if ts is None:
            continue
        points.append((dt_util.as_utc(ts), v))

    points.sort(key=lambda x: x[0])
    return points


async def _fetch_lts_hourly_totals(
    hass: HomeAssistant,
    statistic_id: str,
    start_utc: datetime,
    end_utc: datetime,
) -> list[tuple[datetime, float]]:
    if hass is None:
        return []

    def _job():
        return statistics_during_period(
            hass=hass,
            start_time=start_utc,
            end_time=end_utc,
            statistic_ids={statistic_id},
            period="hour",
            types={"sum", "state"},
            units=None,
        )

    stats = await get_instance(hass).async_add_executor_job(_job)
    rows = stats.get(statistic_id) or []
    out: list[tuple[datetime, float]] = []

    for r in rows:
        start_ts = r.get("start")
        if not isinstance(start_ts, datetime):
            continue
        end_ts = dt_util.as_utc(start_ts + timedelta(hours=1))

        v = r.get("sum")
        if v is None:
            v = r.get("state")
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        out.append((end_ts, fv))

    out.sort(key=lambda x: x[0])
    return out


def _sum_deltas_by_tariff(
    points: list[tuple[datetime, float]],
    tz,
    is_day_fn: Callable[[datetime], bool],
) -> tuple[float, float]:
    if len(points) < 2:
        return 0.0, 0.0

    day = 0.0
    night = 0.0
    prev_v = points[0][1]

    for ts_utc, v in points[1:]:
        d = v - prev_v
        if d >= 0:
            local_end = dt_util.as_local(ts_utc).astimezone(tz)
            if is_day_fn(local_end):
                day += d
            else:
                night += d
        prev_v = v

    return day, night


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


class G11CostTodayFromTotalSensor(SensorEntity):
    _attr_name = "G11 - Net Cost Today"
    _attr_native_unit_of_measurement = "PLN"
    _attr_icon = "mdi:cash-sync"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry_id: str, total_entity_id: str, g11_rate_pln_per_kwh: float) -> None:
        self.hass = hass
        self._total = total_entity_id
        self._rate = g11_rate_pln_per_kwh
        self._attr_unique_id = f"{entry_id}_g11_net_cost_today"
        self._value: float | None = None
        self._attrs: dict[str, Any] = {}

    @property
    def native_value(self) -> float | None:
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attrs

    async def async_update(self) -> None:
        now_local = dt_util.now()
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = dt_util.as_utc(start_local)
        end_utc = dt_util.as_utc(now_local)

        points = await _fetch_history_states(self.hass, self._total, start_utc, end_utc)

        st_now = self.hass.states.get(self._total)
        live_now = _as_float(st_now.state) if st_now else None
        now_source = "live_state"
        if live_now is not None and points:
            points = points[:-1] + [(end_utc, live_now)]
        elif live_now is None:
            now_source = "recorder_last_point"

        if len(points) < 2:
            self._value = None
            self._attrs = {
                "total_energy_entity": self._total,
                "rate_pln_per_kwh": self._rate,
                "start_local": start_local.isoformat(),
                "reason": "not_enough_points",
                "points": len(points),
            }
            return

        baseline = points[0][1]
        now = points[-1][1]
        delta = now - baseline
        if delta < 0:
            self._value = None
            self._attrs = {
                "total_energy_entity": self._total,
                "rate_pln_per_kwh": self._rate,
                "start_local": start_local.isoformat(),
                "reason": "negative_delta",
                "points": len(points),
            }
            return

        self._value = round(delta * self._rate, 4)
        self._attrs = {
            "total_energy_entity": self._total,
            "rate_pln_per_kwh": self._rate,
            "formula": "cost_today = (total_now - total_at_midnight) * rate",
            "start_local": start_local.isoformat(),
            "baseline_total_kwh": round(baseline, 4),
            "now_total_kwh": round(now, 4),
            "kwh_today": round(delta, 4),
            "now_source": now_source,
            "resolution": "history",
            "points": len(points),
        }


class _TariffCostTodayFromTotalSensor(SensorEntity):
    _attr_native_unit_of_measurement = "PLN"
    _attr_icon = "mdi:cash-clock"
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        entry_id: str,
        total_entity_id: str,
        name: str,
        unique_suffix: str,
        day_rate: float,
        night_rate: float,
        time_ranges_attr: dict[str, Any],
        season_rule: str,
        is_day_fn: Callable[[datetime], bool],
    ) -> None:
        self.hass = hass
        self._total = total_entity_id
        self._day_rate = day_rate
        self._night_rate = night_rate
        self._ranges_attr = time_ranges_attr
        self._season_rule = season_rule
        self._is_day_fn = is_day_fn

        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{unique_suffix}"
        self._value: float | None = None
        self._attrs: dict[str, Any] = {}

    @property
    def native_value(self) -> float | None:
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attrs

    async def async_update(self) -> None:
        now_local = dt_util.now()
        tz = dt_util.DEFAULT_TIME_ZONE
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

        start_utc = dt_util.as_utc(start_local)
        end_utc = dt_util.as_utc(now_local)

        resolution = "history"
        points = await _fetch_history_states(self.hass, self._total, start_utc, end_utc)
        if len(points) < 2:
            resolution = "long_term_statistics"
            points = await _fetch_lts_hourly_totals(self.hass, self._total, start_utc, end_utc)

        if len(points) < 2:
            self._value = None
            self._attrs = {
                "total_energy_entity": self._total,
                "start_local": start_local.isoformat(),
                "resolution": resolution,
                "reason": "not_enough_points",
                "points": len(points),
            }
            return

        if resolution == "history":
            st_now = self.hass.states.get(self._total)
            live_now = _as_float(st_now.state) if st_now else None
            if live_now is not None:
                points = points[:-1] + [(end_utc, live_now)]

        day_kwh, night_kwh = _sum_deltas_by_tariff(points, tz, self._is_day_fn)
        cost = day_kwh * self._day_rate + night_kwh * self._night_rate

        self._value = round(cost, 4)
        self._attrs = {
            "total_energy_entity": self._total,
            "start_local": start_local.isoformat(),
            "resolution": resolution,
            "day_kwh": round(day_kwh, 4),
            "night_kwh": round(night_kwh, 4),
            "day_rate_pln_per_kwh": self._day_rate,
            "night_rate_pln_per_kwh": self._night_rate,
            "time_ranges": self._ranges_attr,
            "formula": "cost = day_kwh*day_rate + night_kwh*night_rate",
            "season_rule": self._season_rule,
            "points": len(points),
        }


class _TariffPeriodCostFromTotalSensor(SensorEntity):
    _attr_native_unit_of_measurement = "PLN"
    _attr_icon = "mdi:cash-clock"
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        entry_id: str,
        total_entity_id: str,
        period: str,
        name: str,
        unique_suffix: str,
        day_rate: float,
        night_rate: float,
        time_ranges_attr: dict[str, Any],
        season_rule: str,
        is_day_fn: Callable[[datetime], bool],
    ) -> None:
        self.hass = hass
        self._total = total_entity_id
        self._period = period
        self._day_rate = day_rate
        self._night_rate = night_rate
        self._ranges_attr = time_ranges_attr
        self._season_rule = season_rule
        self._is_day_fn = is_day_fn

        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{unique_suffix}"
        self._value: float | None = None
        self._attrs: dict[str, Any] = {}

    @property
    def native_value(self) -> float | None:
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attrs

    async def async_update(self) -> None:
        now_local = dt_util.now()
        tz = dt_util.DEFAULT_TIME_ZONE
        start_local, end_local = _period_range_local(now_local, self._period)

        start_utc = dt_util.as_utc(start_local)
        end_utc = dt_util.as_utc(end_local)

        resolution = "history"
        points = await _fetch_history_states(self.hass, self._total, start_utc, end_utc)
        if len(points) < 2:
            resolution = "long_term_statistics"
            points = await _fetch_lts_hourly_totals(self.hass, self._total, start_utc, end_utc)

        if len(points) < 2:
            self._value = None
            self._attrs = {
                "total_energy_entity": self._total,
                "period": self._period,
                "start_local": start_local.isoformat(),
                "end_local": end_local.isoformat(),
                "resolution": resolution,
                "reason": "not_enough_points",
                "points": len(points),
            }
            return

        day_kwh, night_kwh = _sum_deltas_by_tariff(points, tz, self._is_day_fn)
        cost = day_kwh * self._day_rate + night_kwh * self._night_rate

        self._value = round(cost, 4)
        self._attrs = {
            "total_energy_entity": self._total,
            "period": self._period,
            "start_local": start_local.isoformat(),
            "end_local": end_local.isoformat(),
            "resolution": resolution,
            "day_kwh": round(day_kwh, 4),
            "night_kwh": round(night_kwh, 4),
            "day_rate_pln_per_kwh": self._day_rate,
            "night_rate_pln_per_kwh": self._night_rate,
            "time_ranges": self._ranges_attr,
            "formula": "cost = day_kwh*day_rate + night_kwh*night_rate",
            "season_rule": self._season_rule,
            "points": len(points),
            "week_start": "monday" if self._period == "week" else None,
        }


class G11PeriodCostFromTotalSensor(SensorEntity):
    _attr_native_unit_of_measurement = "PLN"
    _attr_icon = "mdi:cash-clock"
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        entry_id: str,
        total_entity_id: str,
        g11_rate_pln_per_kwh: float,
        period: str,
        name: str,
        unique_suffix: str,
    ) -> None:
        self.hass = hass
        self._total = total_entity_id
        self._rate = g11_rate_pln_per_kwh
        self._period = period
        self._attr_name = name
        self._attr_unique_id = f"{entry_id}_{unique_suffix}"

        self._value: float | None = None
        self._attrs: dict[str, Any] = {}

    @property
    def native_value(self) -> float | None:
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attrs

    async def async_update(self) -> None:
        now_local = dt_util.now()
        start_local, end_local = _period_range_local(now_local, self._period)

        start_utc = dt_util.as_utc(start_local)
        end_utc = dt_util.as_utc(end_local)

        resolution = "history"
        points = await _fetch_history_states(self.hass, self._total, start_utc, end_utc)
        if len(points) < 2:
            resolution = "long_term_statistics"
            points = await _fetch_lts_hourly_totals(self.hass, self._total, start_utc, end_utc)

        if len(points) < 2:
            self._value = None
            self._attrs = {
                "total_energy_entity": self._total,
                "period": self._period,
                "rate_pln_per_kwh": self._rate,
                "start_local": start_local.isoformat(),
                "end_local": end_local.isoformat(),
                "resolution": resolution,
                "reason": "not_enough_points",
                "points": len(points),
            }
            return

        baseline = points[0][1]
        now = points[-1][1]
        delta = now - baseline
        if delta < 0:
            self._value = None
            self._attrs = {
                "total_energy_entity": self._total,
                "period": self._period,
                "rate_pln_per_kwh": self._rate,
                "start_local": start_local.isoformat(),
                "end_local": end_local.isoformat(),
                "resolution": resolution,
                "reason": "negative_delta",
                "points": len(points),
            }
            return

        self._value = round(delta * self._rate, 4)
        self._attrs = {
            "total_energy_entity": self._total,
            "period": self._period,
            "rate_pln_per_kwh": self._rate,
            "formula": "cost_period = (total_end - total_start) * rate",
            "start_local": start_local.isoformat(),
            "end_local": end_local.isoformat(),
            "baseline_total_kwh": round(baseline, 4),
            "end_total_kwh": round(now, 4),
            "kwh": round(delta, 4),
            "resolution": resolution,
            "points": len(points),
            "week_start": "monday" if self._period == "week" else None,
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    price_entity = _get_entry_value(entry, CONF_PRICE_ENTITY, None)
    total_energy_entity = _get_entry_value(entry, CONF_TOTAL_ENERGY_ENTITY, DEFAULT_TOTAL_ENERGY_ENTITY)

    g11_rate = float(_get_entry_value(entry, CONF_G11_RATE, DEFAULT_G11_RATE))

    g12_day_rate = float(_get_entry_value(entry, CONF_G12_DAY_RATE, DEFAULT_G12_DAY_RATE))
    g12_night_rate = float(_get_entry_value(entry, CONF_G12_NIGHT_RATE, DEFAULT_G12_NIGHT_RATE))
    g12w_day_rate = float(_get_entry_value(entry, CONF_G12W_DAY_RATE, DEFAULT_G12W_DAY_RATE))
    g12w_night_rate = float(_get_entry_value(entry, CONF_G12W_NIGHT_RATE, DEFAULT_G12W_NIGHT_RATE))
    g12n_day_rate = float(_get_entry_value(entry, CONF_G12N_DAY_RATE, DEFAULT_G12N_DAY_RATE))
    g12n_night_rate = float(_get_entry_value(entry, CONF_G12N_NIGHT_RATE, DEFAULT_G12N_NIGHT_RATE))

    g12_cfg = {
        "day_range_1_start": _get_entry_value(entry, CONF_G12_DAY_RANGE_1_START, DEFAULT_G12_DAY_RANGE_1_START),
        "day_range_2_summer_start": _get_entry_value(entry, CONF_G12_DAY_RANGE_2_SUMMER_START, DEFAULT_G12_DAY_RANGE_2_SUMMER_START),
        "day_range_2_winter_start": _get_entry_value(entry, CONF_G12_DAY_RANGE_2_WINTER_START, DEFAULT_G12_DAY_RANGE_2_WINTER_START),
        "night_range_1_summer_start": _get_entry_value(entry, CONF_G12_NIGHT_RANGE_1_SUMMER_START, DEFAULT_G12_NIGHT_RANGE_1_SUMMER_START),
        "night_range_1_winter_start": _get_entry_value(entry, CONF_G12_NIGHT_RANGE_1_WINTER_START, DEFAULT_G12_NIGHT_RANGE_1_WINTER_START),
        "night_range_2_start": _get_entry_value(entry, CONF_G12_NIGHT_RANGE_2_START, DEFAULT_G12_NIGHT_RANGE_2_START),
    }
    g12w_cfg = {
        "day_range_1_start": _get_entry_value(entry, CONF_G12W_DAY_RANGE_1_START, DEFAULT_G12W_DAY_RANGE_1_START),
        "day_range_2_summer_start": _get_entry_value(entry, CONF_G12W_DAY_RANGE_2_SUMMER_START, DEFAULT_G12W_DAY_RANGE_2_SUMMER_START),
        "day_range_2_winter_start": _get_entry_value(entry, CONF_G12W_DAY_RANGE_2_WINTER_START, DEFAULT_G12W_DAY_RANGE_2_WINTER_START),
        "night_range_1_summer_start": _get_entry_value(entry, CONF_G12W_NIGHT_RANGE_1_SUMMER_START, DEFAULT_G12W_NIGHT_RANGE_1_SUMMER_START),
        "night_range_1_winter_start": _get_entry_value(entry, CONF_G12W_NIGHT_RANGE_1_WINTER_START, DEFAULT_G12W_NIGHT_RANGE_1_WINTER_START),
        "night_range_2_start": _get_entry_value(entry, CONF_G12W_NIGHT_RANGE_2_START, DEFAULT_G12W_NIGHT_RANGE_2_START),
        "weekend_rule": "sat_sun_always_night",
    }
    g12n_cfg = {
        "day_start": _get_entry_value(entry, CONF_G12N_DAY_START, DEFAULT_G12N_DAY_START),
        "night_start": _get_entry_value(entry, CONF_G12N_NIGHT_START, DEFAULT_G12N_NIGHT_START),
        "sunday_rule": "always_night",
    }

    # Today sensors
    g11_today = G11CostTodayFromTotalSensor(hass, entry.entry_id, total_energy_entity, g11_rate)
    g12_today = _TariffCostTodayFromTotalSensor(
        hass,
        entry_id=entry.entry_id,
        total_entity_id=total_energy_entity,
        name="G12 - Net Cost Today",
        unique_suffix="g12_net_cost_today",
        day_rate=g12_day_rate,
        night_rate=g12_night_rate,
        time_ranges_attr=g12_cfg,
        season_rule="summer if DST else winter",
        is_day_fn=lambda dt: _is_day_tariff_g12(dt, g12_cfg),
    )
    g12w_today = _TariffCostTodayFromTotalSensor(
        hass,
        entry_id=entry.entry_id,
        total_entity_id=total_energy_entity,
        name="G12w - Net Cost Today",
        unique_suffix="g12w_net_cost_today",
        day_rate=g12w_day_rate,
        night_rate=g12w_night_rate,
        time_ranges_attr=g12w_cfg,
        season_rule="summer if DST else winter",
        is_day_fn=lambda dt: _is_day_tariff_g12w(dt, g12w_cfg),
    )
    g12n_today = _TariffCostTodayFromTotalSensor(
        hass,
        entry_id=entry.entry_id,
        total_entity_id=total_energy_entity,
        name="G12n - Net Cost Today",
        unique_suffix="g12n_net_cost_today",
        day_rate=g12n_day_rate,
        night_rate=g12n_night_rate,
        time_ranges_attr=g12n_cfg,
        season_rule="fixed (weekday rules; no DST)",
        is_day_fn=lambda dt: _is_day_tariff_g12n(dt, g12n_cfg),
    )

    # G11 periods
    g11_week = G11PeriodCostFromTotalSensor(
        hass,
        entry_id=entry.entry_id,
        total_entity_id=total_energy_entity,
        g11_rate_pln_per_kwh=g11_rate,
        period="week",
        name="G11 - Net Cost This Week",
        unique_suffix="g11_net_cost_this_week",
    )
    g11_month = G11PeriodCostFromTotalSensor(
        hass,
        entry_id=entry.entry_id,
        total_entity_id=total_energy_entity,
        g11_rate_pln_per_kwh=g11_rate,
        period="month",
        name="G11 - Net Cost This Month",
        unique_suffix="g11_net_cost_this_month",
    )
    g11_year = G11PeriodCostFromTotalSensor(
        hass,
        entry_id=entry.entry_id,
        total_entity_id=total_energy_entity,
        g11_rate_pln_per_kwh=g11_rate,
        period="year",
        name="G11 - Net Cost This Year",
        unique_suffix="g11_net_cost_this_year",
    )
    g11_last_year = G11PeriodCostFromTotalSensor(
        hass,
        entry_id=entry.entry_id,
        total_entity_id=total_energy_entity,
        g11_rate_pln_per_kwh=g11_rate,
        period="last_year",
        name="G11 - Net Cost Last Year",
        unique_suffix="g11_net_cost_last_year",
    )

    def _mk_periods(prefix: str, day_rate: float, night_rate: float, cfg: dict[str, Any], season_rule: str, is_day_fn: Callable[[datetime], bool]):
        return (
            _TariffPeriodCostFromTotalSensor(
                hass,
                entry_id=entry.entry_id,
                total_entity_id=total_energy_entity,
                period="week",
                name=f"{prefix} - Net Cost This Week",
                unique_suffix=f"{prefix.lower()}_net_cost_this_week",
                day_rate=day_rate,
                night_rate=night_rate,
                time_ranges_attr=cfg,
                season_rule=season_rule,
                is_day_fn=is_day_fn,
            ),
            _TariffPeriodCostFromTotalSensor(
                hass,
                entry_id=entry.entry_id,
                total_entity_id=total_energy_entity,
                period="month",
                name=f"{prefix} - Net Cost This Month",
                unique_suffix=f"{prefix.lower()}_net_cost_this_month",
                day_rate=day_rate,
                night_rate=night_rate,
                time_ranges_attr=cfg,
                season_rule=season_rule,
                is_day_fn=is_day_fn,
            ),
            _TariffPeriodCostFromTotalSensor(
                hass,
                entry_id=entry.entry_id,
                total_entity_id=total_energy_entity,
                period="year",
                name=f"{prefix} - Net Cost This Year",
                unique_suffix=f"{prefix.lower()}_net_cost_this_year",
                day_rate=day_rate,
                night_rate=night_rate,
                time_ranges_attr=cfg,
                season_rule=season_rule,
                is_day_fn=is_day_fn,
            ),
            _TariffPeriodCostFromTotalSensor(
                hass,
                entry_id=entry.entry_id,
                total_entity_id=total_energy_entity,
                period="last_year",
                name=f"{prefix} - Net Cost Last Year",
                unique_suffix=f"{prefix.lower()}_net_cost_last_year",
                day_rate=day_rate,
                night_rate=night_rate,
                time_ranges_attr=cfg,
                season_rule=season_rule,
                is_day_fn=is_day_fn,
            ),
        )

    g12_week, g12_month, g12_year, g12_last_year = _mk_periods(
        "G12",
        g12_day_rate,
        g12_night_rate,
        g12_cfg,
        "summer if DST else winter",
        lambda dt: _is_day_tariff_g12(dt, g12_cfg),
    )
    g12w_week, g12w_month, g12w_year, g12w_last_year = _mk_periods(
        "G12w",
        g12w_day_rate,
        g12w_night_rate,
        g12w_cfg,
        "summer if DST else winter",
        lambda dt: _is_day_tariff_g12w(dt, g12w_cfg),
    )
    g12n_week, g12n_month, g12n_year, g12n_last_year = _mk_periods(
        "G12n",
        g12n_day_rate,
        g12n_night_rate,
        g12n_cfg,
        "fixed (weekday rules; no DST)",
        lambda dt: _is_day_tariff_g12n(dt, g12n_cfg),
    )

    # Config sensors
    sensors: list[SensorEntity] = [
        G11PricePlnPerKwhSensor(hass, price_entity),
        g11_today,
        g12_today,
        g12w_today,
        g12n_today,
        g11_week, g11_month, g11_year, g11_last_year,
        g12_week, g12_month, g12_year, g12_last_year,
        g12w_week, g12w_month, g12w_year, g12w_last_year,
        g12n_week, g12n_month, g12n_year, g12n_last_year,
        _RateConfigSensor(entry, unique_suffix="g11_rate", name="G11 rate (PLN/kWh)", key=CONF_G11_RATE, default=DEFAULT_G11_RATE),
        _RateConfigSensor(entry, unique_suffix="g12_day_rate", name="G12 day rate (PLN/kWh)", key=CONF_G12_DAY_RATE, default=DEFAULT_G12_DAY_RATE),
        _RateConfigSensor(entry, unique_suffix="g12_night_rate", name="G12 night rate (PLN/kWh)", key=CONF_G12_NIGHT_RATE, default=DEFAULT_G12_NIGHT_RATE),
        _RateConfigSensor(entry, unique_suffix="g12w_day_rate", name="G12w day rate (PLN/kWh)", key=CONF_G12W_DAY_RATE, default=DEFAULT_G12W_DAY_RATE),
        _RateConfigSensor(entry, unique_suffix="g12w_night_rate", name="G12w night rate (PLN/kWh)", key=CONF_G12W_NIGHT_RATE, default=DEFAULT_G12W_NIGHT_RATE),
        _RateConfigSensor(entry, unique_suffix="g12n_day_rate", name="G12n day rate (PLN/kWh)", key=CONF_G12N_DAY_RATE, default=DEFAULT_G12N_DAY_RATE),
        _RateConfigSensor(entry, unique_suffix="g12n_night_rate", name="G12n night rate (PLN/kWh)", key=CONF_G12N_NIGHT_RATE, default=DEFAULT_G12N_NIGHT_RATE),
        G12ScheduleSummarySensor(entry),
        G12wScheduleSummarySensor(entry),
        G12nScheduleSummarySensor(entry),
    ]

    async_add_entities(sensors, update_before_add=True)

    @callback
    def _handle_source_change(event: Any) -> None:
        entity_id = event.data.get("entity_id")

        for s in sensors:
            if s.hass is None:
                continue

            if isinstance(s, (G11CostTodayFromTotalSensor, _TariffCostTodayFromTotalSensor)) and entity_id == total_energy_entity:
                hass.async_create_task(s.async_update_ha_state(True))
                continue

            if isinstance(s, G11PricePlnPerKwhSensor) and entity_id == price_entity:
                hass.async_create_task(s.async_update_ha_state(True))
                continue

    async_track_state_change_event(hass, [price_entity, total_energy_entity], _handle_source_change)

    async def _tick_today(_now: datetime) -> None:
        for s in (g11_today, g12_today, g12w_today, g12n_today):
            if s.hass is None:
                continue
            hass.async_create_task(s.async_update_ha_state(True))

    async_track_time_interval(hass, _tick_today, timedelta(minutes=2))

    async def _tick_periods(_now: datetime) -> None:
        for s in (
            g11_week, g11_month, g11_year, g11_last_year,
            g12_week, g12_month, g12_year, g12_last_year,
            g12w_week, g12w_month, g12w_year, g12w_last_year,
            g12n_week, g12n_month, g12n_year, g12n_last_year,
        ):
            if s.hass is None:
                continue
            hass.async_create_task(s.async_update_ha_state(True))

    async_track_time_interval(hass, _tick_periods, timedelta(minutes=15))
