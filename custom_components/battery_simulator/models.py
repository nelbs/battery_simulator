"""Data models for Battery Simulator."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(slots=True)
class VariantResult:
    capacity_kwh: float
    avoided_import_kwh: float
    avoided_export_kwh: float
    battery_losses_kwh: float
    cycles: float
    annual_savings: float
    investment: float
    payback_years: float | None
    self_consumption_pct: float | None
    self_sufficiency_pct: float | None

@dataclass(slots=True)
class EvaluationResult:
    start: str = ""
    end: str = ""
    hours: int = 0
    coverage_pct: float = 0.0
    baseline_import_kwh: float = 0.0
    baseline_export_kwh: float = 0.0
    solar_kwh: float = 0.0
    avoided_import_kwh: float = 0.0
    avoided_export_kwh: float = 0.0
    battery_losses_kwh: float = 0.0
    cycles: float = 0.0
    annual_savings: float = 0.0
    payback_years: float | None = None
    self_consumption_pct: float | None = None
    self_sufficiency_pct: float | None = None
