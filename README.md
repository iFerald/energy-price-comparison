# Energy Price Comparison

Compare one cumulative grid-import meter against G11, G12, G12n, G12w and historical PSE RCE prices for today, this Monday-based week, this calendar month, this year and last year.

## Installation and configuration

Install this repository through HACS as an integration, restart Home Assistant, then add **Energy Price Comparison** under Devices & services. Version 0.0.14 targets Home Assistant 2026.9.1 or later. Existing 0.0.13 entity identifiers and configuration keys are preserved. Back up Home Assistant before updating.

Choose a cumulative imported-energy sensor with `total` or `total_increasing` state class and Wh, kWh or MWh units. The optional live RCE display source expects PLN/MWh; historical RCE costs come from PSE independently. Configure your net energy rates and tariff hours. Saving options reloads the integration and recalculates historical comparisons using those rates.

These are **net energy-only comparisons**, not complete electricity bills. VAT, distribution, fixed charges and supplier markups are excluded. All tariffs use the same imported consumption; solar production and battery operation remain those actually measured rather than simulated for each tariff.

The existing rules are retained: G12/G12w use configured summer hours during local daylight-saving time; G12w weekends and G12n Sundays use the night rate. Public holidays are not separately modelled. Check the configured schedule against your supplier's contract.

## Historical data and accuracy

Completed hours use Home Assistant's durable long-term statistics. Recent recorder states fill only the unfinished tail, so normal recorder history purges do not turn a yearly total into a moving ten-day total. The preceding hourly record provides the baseline; raw meter values are never mixed with reset-adjusted statistical sums.

Consumption is allocated uniformly within each measured interval. Historical hourly data cannot reconstruct precise quarter-hour consumption, so RCE historical costs are estimates. UTC interval splitting handles daylight-saving changes. Missing readings, statistical gaps and unresolved live meter resets are exposed as missing coverage; the integration does not invent lost data.

Each cost sensor provides `energy_coverage_ratio`, `coverage_status`, `coverage_start_local`, `coverage_end_local` and `cumulative_cost_chart`. RCE also reports `priced_kwh`, `missing_price_kwh` and `coverage_ratio_time`. A partial total must not be compared as a complete bill. Missing PSE prices are retried, and already cached prices survive temporary API failures. Initial historical price backfilling runs in bounded batches.

Positive fixed-tariff totals should grow within the reporting period as consumption accumulates. Period resets, changed configured rates and corrected source statistics can legitimately change totals. Negative RCE prices can legitimately reduce an RCE total.

## Dashboard

The `cumulative_cost_chart` attribute is an array of `[timestamp_milliseconds, cumulative_cost_PLN]` pairs. It contains hourly points for today, daily points for this week/month and monthly points for yearly comparisons. Missing buckets are `null`. ApexCharts cards can read it with:

```yaml
data_generator: return entity.attributes.cumulative_cost_chart || [];
```

Use separate charts for each reporting period and show coverage alongside the totals. Do not combine daily, weekly, monthly and yearly sensor histories on the same scale.

## Development

The `preserve-ha-0.0.13` branch preserves the owner's nine installed files, including RCE work previously edited directly in Home Assistant. Development continues in GitHub.

Run `python -m unittest discover -s tests -v` with `aiohttp` and `tzdata` installed. GitHub Actions additionally imports the integration against Home Assistant and recorder dependencies. Unit tests isolate I/O boundaries; a live reload and sensor/dashboard check are still required before considering deployment validated.
