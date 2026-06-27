"""Switch entities: cup chiller and music-sync vibration."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CinesoundCoordinator
from . import sofa_protocol as P


@dataclass(frozen=True, kw_only=True)
class CinesoundSwitchDescription(SwitchEntityDescription):
    on_code: int
    off_code: int
    pid: int = P.PID_CTRL
    icon: str = "mdi:toggle-switch"


SWITCHES: tuple[CinesoundSwitchDescription, ...] = (
    # Cup chillers: same codes, left vs right selected by PID.
    CinesoundSwitchDescription(
        key="chiller_left",
        name="Left Cup Chiller",
        on_code=P.CMD["cup_cool_on"],
        off_code=P.CMD["cup_cool_off"],
        pid=P.PID_CTRL,
        icon="mdi:cup-water",
    ),
    CinesoundSwitchDescription(
        key="chiller_right",
        name="Right Cup Chiller",
        on_code=P.CMD["cup_cool_on"],
        off_code=P.CMD["cup_cool_off"],
        pid=P.PID_CTRL_RIGHT,
        icon="mdi:cup-water",
    ),
    # Music-sync vibration: left = massage1, right = massage2 (both PID=1).
    # Only audible/visible while audio is playing.
    CinesoundSwitchDescription(
        key="vibration_left",
        name="Left Music Vibration",
        on_code=P.CMD["audio_massage1_start"],
        off_code=P.CMD["audio_massage1_stop"],
        pid=P.PID_CTRL,
        icon="mdi:vibrate",
    ),
    CinesoundSwitchDescription(
        key="vibration_right",
        name="Right Music Vibration",
        on_code=P.CMD["audio_massage2_start"],
        off_code=P.CMD["audio_massage2_stop"],
        pid=P.PID_CTRL,
        icon="mdi:vibrate",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CinesoundCoordinator = entry.runtime_data
    async_add_entities(CinesoundSwitch(coordinator, desc) for desc in SWITCHES)


class CinesoundSwitch(SwitchEntity):
    """A simple on/off switch for sofa accessories."""

    _attr_has_entity_name = True
    _attr_is_on = False

    def __init__(
        self, coordinator: CinesoundCoordinator, desc: CinesoundSwitchDescription
    ) -> None:
        self._coordinator = coordinator
        self.entity_description = desc
        self._attr_unique_id = f"{coordinator.address}_{desc.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.name,
            manufacturer="YKD / DFS",
            model="Aventra Cinesound",
        )

    @property
    def icon(self) -> str:
        return self.entity_description.icon

    async def async_turn_on(self, **kwargs) -> None:
        desc = self.entity_description
        await self._coordinator.async_send(desc.on_code, pid=desc.pid)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        desc = self.entity_description
        await self._coordinator.async_send(desc.off_code, pid=desc.pid)
        self._attr_is_on = False
        self.async_write_ha_state()
