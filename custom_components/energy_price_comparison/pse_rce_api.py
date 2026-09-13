"""PSE prices with persistent successful data and retryable gaps."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .calculation import finite_number

API_URL = "https://api.raporty.pse.pl/api/rce-pln"
WARSAW = ZoneInfo("Europe/Warsaw")
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RCEBin:
    start_utc: datetime
    end_utc: datetime
    price_pln_per_kwh: float


def business_date_for_local_dt(local_dt: datetime) -> date:
    return local_dt.astimezone(WARSAW).date()


def decode_bins(raw: list[dict]) -> list[RCEBin]:
    result = {}
    for item in raw:
        try:
            start, end = datetime.fromisoformat(item["s"]), datetime.fromisoformat(item["e"])
            price = finite_number(item["p"])
        except (KeyError, ValueError, TypeError):
            continue
        if start.tzinfo is None or end.tzinfo is None or price is None or end <= start:
            continue
        start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
        result[start] = RCEBin(start, end, price)
    return sorted(result.values(), key=lambda item: item.start_utc)


def complete_day(day: date, bins: list[RCEBin]) -> bool:
    cursor = datetime.combine(day, time(), WARSAW).astimezone(timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time(), WARSAW).astimezone(timezone.utc)
    for item in bins:
        if item.start_utc != cursor or item.end_utc - item.start_utc != timedelta(minutes=15):
            return False
        cursor = item.end_utc
    return cursor == end


class RCEApiClient:
    def __init__(self, hass):
        self.hass = hass
        # Keep compatibility with the owner's installed 0.0.13 cache.
        self._store = Store(hass, 1, "energy_price_comparison_rce_cache_v1")
        self._cache = None
        self._load_lock = asyncio.Lock()
        self._locks = {}
        self._retry_at = {}
        self._semaphore = asyncio.Semaphore(3)

    async def _load(self):
        async with self._load_lock:
            if self._cache is None:
                data = await self._store.async_load() or {}
                self._cache = data.get("days", {})

    async def get_day_bins(self, day: date) -> list[RCEBin]:
        await self._load()
        key = day.isoformat()
        async with self._locks.setdefault(key, asyncio.Lock()):
            now = datetime.now(timezone.utc)
            existing = decode_bins(self._cache.get(key, []))
            if complete_day(day, existing) and day < now.astimezone(WARSAW).date():
                return existing
            if now < self._retry_at.get(key, datetime.min.replace(tzinfo=timezone.utc)):
                return existing
            self._retry_at[key] = now + timedelta(minutes=15)
            try:
                async with self._semaphore:
                    raw = await self._fetch_day(day)
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, TypeError) as error:
                _LOGGER.warning("PSE prices for %s could not be refreshed: %s", key, error)
                return existing
            # A failed/incomplete refresh must not discard already known prices.
            merged = {item["s"]: item for item in self._cache.get(key, []) if isinstance(item, dict) and "s" in item}
            merged.update({item["s"]: item for item in raw})
            self._cache[key] = list(merged.values())
            self._store.async_delay_save(lambda: {"days": self._cache}, 5)
            return decode_bins(self._cache[key])

    async def _fetch_day(self, day: date) -> list[dict]:
        url = API_URL
        params = {"$filter": f"business_date eq '{day.isoformat()}'", "$first": "1000"}
        result = []
        seen = set()
        for _ in range(10):
            if url in seen:
                raise ValueError("Repeated PSE pagination link")
            seen.add(url)
            async with async_get_clientsession(self.hass).get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response.raise_for_status()
                data = await response.json()
            for item in data.get("value", []):
                if item.get("business_date") != day.isoformat():
                    continue
                try:
                    end = datetime.fromisoformat(item["dtime_utc"]).replace(tzinfo=timezone.utc)
                    price = finite_number(item["rce_pln"])
                except (KeyError, ValueError, TypeError):
                    continue
                if price is None:
                    continue
                result.append({"s": (end - timedelta(minutes=15)).isoformat(), "e": end.isoformat(), "p": price / 1000})
            following = data.get("nextLink") or data.get("@odata.nextLink")
            if not following:
                return result
            parts = urlsplit(following)
            if parts.scheme != "https" or parts.netloc != "api.raporty.pse.pl" or parts.path != "/api/rce-pln":
                raise ValueError("Unexpected PSE pagination destination")
            url, params = following, None
        raise ValueError("Too many PSE result pages")
