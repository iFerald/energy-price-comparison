"""Pure interval arithmetic used by every tariff and reporting period."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Callable, Iterable


def finite_number(value) -> float | None:
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if isfinite(result) else None


def timestamp(value) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else None
    value = finite_number(value)
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value, timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None


@dataclass(frozen=True, slots=True)
class EnergyInterval:
    start: datetime
    end: datetime
    kwh: float
    resolution: str = "hourly_statistics"

    def clip(self, start: datetime, end: datetime) -> EnergyInterval | None:
        left, right = max(start, self.start), min(end, self.end)
        if right <= left or self.end <= self.start:
            return None
        fraction = (right - left).total_seconds() / (self.end - self.start).total_seconds()
        return EnergyInterval(left, right, self.kwh * fraction, self.resolution)


def statistics_intervals(rows: list[dict]) -> list[EnergyInterval]:
    """Use adjacent reset-adjusted sums, never mix sum and meter state.

    Caller includes the preceding hour for a boundary baseline. Missing hours
    stay missing: consumption across an outage cannot be timed accurately.
    """
    result = []
    previous = None
    for row in sorted(rows, key=lambda row: timestamp(row.get("start")) or datetime.min.replace(tzinfo=timezone.utc)):
        start = timestamp(row.get("start"))
        end = timestamp(row.get("end")) or (start + timedelta(hours=1) if start else None)
        total = finite_number(row.get("sum"))
        if start is None or end is None or total is None or end <= start:
            previous = None
            continue
        if previous is not None:
            previous_end, previous_sum = previous
            delta = total - previous_sum
            if previous_end == start and delta >= 0:
                result.append(EnergyInterval(start, end, delta))
        previous = end, total
    return result


def history_intervals(points: Iterable[tuple[datetime, float | None]]) -> list[EnergyInterval]:
    """Detailed tail only. Invalid readings and resets break coverage."""
    result = []
    previous = None
    reset_floor = None
    for at, value in sorted(points, key=lambda point: point[0]):
        value = finite_number(value)
        if value is None or value < 0:
            previous = None
            continue
        if reset_floor is not None:
            if value < reset_floor:
                continue
            reset_floor = None
            previous = at, value
            continue
        if previous is not None:
            prev_at, prev_value = previous
            if value < prev_value:
                # A temporary zero and a real meter reset are indistinguishable
                # here. Leave the tail unpriced until recorder's adjusted sum
                # resolves it, instead of charging the entire rebound.
                reset_floor = prev_value
                previous = None
                continue
            if at > prev_at and value >= prev_value:
                result.append(EnergyInterval(prev_at, at, value - prev_value, "recorder_tail"))
        previous = at, value
    return result


def fixed_cost(intervals: Iterable[EnergyInterval], rate: Callable[[datetime], float], boundary_minutes: tuple[int, ...] = tuple(range(60))) -> tuple[float, float]:
    """Split at tariff boundary minutes and hourly UTC boundaries.

    UTC traversal handles both repeated and missing local hours at DST changes.
    Energy within a meter interval is estimated uniformly in elapsed time.
    """
    energy = cost = 0.0
    for interval in intervals:
        seconds = (interval.end - interval.start).total_seconds()
        if seconds <= 0:
            continue
        energy += interval.kwh
        at = interval.start
        while at < interval.end:
            hour = at.replace(minute=0, second=0, microsecond=0)
            candidates = [hour + timedelta(minutes=minute) for minute in boundary_minutes]
            until = min(interval.end, hour + timedelta(hours=1), *(point for point in candidates if point > at))
            cost += interval.kwh * (until - at).total_seconds() / seconds * rate(at)
            at = until
    return energy, cost


def priced_cost(intervals: Iterable[EnergyInterval], bins) -> dict[str, float]:
    """Price only covered energy; do not count gaps or overlaps twice."""
    bins = sorted(bins, key=lambda item: item.start_utc)
    energy = priced_energy = cost = covered_seconds = 0.0
    index = 0
    for interval in intervals:
        seconds = (interval.end - interval.start).total_seconds()
        if seconds <= 0:
            continue
        energy += interval.kwh
        while index < len(bins) and bins[index].end_utc <= interval.start:
            index += 1
        cursor = interval.start
        for price_index in range(index, len(bins)):
            item = bins[price_index]
            if item.start_utc >= interval.end:
                break
            left, right = max(cursor, item.start_utc), min(interval.end, item.end_utc)
            price = finite_number(item.price_pln_per_kwh)
            if right <= left or price is None:
                continue
            overlap = (right - left).total_seconds()
            kwh = interval.kwh * overlap / seconds
            cost += kwh * price
            priced_energy += kwh
            covered_seconds += overlap
            cursor = right
    return {"kwh": energy, "priced_kwh": priced_energy, "missing_price_kwh": max(0.0, energy - priced_energy), "cost": cost, "covered_seconds": covered_seconds}
