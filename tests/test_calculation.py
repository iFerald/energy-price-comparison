import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

path = Path(__file__).parents[1] / "custom_components/energy_price_comparison/calculation.py"
spec = importlib.util.spec_from_file_location("calculation", path)
calc = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = calc
spec.loader.exec_module(calc)
UTC = timezone.utc
START = datetime(2026, 1, 1, tzinfo=UTC)


class CalculationTests(unittest.TestCase):
    def test_numeric_statistics_and_reset_adjusted_sum(self):
        rows = [dict(start=(START + timedelta(hours=i)).timestamp(), sum=value, state=raw)
                for i, (value, raw) in enumerate([(100, 1000), (102, 1002), (105, 3)])]
        intervals = calc.statistics_intervals(rows)
        self.assertEqual([item.kwh for item in intervals], [2, 3])

    def test_no_mixing_state_and_sum_or_bridging_missing_hour(self):
        rows = [dict(start=START, sum=1), dict(start=START + timedelta(hours=1), state=100),
                dict(start=START + timedelta(hours=2), sum=3), dict(start=START + timedelta(hours=4), sum=10)]
        self.assertEqual(calc.statistics_intervals(rows), [])

    def test_year_survives_recorder_purge(self):
        rows = [dict(start=(START + timedelta(hours=i)).timestamp(), sum=i * 2) for i in range(1000)]
        # Historical totals depend solely on durable statistics, not retained raw states.
        before = sum(item.kwh for item in calc.statistics_intervals(rows))
        rows.append(dict(start=(START + timedelta(hours=1000)).timestamp(), sum=2000))
        after = sum(item.kwh for item in calc.statistics_intervals(rows))
        self.assertEqual((before, after), (1998, 2000))

    def test_clip_prorates_energy_at_period_boundary(self):
        interval = calc.EnergyInterval(START, START + timedelta(hours=2), 8)
        clipped = interval.clip(START + timedelta(hours=1), START + timedelta(hours=2))
        self.assertEqual(clipped.kwh, 4)
        price = SimpleNamespace(start_utc=START, end_utc=START + timedelta(hours=2), price_pln_per_kwh=0.5)
        self.assertEqual(calc.priced_cost([clipped], [price])["cost"], 2)

    def test_tariff_switch_splits_interval(self):
        interval = calc.EnergyInterval(START, START + timedelta(hours=1), 4)
        energy, cost = calc.fixed_cost([interval], lambda at: 1 if at.minute < 30 else 2, (0, 30))
        self.assertEqual(energy, 4)
        self.assertAlmostEqual(cost, 6)

    def test_dst_uses_elapsed_hours(self):
        warsaw = ZoneInfo("Europe/Warsaw")
        for month, day, expected in [(3, 29, 23), (10, 25, 25)]:
            local = datetime(2026, month, day, tzinfo=warsaw)
            start, end = local.astimezone(UTC), (local + timedelta(days=1)).astimezone(UTC)
            interval = calc.EnergyInterval(start, end, expected)
            energy, cost = calc.fixed_cost([interval], lambda at: 1, (0,))
            self.assertEqual(energy, expected)
            self.assertAlmostEqual(cost, expected)

    def test_missing_partial_price_and_duplicate_bin(self):
        interval = calc.EnergyInterval(START, START + timedelta(hours=1), 4)
        price = SimpleNamespace(start_utc=START, end_utc=START + timedelta(minutes=15), price_pln_per_kwh=2)
        result = calc.priced_cost([interval], [price, price])
        self.assertEqual(result["priced_kwh"], 1)
        self.assertEqual(result["missing_price_kwh"], 3)
        self.assertEqual(result["covered_seconds"], 900)
        self.assertEqual(result["cost"], 2)

    def test_negative_rce_is_not_clamped(self):
        interval = calc.EnergyInterval(START, START + timedelta(hours=1), 4)
        price = SimpleNamespace(start_utc=START, end_utc=interval.end, price_pln_per_kwh=-0.5)
        self.assertEqual(calc.priced_cost([interval], [price])["cost"], -2)

    def test_invalid_state_breaks_tail_coverage(self):
        points = [(START, 100), (START + timedelta(minutes=1), None),
                  (START + timedelta(minutes=2), 200), (START + timedelta(minutes=3), 201)]
        self.assertEqual(sum(item.kwh for item in calc.history_intervals(points)), 1)
        for invalid in ["nan", "inf", "-inf", "unavailable", None]:
            self.assertIsNone(calc.finite_number(invalid))

    def test_zero_glitch_does_not_charge_meter_lifetime_again(self):
        points = [(START + timedelta(minutes=i), value) for i, value in enumerate([100, 0, 100, 101])]
        self.assertEqual(sum(item.kwh for item in calc.history_intervals(points)), 1)


if __name__ == "__main__":
    unittest.main()
