from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Any, Sequence

from .pse_rce_api import RCEBin

def compute_cost_overlap(
    energy_points: Sequence[tuple[datetime, float]],
    bins: Sequence[RCEBin],
    *,
    start_utc: datetime,
    end_utc: datetime,
) -> tuple[float, float, int]:
    """Compute (kWh, cost PLN, missing_energy_intervals) using overlap-weighting.

    energy_points: (timestamp_utc, monotonic_total_kwh) sorted ascending.
    bins: 15-min price bins in UTC.
    start_utc/end_utc: effective bounds (partial coverage supported).

    Negative deltas are ignored.
    """
    if len(energy_points) < 2 or not bins:
        return (0.0, 0.0, 0)

    # ensure sorted
    pts = sorted(energy_points, key=lambda x: x[0])
    bs = sorted(bins, key=lambda b: b.start_utc)

    kwh_total = 0.0
    cost_total = 0.0
    missing_intervals = 0

    bi = 0

    prev_t, prev_v = pts[0]
    for t, v in pts[1:]:
        a = max(prev_t, start_utc)
        b = min(t, end_utc)
        dt_seconds = (b - a).total_seconds()
        d = v - prev_v

        prev_t, prev_v = t, v

        if dt_seconds <= 0 or d <= 0:
            continue

        kwh_total += d

        while bi < len(bs) and bs[bi].end_utc <= a:
            bi += 1

        covered = 0.0
        interval_cost = 0.0
        bj = bi
        while bj < len(bs) and bs[bj].start_utc < b:
            s = bs[bj].start_utc
            e = bs[bj].end_utc
            ov_start = a if a > s else s
            ov_end = b if b < e else e
            ov = (ov_end - ov_start).total_seconds()
            if ov > 0:
                covered += ov
                interval_cost += (d * (ov / dt_seconds)) * bs[bj].price_pln_per_kwh
            bj += 1

        if covered == 0:
            missing_intervals += 1
        else:
            cost_total += interval_cost

    return (kwh_total, cost_total, missing_intervals)
