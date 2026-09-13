"""One shared recorder snapshot for all tariffs and periods."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.history import get_significant_states
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .calculation import finite_number, fixed_cost, history_intervals, priced_cost, statistics_intervals
from .pse_rce_api import RCEApiClient, WARSAW, complete_day, decode_bins
from .tariffs import rate, settings

_LOGGER = logging.getLogger(__name__)
from .reporting import PERIODS, TARIFFS, reports


class EnergyCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name="Energy price comparison", config_entry=entry, update_interval=timedelta(minutes=5))
        self.cfg = settings(entry)
        self.client = RCEApiClient(hass)

    async def _async_update_data(self):
        now = dt_util.now()
        end = now.astimezone(timezone.utc)
        start = now.replace(year=now.year - 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
        source = self.cfg["total_energy_entity"]
        state = self.hass.states.get(source)
        if state and state.attributes.get("unit_of_measurement") not in ("kWh", "Wh", "MWh"):
            raise UpdateFailed("Energy source must report kWh, Wh or MWh")

        def fetch():
            rows = statistics_during_period(self.hass, start - timedelta(hours=1), end, {source}, "hour", {"energy": "kWh"}, {"sum", "state"}).get(source, [])
            intervals = statistics_intervals(rows)
            tail_start = intervals[-1].end if intervals else max(start, end - timedelta(days=1))
            history = get_significant_states(self.hass, tail_start, end, [source], significant_changes_only=False, minimal_response=False).get(source, [])
            points = []
            for item in history:
                unit = item.attributes.get("unit_of_measurement", "kWh")
                scale = {"kWh": 1, "Wh": 0.001, "MWh": 1000}.get(unit)
                value = finite_number(item.state)
                points.append((dt_util.as_utc(item.last_updated), value * scale if value is not None and scale is not None else None))
            if state:
                scale = {"kWh": 1, "Wh": 0.001, "MWh": 1000}.get(state.attributes.get("unit_of_measurement"))
                value = finite_number(state.state)
                # Extend the last known state to now without replacing earlier points.
                points.append((end, value * scale if value is not None and scale is not None else None))
            intervals.extend(item for raw in history_intervals(points) if (item := raw.clip(tail_start, end)) is not None)
            return intervals

        intervals = await get_instance(self.hass).async_add_executor_job(fetch)
        await self.client._load()
        days = set()
        for item in intervals:
            day = item.start.astimezone(WARSAW).date()
            last = (item.end - timedelta(microseconds=1)).astimezone(WARSAW).date()
            while day <= last:
                days.add(day)
                day += timedelta(days=1)
        cached = {day: decode_bins(self.client._cache.get(day.isoformat(), [])) for day in days}
        needed = [day for day in days if not complete_day(day, cached[day]) or day == now.astimezone(WARSAW).date()]
        # Bound startup network work; continue backfilling without blocking other tariffs.
        never = datetime.min.replace(tzinfo=timezone.utc)
        needed.sort(key=lambda day: (self.client._retry_at.get(day.isoformat(), never), -day.toordinal()))
        eligible = [day for day in needed if self.client._retry_at.get(day.isoformat(), never) <= end]
        batch = eligible[:24]
        if batch:
            tasks = {asyncio.create_task(self.client.get_day_bins(day)): day for day in batch}
            done, pending = await asyncio.wait(tasks, timeout=40)
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                cached[tasks[task]] = task.result()
        self.update_interval = timedelta(seconds=30) if len(eligible) > len(batch) else timedelta(minutes=5)
        bins = sorted((item for values in cached.values() for item in values), key=lambda item: item.start_utc)
        return await self.hass.async_add_executor_job(reports, intervals, bins, self.cfg, now)
