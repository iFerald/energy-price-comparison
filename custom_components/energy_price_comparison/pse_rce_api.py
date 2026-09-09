from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

_STORAGE_KEY = "energy_price_comparison_rce_cache_v1"
_STORAGE_VERSION = 1

API_URL = "https://api.raporty.pse.pl/api/rce-pln"

@dataclass(slots=True)
class RCEBin:
    start_utc: datetime
    end_utc: datetime
    price_pln_per_kwh: float

def business_date_for_local_dt(local_dt: datetime) -> date:
    """Business date is the local calendar date."""
    return local_dt.date()

class RCEApiClient:
    """Fetches and caches PSE RCE 15-min prices per business_date."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store = Store[dict[str, Any]](hass, _STORAGE_VERSION, _STORAGE_KEY)
        self._cache: dict[str, list[dict[str, Any]]] | None = None

    async def _load(self) -> None:
        if self._cache is not None:
            return
        data = await self._store.async_load() or {}
        self._cache = data.get("days", {})

    async def _save(self) -> None:
        if self._cache is None:
            return
        await self._store.async_save({"days": self._cache})

    async def get_day_bins(self, day: date) -> list[RCEBin]:
        await self._load()
        assert self._cache is not None

        key = day.isoformat()
        if key in self._cache:
            return self._decode_bins(self._cache[key])

        raw = await self._fetch_day(day)
        # Cache even empty (prevents hammering API for missing days)
        self._cache[key] = raw
        await self._save()
        return self._decode_bins(raw)

    async def _fetch_day(self, day: date) -> list[dict[str, Any]]:
        # OData filter (business_date eq 'YYYY-MM-DD')
        url = f"{API_URL}?$filter=business_date%20eq%20'{day.isoformat()}'"
        session = aiohttp.ClientSession()
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                data = await resp.json()
        finally:
            await session.close()

        values = data.get("value", [])
        out: list[dict[str, Any]] = []
        for it in values:
            dtime_utc = it.get("dtime_utc")
            rce_pln = it.get("rce_pln")
            if not dtime_utc or rce_pln is None:
                continue
            # dtime_utc format: YYYY-MM-DD HH:MM:SS
            try:
                end = datetime.strptime(dtime_utc, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except Exception:
                continue
            start = end - timedelta(minutes=15)
            price = float(rce_pln) / 1000.0  # PLN/MWh -> PLN/kWh
            out.append(
                {
                    "s": start.isoformat(),
                    "e": end.isoformat(),
                    "p": price,
                }
            )

        out.sort(key=lambda x: x["s"])
        return out

    def _decode_bins(self, raw: list[dict[str, Any]]) -> list[RCEBin]:
        bins: list[RCEBin] = []
        for it in raw:
            try:
                s = datetime.fromisoformat(it["s"])
                e = datetime.fromisoformat(it["e"])
                p = float(it["p"])
            except Exception:
                continue
            if s.tzinfo is None:
                s = s.replace(tzinfo=timezone.utc)
            if e.tzinfo is None:
                e = e.replace(tzinfo=timezone.utc)
            bins.append(RCEBin(start_utc=s, end_utc=e, price_pln_per_kwh=p))
        bins.sort(key=lambda b: b.start_utc)
        return bins
