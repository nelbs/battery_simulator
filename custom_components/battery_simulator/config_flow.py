"""Config flow for Battery Simulator."""
from __future__ import annotations
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from .const import *

ENERGY_SELECTOR = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", device_class="energy"))

def _number(minimum, maximum, step, unit):
    return selector.NumberSelector(selector.NumberSelectorConfig(min=minimum, max=maximum, step=step, unit_of_measurement=unit, mode=selector.NumberSelectorMode.BOX))

def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema({
        vol.Required(CONF_SOLAR_ENTITY, default=d.get(CONF_SOLAR_ENTITY, "")): ENERGY_SELECTOR,
        vol.Required(CONF_EXPORT_ENTITY, default=d.get(CONF_EXPORT_ENTITY, "")): ENERGY_SELECTOR,
        vol.Required(CONF_IMPORT_ENTITY, default=d.get(CONF_IMPORT_ENTITY, "")): ENERGY_SELECTOR,
        vol.Required(CONF_CAPACITY, default=d.get(CONF_CAPACITY, DEFAULT_CAPACITY)): _number(0.5, 100, 0.1, "kWh"),
        vol.Required(CONF_BATTERY_POWER, default=d.get(CONF_BATTERY_POWER, DEFAULT_BATTERY_POWER)): _number(0.1, 50, 0.1, "kW"),
        vol.Required(CONF_PURCHASE_COST, default=d.get(CONF_PURCHASE_COST, DEFAULT_PURCHASE_COST)): _number(0, 100000, 50, "€"),
        vol.Required(CONF_BUY_PRICE, default=d.get(CONF_BUY_PRICE, DEFAULT_BUY_PRICE)): _number(-1, 2, 0.001, "€/kWh"),
        vol.Required(CONF_SELL_PRICE, default=d.get(CONF_SELL_PRICE, DEFAULT_SELL_PRICE)): _number(-1, 2, 0.001, "€/kWh"),
        vol.Required(CONF_EXPORT_COST, default=d.get(CONF_EXPORT_COST, DEFAULT_EXPORT_COST)): _number(0, 2, 0.001, "€/kWh"),
    })

class BatteryEvaluatorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2
    async def async_step_user(self, user_input=None) -> FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title="Battery Simulator", data=user_input)
        return self.async_show_form(step_id="user", data_schema=_schema())
    @staticmethod
    def async_get_options_flow(config_entry):
        return BatteryEvaluatorOptionsFlow(config_entry)

class BatteryEvaluatorOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry): self.config_entry = config_entry
    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(step_id="init", data_schema=_schema({**self.config_entry.data, **self.config_entry.options}))
