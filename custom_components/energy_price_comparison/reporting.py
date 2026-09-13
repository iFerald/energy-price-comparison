"""Calendar comparisons, independent of Home Assistant I/O."""
from datetime import timedelta, timezone
from .calculation import fixed_cost, priced_cost
from .tariffs import rate

PERIODS = ("today", "week", "month", "year", "last_year")
TARIFFS = ("g11", "g12", "g12n", "g12w", "rce")


def period_bounds(now, period):
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "today":
        return today, now
    if period == "week":
        return today - timedelta(days=today.weekday()), now
    if period == "month":
        return today.replace(day=1), now
    year = today.replace(month=1, day=1)
    if period == "year":
        return year, now
    return year.replace(year=year.year - 1), year


def reports(intervals, bins, cfg, now):
    result = {}
    minutes = tuple(sorted({0} | {int(value.split(":")[1]) for key, value in cfg.items() if key.endswith("_start")}))
    for period in PERIODS:
        local_start, local_end = period_bounds(now, period)
        start, end = local_start.astimezone(timezone.utc), local_end.astimezone(timezone.utc)
        selected = [clipped for item in intervals if (clipped := item.clip(start, end)) is not None]
        covered = sum((item.end - item.start).total_seconds() for item in selected)
        requested = (end - start).total_seconds()
        coverage = min(1.0, covered / requested) if requested else 0.0
        energy = sum(item.kwh for item in selected)
        buckets = []
        cursor = local_start
        while cursor < local_end:
            if period == "today":
                following = (cursor.astimezone(timezone.utc) + timedelta(hours=1)).astimezone(now.tzinfo)
            elif period in ("year", "last_year"):
                following = cursor.replace(year=cursor.year + 1, month=1) if cursor.month == 12 else cursor.replace(month=cursor.month + 1)
            else:
                following = cursor + timedelta(days=1)
            boundary = min(following.astimezone(timezone.utc), end)
            bucket_start = cursor.astimezone(timezone.utc)
            bucket_items = [clipped for item in selected if (clipped := item.clip(bucket_start, boundary)) is not None]
            buckets.append((boundary, bucket_items))
            cursor = following
        common = {
            "period": period, "period_start_local": local_start.isoformat(), "period_end_local": local_end.isoformat(),
            "total_energy_entity": cfg["total_energy_entity"], "kwh": round(energy, 6),
            "energy_coverage_ratio": round(coverage, 6),
            "coverage_start_local": selected[0].start.astimezone(now.tzinfo).isoformat() if selected else None,
            "coverage_end_local": selected[-1].end.astimezone(now.tzinfo).isoformat() if selected else None,
            "resolution_energy": "long_term_hourly_statistics_with_recorder_tail",
            "allocation": "uniform energy within each measured interval",
            "cost_scope": "net energy only; excludes distribution, VAT and supplier fees",
            "intervals": len(selected),
        }
        for tariff in TARIFFS:
            attrs = dict(common)
            if tariff == "rce":
                priced = priced_cost(selected, bins)
                value = priced["cost"] if selected and priced["covered_seconds"] > 0 else None
                attrs.update({"priced_kwh": round(priced["priced_kwh"], 6), "missing_price_kwh": round(priced["missing_price_kwh"], 6),
                              "coverage_ratio_time": round(priced["covered_seconds"] / requested, 6) if requested else 0,
                              "price_source": "PSE RCE, PLN/MWh converted to PLN/kWh"})
                complete = coverage >= 0.999999 and priced["covered_seconds"] >= covered - 1
            else:
                _, value = fixed_cost(selected, lambda at: rate(at.astimezone(now.tzinfo), tariff, cfg), minutes)
                if not selected:
                    value = None
                complete = coverage >= 0.999999
            attrs["coverage_status"] = "complete" if complete else "partial" if value is not None else "no_data"
            running = 0.0
            chart = []
            for boundary, items in buckets:
                if tariff == "rce":
                    bucket = priced_cost(items, bins)
                    bucket_cost = bucket["cost"]
                    has_data = bucket["covered_seconds"] > 0
                else:
                    _, bucket_cost = fixed_cost(items, lambda at: rate(at.astimezone(now.tzinfo), tariff, cfg), minutes)
                    has_data = bool(items)
                running += bucket_cost
                chart.append([int(boundary.timestamp() * 1000), round(running, 4) if has_data else None])
            attrs["cumulative_cost_chart"] = chart
            result[(tariff, period)] = {"value": round(value, 4) if value is not None else None, "attributes": attrs}
    return result


