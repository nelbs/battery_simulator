"""Battery Simulator integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, PLATFORMS, SERVICE_RECALCULATE
from .coordinator import BatteryEvaluatorCoordinator


type BatteryEvaluatorConfigEntry = ConfigEntry[BatteryEvaluatorCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up service actions."""

    async def async_recalculate(call: ServiceCall) -> None:
        """Force a complete recalculation from long-term statistics."""
        for entry in hass.config_entries.async_entries(DOMAIN):
            coordinator = entry.runtime_data
            await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_RECALCULATE, async_recalculate)
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BatteryEvaluatorConfigEntry,
) -> bool:
    """Set up Battery Simulator from a config entry."""
    coordinator = BatteryEvaluatorCoordinator(hass, entry)
    cached_result = await coordinator.async_load_cached_result()

    if cached_result is None:
        await coordinator.async_config_entry_first_refresh()
    else:
        # Expose the cached values immediately, then replace them with a complete
        # recalculation from all available long-term statistics.
        coordinator.async_set_updated_data(cached_result)

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    if cached_result is not None:
        entry.async_create_background_task(
            hass,
            coordinator.async_request_refresh(),
            "battery_simulator_full_recalculation",
        )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: BatteryEvaluatorConfigEntry,
) -> bool:
    """Unload an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(
    hass: HomeAssistant,
    entry: BatteryEvaluatorConfigEntry,
) -> None:
    """Reload after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
