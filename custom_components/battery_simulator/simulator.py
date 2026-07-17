"""Battery simulation engine."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import sqrt

from .models import VariantResult


@dataclass(frozen=True, slots=True)
class HourEnergy:
    """Energy flows in one hourly interval."""

    imported: float
    exported: float
    solar: float | None = None


def simulate(
    rows: Iterable[HourEnergy],
    *,
    capacity_kwh: float,
    charge_power_kw: float,
    discharge_power_kw: float,
    roundtrip_efficiency: float,
    minimum_soc_fraction: float,
    buy_price: float,
    sell_price: float,
    purchase_cost: float,
    export_cost: float,
    annualization_factor: float,
) -> VariantResult:
    """Simulate self-consumption battery dispatch."""
    usable_floor = capacity_kwh * minimum_soc_fraction
    soc = usable_floor
    one_way_efficiency = sqrt(roundtrip_efficiency)
    avoided_import = 0.0
    avoided_export = 0.0
    charged_input = 0.0
    discharged_output = 0.0
    total_solar = 0.0
    total_load = 0.0
    baseline_direct_solar = 0.0

    for row in rows:
        imported = max(0.0, row.imported)
        exported = max(0.0, row.exported)
        if row.solar is not None:
            solar = max(0.0, row.solar)
            total_solar += solar
            load = max(0.0, solar + imported - exported)
            total_load += load
            baseline_direct_solar += max(0.0, solar - exported)

        room = max(0.0, capacity_kwh - soc)
        charge_input = min(exported, charge_power_kw, room / one_way_efficiency)
        soc += charge_input * one_way_efficiency
        avoided_export += charge_input
        charged_input += charge_input

        available_output = max(0.0, soc - usable_floor) * one_way_efficiency
        discharge_output = min(imported, discharge_power_kw, available_output)
        soc -= discharge_output / one_way_efficiency
        avoided_import += discharge_output
        discharged_output += discharge_output

    annual_avoided_import = avoided_import * annualization_factor
    annual_avoided_export = avoided_export * annualization_factor
    annual_savings = (
        annual_avoided_import * buy_price
        - annual_avoided_export * sell_price
        + annual_avoided_export * export_cost
    )
    investment = purchase_cost
    payback = investment / annual_savings if annual_savings > 0 else None
    cycles = discharged_output / capacity_kwh * annualization_factor if capacity_kwh else 0.0
    losses = max(0.0, charged_input - discharged_output) * annualization_factor

    self_consumption = None
    self_sufficiency = None
    if total_solar > 0:
        self_consumption = min(100.0, 100.0 * (baseline_direct_solar + avoided_export) / total_solar)
    if total_load > 0:
        direct = baseline_direct_solar
        self_sufficiency = min(100.0, 100.0 * (direct + avoided_import) / total_load)

    return VariantResult(
        capacity_kwh=capacity_kwh,
        avoided_import_kwh=annual_avoided_import,
        avoided_export_kwh=annual_avoided_export,
        battery_losses_kwh=losses,
        cycles=cycles,
        annual_savings=annual_savings,
        investment=investment,
        payback_years=payback,
        self_consumption_pct=self_consumption,
        self_sufficiency_pct=self_sufficiency,
    )
