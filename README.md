# Energy Price Comparison for Home Assistant

A starter repository to compare daily, monthly, and yearly energy costs for G11, G12, G12w, and Dynamic tariffs in Home Assistant. It ships with:

- Template sensors that calculate costs for each tariff and period.
- Helper inputs for tariff rates and time/date ranges.
- Utility meters to derive monthly/yearly totals from daily usage and split G12/G12w by tariff.
- A Lovelace dashboard view with a comparison table and graphs.

## What you need

You must provide or map the following entities in Home Assistant:

- **Daily total energy consumption** (`sensor.energy_daily`, kWh).
- **Dynamic tariff price** (PLN/kWh), if you want dynamic pricing (sensor or helper input).

Monthly/yearly totals are derived automatically from the daily values in this package.

## Files

- `home_assistant/packages/energy_price_comparison.yaml` - helpers, utility meters, tariff schedule automation, and cost sensors.
- `home_assistant/dashboards/energy_price_comparison.yaml` - Lovelace view (table + graphs).

## Setup

1. Copy the package file into your Home Assistant config (e.g., `config/packages/energy_price_comparison.yaml`).
2. Map your daily energy sensor to `sensor.energy_daily` (or rename in the package).
3. Set tariff rates and time/date ranges using the input helpers in Home Assistant.
4. Add the dashboard YAML as a new Lovelace dashboard or view.

## Tariff schedule inputs

You can define two time ranges for each day/night tariff:

- **G12**: two day ranges and two night ranges.
- **G12w**: separate two day/night ranges for summer and winter.
- **G12w**: define the summer date range (start/end date). If the range crosses year-end, the automation handles it.

The automations update the G12/G12w tariff select every 5 minutes.

## Example entity mapping

Replace these placeholders in the package file with your actual entities:

| Placeholder | Example purpose |
| --- | --- |
| `sensor.energy_daily` | Total energy used today (kWh) |
| `sensor.dynamic_rate` | Dynamic price (PLN/kWh). If you don’t have it, the template will fall back to `input_number.dynamic_rate`. |

The package creates the following sensors automatically:

- `sensor.energy_monthly` and `sensor.energy_yearly` (derived from daily values).
- `sensor.g12_energy_*_day/night` and `sensor.g12w_energy_*_day/night` via `utility_meter`.

## Optional: utility_meter example

If you prefer to generate `sensor.energy_daily` yourself, use `utility_meter` with your total energy sensor.

```yaml
utility_meter:
  energy_daily:
    source: sensor.energy_total
    cycle: daily
```

## Next questions

If you want me to wire the package to your exact entity IDs, please share:

- Daily total energy (kWh).
- Dynamic price sensor (PLN/kWh), if available.

Once you share those, I can tailor the package to your exact setup.
