import asyncio
import importlib
import sys
import types
import unittest
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

package = types.ModuleType("epc")
package.__path__ = [str(Path(__file__).parents[1] / "custom_components/energy_price_comparison")]
sys.modules.setdefault("epc", package)
# Unit-test storage and HTTP boundaries without starting Home Assistant.
storage = types.ModuleType("homeassistant.helpers.storage")
storage.Store = lambda *args: types.SimpleNamespace(async_load=AsyncMock(return_value={"days": {}}), async_delay_save=lambda *args: None)
http = types.ModuleType("homeassistant.helpers.aiohttp_client")
http.async_get_clientsession = lambda hass: None
with patch.dict(sys.modules, {"homeassistant.helpers.storage": storage, "homeassistant.helpers.aiohttp_client": http}):
    api = importlib.import_module("epc.pse_rce_api")


def day_raw(day):
    start = datetime.combine(day, time(), api.WARSAW).astimezone(timezone.utc)
    end = datetime.combine(day+timedelta(days=1), time(), api.WARSAW).astimezone(timezone.utc)
    raw = []
    while start < end:
        following = start+timedelta(minutes=15)
        raw.append({"s": start.isoformat(), "e": following.isoformat(), "p": 0.5})
        start = following
    return raw


class PSETests(unittest.IsolatedAsyncioTestCase):
    def test_dst_complete_day_is_not_always_96_bins(self):
        for day, expected in [(date(2026, 3, 29), 92), (date(2026, 10, 25), 100)]:
            bins = api.decode_bins(day_raw(day))
            self.assertEqual(len(bins), expected)
            self.assertTrue(api.complete_day(day, bins))
            self.assertFalse(api.complete_day(day, bins[:-1]))

    async def test_old_empty_cache_is_retried_and_persisted(self):
        day = date(2026, 1, 1)
        client = api.RCEApiClient(None)
        client._cache = {day.isoformat(): []}
        client._fetch_day = AsyncMock(return_value=day_raw(day))
        bins = await client.get_day_bins(day)
        self.assertEqual(len(bins), 96)
        self.assertEqual(len(client._cache[day.isoformat()]), 96)
        await client.get_day_bins(day)
        client._fetch_day.assert_awaited_once()

    async def test_failed_refresh_keeps_existing_data_and_backs_off(self):
        day = date(2026, 1, 1)
        client = api.RCEApiClient(None)
        client._cache = {day.isoformat(): day_raw(day)[:2]}
        client._fetch_day = AsyncMock(side_effect=asyncio.TimeoutError())
        self.assertEqual(len(await client.get_day_bins(day)), 2)
        self.assertEqual(len(await client.get_day_bins(day)), 2)
        client._fetch_day.assert_awaited_once()

    async def test_concurrent_requests_fetch_one_day_once(self):
        day = date(2026, 1, 1)
        client = api.RCEApiClient(None)
        client._cache = {}
        client._fetch_day = AsyncMock(return_value=day_raw(day))
        await asyncio.gather(*(client.get_day_bins(day) for _ in range(5)))
        client._fetch_day.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
