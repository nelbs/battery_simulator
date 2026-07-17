"""Tests for the simulation engine."""

from custom_components.battery_simulator.simulator import HourEnergy, simulate


def test_simple_shift() -> None:
    """Stored solar energy should replace later grid import."""
    rows = [
        HourEnergy(imported=0, exported=5, solar=5),
        HourEnergy(imported=5, exported=0, solar=0),
    ]
    result = simulate(
        rows,
        capacity_kwh=5,
        charge_power_kw=5,
        discharge_power_kw=5,
        roundtrip_efficiency=1,
        minimum_soc_fraction=0,
        buy_price=0.30,
        sell_price=0.08,
        purchase_cost=3500,
        export_cost=0,
        annualization_factor=1,
    )
    assert result.avoided_import_kwh == 5
    assert result.avoided_export_kwh == 5
    assert result.annual_savings == 1.1
    assert result.payback_years == 3500 / 1.1
