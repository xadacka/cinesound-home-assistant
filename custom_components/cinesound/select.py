"""Select entity for seat heat level."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CinesoundCoordinator
from . import sofa_protocol as P

HEAT_OPTIONS: dict[str, int] = {
    "Off":     P.CMD["heat_off"],
    "Level 1": P.CMD["heat_1"],
    "Level 2": P.CMD["heat_2"],
    "Level 3": P.CMD["heat_3"],
    "Level 4": P.CMD["heat_4"],
    "Level 5": P.CMD["heat_5"],
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CinesoundCoordinator = entry.runtime_data
    async_add_entities([CinesoundHeat(coordinator)])


class CinesoundHeat(SelectEntity):
    """Seat heating level selector."""

    _attr_name = "Seat Heat"
    _attr_has_entity_name = True
    _attr_options = list(HEAT_OPTIONS)
    _attr_current_option = "Off"
    _attr_icon = "mdi:heat-wave"

    def __init__(self, coordinator: CinesoundCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.address}_heat"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.name,
            manufacturer="YKD / DFS",
            model="Aventra Cinesound",
        )

    async def async_select_option(self, option: str) -> None:
        code = HEAT_OPTIONS[option]
        await self._coordinator.async_send(code)
        self._attr_current_option = option
        self.async_write_ha_state()
