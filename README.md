# Battery Simulator for Home Assistant

Battery Simulator simulates one home battery using the actual hourly long-term statistics from Home Assistant.

## Inputs

- cumulative solar-production energy sensor;
- cumulative grid-export energy sensor;
- cumulative grid-import energy sensor;
- battery capacity in kWh;
- battery charge/discharge power in kW;
- total battery purchase and installation cost;
- electricity purchase price in EUR/kWh;
- feed-in compensation in EUR/kWh;
- variable feed-in cost in EUR/kWh.

The model uses a fixed 90% round-trip efficiency and a fixed 5% minimum state of charge.

## Outputs

- annual savings;
- simple payback period;
- avoided grid import;
- avoided grid export;
- equivalent full cycles;
- conversion losses;
- solar self-consumption;
- self-sufficiency;
- historical-data coverage.

## Historical data and cache

The integration reads all overlapping hourly long-term statistics available for the three selected energy sensors. It does not depend on data accumulated by the integration itself.

The latest result is cached in Home Assistant's `.storage` area. After a restart, update, or reinstallation, matching cached values are exposed immediately. Home Assistant then starts a complete recalculation using all currently available long-term statistics and replaces the cached result. Removing and re-adding the integration with the same settings can reuse the same cache.

If the Recorder database or its long-term statistics are deleted, the historical basis is also lost.

## Installation

Copy `custom_components/battery_simulator` into `/config/custom_components/` and restart Home Assistant. Then add **Battery Simulator** under **Settings > Devices & services**.

## Recalculate

The integration performs a complete recalculation every 12 hours. A recalculation can also be requested manually:

```yaml
action: battery_simulator.recalculate
```

## Financial model

Annual savings are calculated as:

```text
avoided import x purchase price
- avoided export x feed-in compensation
+ avoided export x variable feed-in cost
```

The simple payback period is the total purchase cost divided by annual savings. Financing, degradation, maintenance, replacement, tariff tiers, and dynamic-price arbitrage are not yet included.
