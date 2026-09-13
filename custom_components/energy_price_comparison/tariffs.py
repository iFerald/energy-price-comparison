"""Configured energy-only tariffs; supplier rates are never fetched or changed."""
from __future__ import annotations

from datetime import timedelta

from . import const


def settings(entry):
    result = {}
    for name, key in vars(const).items():
        if name.startswith("CONF_"):
            default_name = "DEFAULT_" + name[5:]
            if hasattr(const, default_name):
                result[key] = entry.options.get(key, entry.data.get(key, getattr(const, default_name)))
    return result


def in_range(hm, start, end):
    if start < end:
        return start <= hm < end
    return hm >= start or hm < end


def is_day(local, tariff, cfg):
    if tariff == "g11":
        return True
    if tariff == "g12w" and local.weekday() >= 5:
        return False
    if tariff == "g12n":
        return local.weekday() != 6 and in_range(local.strftime("%H:%M"), cfg["g12n_day_start"], cfg["g12n_night_start"])
    season = "summer" if local.dst() and local.dst() != timedelta() else "winter"
    hm = local.strftime("%H:%M")
    return in_range(hm, cfg[f"{tariff}_day_range_1_start"], cfg[f"{tariff}_night_range_1_{season}_start"]) or in_range(hm, cfg[f"{tariff}_day_range_2_{season}_start"], cfg[f"{tariff}_night_range_2_start"])


def rate(local, tariff, cfg):
    if tariff == "g11":
        return float(cfg["g11_rate_pln_per_kwh"])
    band = "day" if is_day(local, tariff, cfg) else "night"
    return float(cfg[f"{tariff}_{band}_rate_pln_per_kwh"])
