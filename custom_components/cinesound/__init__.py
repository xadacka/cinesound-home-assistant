"""DFS Aventra Cinesound sofa: Home Assistant integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_ADDRESS, CONF_NAME
from .coordinator import CinesoundCoordinator

PLATFORMS = [
    Platform.COVER,
    Platform.LIGHT,
    Platform.SELECT,
    Platform.MEDIA_PLAYER,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = CinesoundCoordinator(
        hass,
        entry.data[CONF_ADDRESS],
        entry.data.get(CONF_NAME, "Cinesound Sofa"),
    )
    entry.runtime_data = coordinator
    await coordinator.async_setup()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_teardown()
    return unload_ok
