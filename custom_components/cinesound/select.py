"""Select entities for seat heat level (left and right seats)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CinesoundCoordinator
from . import sofa_protocol as P

# Only Off / Level 1 / Level 2 exist on this sofa (m3-m5 do nothing).
HEAT_OPTIONS: dict[str, int] = {
    "Off":     P.CMD["heat_off"],
    "Level 1": P.CMD["heat_1"],
    "Level 2": P.CMD["heat_2"],
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CinesoundCoordinator = entry.runtime_data
    async_add_entities([
        CinesoundHeat(coordinator, "Left Seat Heat", "heat_left", P.PID_CTRL),
        CinesoundHeat(coordinator, "Right Seat Heat", "heat_right", P.PID_CTRL_RIGHT),
    ])


class CinesoundHeat(SelectEntity):
    """Seat heating level selector for one seat (left or right)."""

    _attr_has_entity_name = True
    _attr_options = list(HEAT_OPTIONS)
    _attr_current_option = "Off"
    _attr_icon = "mdi:heat-wave"

    def __init__(
        self, coordinator: CinesoundCoordinator, name: str, key: str, pid: int
    ) -> None:
        self._coordinator = coordinator
        self._pid = pid
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.address}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.name,
            manufacturer="YKD / DFS",
            model="Aventra Cinesound",
        )

    async def async_select_option(self, option: str) -> None:
        await self._coordinator.async_send(HEAT_OPTIONS[option], pid=self._pid)
        self._attr_current_option = option
        self.async_write_ha_state()
