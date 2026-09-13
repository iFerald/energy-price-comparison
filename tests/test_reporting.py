import importlib
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

package = types.ModuleType("epc")
package.__path__ = [str(Path(__file__).parents[1] / "custom_components/energy_price_comparison")]
sys.modules.setdefault("epc", package)
calc = importlib.import_module("epc.calculation")
tariffs = importlib.import_module("epc.tariffs")
reporting = importlib.import_module("epc.reporting")
UTC = timezone.utc
WARSAW = ZoneInfo("Europe/Warsaw")


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.cfg = tariffs.settings(types.SimpleNamespace(options={}, data={}))

    def test_calendar_boundaries_and_last_year(self):
        now = datetime(2026, 9, 13, 12, tzinfo=WARSAW)
        self.assertEqual(reporting.period_bounds(now, "week")[0].day, 7)
        self.assertEqual(reporting.period_bounds(now, "month")[0].day, 1)
        self.assertEqual(reporting.period_bounds(now, "last_year")[0].year, 2025)
        self.assertEqual(reporting.period_bounds(now, "year")[0].utcoffset(), timedelta(hours=1))

    def test_all_tariffs_use_same_energy_and_chart_matches_total(self):
        local = datetime(2026, 9, 13, tzinfo=WARSAW)
        start = local.astimezone(UTC)
        intervals = [calc.EnergyInterval(start + timedelta(hours=i), start + timedelta(hours=i+1), 1) for i in range(12)]
        bins = [types.SimpleNamespace(start_utc=start, end_utc=start+timedelta(hours=12), price_pln_per_kwh=0.5)]
        reports = reporting.reports(intervals, bins, self.cfg, local+timedelta(hours=12))
        for tariff in reporting.TARIFFS:
            report = reports[tariff, "today"]
            self.assertEqual(report["attributes"]["kwh"], 12)
            self.assertEqual(report["attributes"]["coverage_status"], "complete")
            self.assertEqual(report["attributes"]["cumulative_cost_chart"][-1][1], report["value"])
        self.assertEqual(reports["g11", "today"]["value"], round(12 * self.cfg["g11_rate_pln_per_kwh"], 4))
        self.assertLess(reports["g11", "year"]["attributes"]["energy_coverage_ratio"], 0.01)

    def test_price_gap_cannot_report_complete(self):
        now = datetime(2026, 1, 1, 2, tzinfo=WARSAW)
        start = now.replace(hour=0).astimezone(UTC)
        intervals = [calc.EnergyInterval(start, start+timedelta(hours=2), 2)]
        bins = [types.SimpleNamespace(start_utc=start, end_utc=start+timedelta(hours=1), price_pln_per_kwh=1)]
        report = reporting.reports(intervals, bins, self.cfg, now)["rce", "today"]
        self.assertEqual(report["attributes"]["coverage_status"], "partial")
        self.assertEqual(report["attributes"]["missing_price_kwh"], 1)
        self.assertEqual(report["attributes"]["coverage_ratio_time"], 0.5)

    def test_no_data_is_not_zero_cost(self):
        reports = reporting.reports([], [], self.cfg, datetime(2026, 9, 13, 12, tzinfo=WARSAW))
        self.assertTrue(all(report["value"] is None for report in reports.values()))

    def test_configured_day_night_and_weekends(self):
        monday = datetime(2026, 9, 7, 12, tzinfo=WARSAW)
        self.assertTrue(tariffs.is_day(monday, "g12", self.cfg))
        self.assertFalse(tariffs.is_day(monday.replace(hour=16), "g12", self.cfg))
        self.assertFalse(tariffs.is_day(monday+timedelta(days=5), "g12w", self.cfg))
        self.assertFalse(tariffs.is_day(monday+timedelta(days=6), "g12n", self.cfg))
        self.cfg.update(g12n_day_start="06:00", g12n_night_start="22:00")
        self.assertFalse(tariffs.is_day(monday.replace(hour=23), "g12n", self.cfg))


if __name__ == "__main__":
    unittest.main()
