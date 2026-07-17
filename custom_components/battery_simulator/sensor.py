"""Sensors for Battery Simulator."""
from __future__ import annotations
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .coordinator import BatteryEvaluatorCoordinator

SENSORS = {
    "annual_savings": ("Annual savings", "€", "mdi:cash"),
    "payback_years": ("Payback period", "years", "mdi:calendar-clock"),
    "avoided_import_kwh": ("Avoided grid import", "kWh", "mdi:transmission-tower-import"),
    "avoided_export_kwh": ("Avoided grid export", "kWh", "mdi:transmission-tower-export"),
    "cycles": ("Equivalent cycles", "cycles/year", "mdi:battery-sync"),
    "battery_losses_kwh": ("Battery losses", "kWh/year", "mdi:lightning-bolt"),
    "self_consumption_pct": ("Solar self-consumption", "%", "mdi:solar-power"),
    "self_sufficiency_pct": ("Self-sufficiency", "%", "mdi:home-lightning-bolt"),
    "coverage_pct": ("Data coverage", "%", "mdi:database-check"),
}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback):
    coordinator = entry.runtime_data
    async_add_entities([BatteryEvaluatorSensor(coordinator, entry, key, *meta) for key, meta in SENSORS.items()])

class BatteryEvaluatorSensor(CoordinatorEntity[BatteryEvaluatorCoordinator], SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator, entry, key, name, unit, icon):
        super().__init__(coordinator); self.key = key
        self._attr_name = name; self._attr_native_unit_of_measurement = unit; self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = {"identifiers": {("battery_simulator", entry.entry_id)}, "name": "Battery Simulator", "manufacturer": "Battery Simulator"}
    @property
    def native_value(self):
        value = getattr(self.coordinator.data, self.key)
        return round(value, 2) if isinstance(value, float) else value
    @property
    def extra_state_attributes(self):
        if self.key == "coverage_pct":
            d = self.coordinator.data
            return {"hours": d.hours, "start": d.start, "end": d.end}
        return None
