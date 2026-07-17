"""Coordinator for Battery Simulator."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from functools import partial
import hashlib
import json
import logging
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CACHE_STORAGE_KEY,
    CACHE_STORAGE_VERSION,
    CONF_BATTERY_POWER,
    CONF_BUY_PRICE,
    CONF_CAPACITY,
    CONF_EXPORT_COST,
    CONF_EXPORT_ENTITY,
    CONF_IMPORT_ENTITY,
    CONF_PURCHASE_COST,
    CONF_SELL_PRICE,
    CONF_SOLAR_ENTITY,
    DEFAULT_MIN_SOC_FRACTION,
    DEFAULT_ROUNDTRIP_EFFICIENCY,
)
from .models import EvaluationResult
from .simulator import HourEnergy, simulate

_LOGGER = logging.getLogger(__name__)


class BatteryEvaluatorCoordinator(DataUpdateCoordinator[EvaluationResult]):
    """Read all available statistics and evaluate the configured battery."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(
            hass,
            CACHE_STORAGE_VERSION,
            CACHE_STORAGE_KEY,
        )
        super().__init__(
            hass,
            _LOGGER,
            name="Battery Simulator",
            update_interval=timedelta(hours=12),
        )

    @property
    def config(self) -> dict[str, Any]:
        """Return merged configuration and options."""
        return {**self.entry.data, **self.entry.options}

    @property
    def cache_id(self) -> str:
        """Return a stable identifier based on sensors and calculation settings."""
        encoded = json.dumps(
            self.config,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    async def async_load_cached_result(self) -> EvaluationResult | None:
        """Load a matching cached result, if one exists.

        The cache is independent of the config-entry ID. Removing and re-adding the
        integration with the same settings can therefore reuse the last result.
        """
        stored = await self._store.async_load()
        if not stored:
            return None

        cached = stored.get("results", {}).get(self.cache_id)
        if not isinstance(cached, dict):
            return None

        result = cached.get("result")
        if not isinstance(result, dict):
            return None

        try:
            return EvaluationResult(**result)
        except (TypeError, ValueError):
            _LOGGER.warning("Ignoring an invalid Battery Simulator cache entry")
            return None

    async def _async_save_cached_result(self, result: EvaluationResult) -> None:
        """Persist the latest result for fast recovery after reinstall or restart."""
        stored = await self._store.async_load() or {}
        results = stored.setdefault("results", {})
        results[self.cache_id] = {
            "saved_at": dt_util.utcnow().isoformat(),
            "result": asdict(result),
        }

        # Prevent abandoned configurations from growing the storage file forever.
        if len(results) > 10:
            ordered = sorted(
                results.items(),
                key=lambda item: item[1].get("saved_at", ""),
                reverse=True,
            )
            stored["results"] = dict(ordered[:10])

        await self._store.async_save(stored)

    async def _async_update_data(self) -> EvaluationResult:
        """Run a complete recalculation using all overlapping long-term statistics."""
        cfg = self.config
        end = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
        start = datetime(2000, 1, 1, tzinfo=timezone.utc)
        statistic_ids = [
            cfg[CONF_IMPORT_ENTITY],
            cfg[CONF_EXPORT_ENTITY],
            cfg[CONF_SOLAR_ENTITY],
        ]

        try:
            query = partial(
                statistics_during_period,
                self.hass,
                start,
                end,
                statistic_ids,
                "hour",
                None,
                {"sum"},
            )
            stats = await get_instance(self.hass).async_add_executor_job(query)
        except Exception as err:
            raise UpdateFailed(f"Unable to read recorder statistics: {err}") from err

        series = {
            entity_id: _hourly_changes(stats.get(entity_id, []))
            for entity_id in statistic_ids
        }
        common = (
            set(series[statistic_ids[0]])
            & set(series[statistic_ids[1]])
            & set(series[statistic_ids[2]])
        )
        timestamps = sorted(common)

        if not timestamps:
            raise UpdateFailed("No overlapping hourly long-term statistics found")

        rows = [
            HourEnergy(
                imported=series[statistic_ids[0]][timestamp],
                exported=series[statistic_ids[1]][timestamp],
                solar=series[statistic_ids[2]][timestamp],
            )
            for timestamp in timestamps
        ]

        actual_start = timestamps[0]
        elapsed_days = max((end - actual_start).total_seconds() / 86400, 1)
        annualization = 365.2425 / elapsed_days

        simulation = simulate(
            rows,
            capacity_kwh=float(cfg[CONF_CAPACITY]),
            charge_power_kw=float(cfg[CONF_BATTERY_POWER]),
            discharge_power_kw=float(cfg[CONF_BATTERY_POWER]),
            roundtrip_efficiency=DEFAULT_ROUNDTRIP_EFFICIENCY,
            minimum_soc_fraction=DEFAULT_MIN_SOC_FRACTION,
            buy_price=float(cfg[CONF_BUY_PRICE]),
            sell_price=float(cfg[CONF_SELL_PRICE]),
            purchase_cost=float(cfg[CONF_PURCHASE_COST]),
            export_cost=float(cfg[CONF_EXPORT_COST]),
            annualization_factor=annualization,
        )

        result = EvaluationResult(
            start=actual_start.isoformat(),
            end=end.isoformat(),
            hours=len(rows),
            coverage_pct=min(100.0, len(rows) / (elapsed_days * 24) * 100),
            baseline_import_kwh=sum(row.imported for row in rows) * annualization,
            baseline_export_kwh=sum(row.exported for row in rows) * annualization,
            solar_kwh=sum(row.solar or 0 for row in rows) * annualization,
            avoided_import_kwh=simulation.avoided_import_kwh,
            avoided_export_kwh=simulation.avoided_export_kwh,
            battery_losses_kwh=simulation.battery_losses_kwh,
            cycles=simulation.cycles,
            annual_savings=simulation.annual_savings,
            payback_years=simulation.payback_years,
            self_consumption_pct=simulation.self_consumption_pct,
            self_sufficiency_pct=simulation.self_sufficiency_pct,
        )
        await self._async_save_cached_result(result)
        return result


def _hourly_changes(points: list[dict[str, Any]]) -> dict[Any, float]:
    """Convert cumulative statistics sums into hourly energy differences."""
    output: dict[Any, float] = {}
    previous: float | None = None

    for point in points:
        value = point.get("sum")
        timestamp = point.get("start")
        if value is None or timestamp is None:
            continue

        value = float(value)
        if previous is not None:
            delta = value - previous
            output[timestamp] = max(0.0, value if delta < 0 else delta)
        previous = value

    return output
