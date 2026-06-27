"""Cover entities for sofa motors (recline, lumbar, headrest, storage lid)."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityDescription,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CinesoundCoordinator
from . import sofa_protocol as P


@dataclass(frozen=True, kw_only=True)
class CinesoundCoverDescription(CoverEntityDescription):
    open_code: int
    close_code: int
    pid: int = P.PID_CTRL
    icon: str = "mdi:sofa"


COVERS: tuple[CinesoundCoverDescription, ...] = (
    # Left seat
    CinesoundCoverDescription(
        key="left_recline",
        name="Left Recline",
        open_code=P.CMD["m1_up"],
        close_code=P.CMD["m1_down"],
        pid=P.PID_CTRL,
        icon="mdi:seat-recline-extra",
    ),
    CinesoundCoverDescription(
        key="left_lumbar",
        name="Left Lumbar",
        open_code=P.CMD["m2_up"],
        close_code=P.CMD["m2_down"],
        pid=P.PID_CTRL,
        icon="mdi:human-handsdown",
    ),
    CinesoundCoverDescription(
        key="left_headrest",
        name="Left Headrest",
        open_code=P.CMD["m3_up"],
        close_code=P.CMD["m3_down"],
        pid=P.PID_CTRL,
        icon="mdi:head",
    ),
    # Right seat (same codes, PID=9)
    CinesoundCoverDescription(
        key="right_recline",
        name="Right Recline",
        open_code=P.CMD["m1_up"],
        close_code=P.CMD["m1_down"],
        pid=P.PID_CTRL_RIGHT,
        icon="mdi:seat-recline-extra",
    ),
    CinesoundCoverDescription(
        key="right_lumbar",
        name="Right Lumbar",
        open_code=P.CMD["m2_up"],
        close_code=P.CMD["m2_down"],
        pid=P.PID_CTRL_RIGHT,
        icon="mdi:human-handsdown",
    ),
    CinesoundCoverDescription(
        key="right_headrest",
        name="Right Headrest",
        open_code=P.CMD["m3_up"],
        close_code=P.CMD["m3_down"],
        pid=P.PID_CTRL_RIGHT,
        icon="mdi:head",
    ),
    # Storage compartment lid
    CinesoundCoverDescription(
        key="storage",
        name="Storage Compartment",
        device_class=CoverDeviceClass.LID,
        open_code=P.CMD["cup_motor_up"],
        close_code=P.CMD["cup_motor_down"],
        pid=P.PID_CTRL,
        icon="mdi:tray-arrow-up",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CinesoundCoordinator = entry.runtime_data
    async_add_entities(CinesoundCover(coordinator, desc) for desc in COVERS)


class CinesoundCover(CoverEntity):
    """A motorised axis on the sofa.

    State is tracked optimistically (no position feedback from hardware).
    open  = reclined / extended / lid open
    close = upright / retracted / lid closed
    """

    _attr_supported_features = (
        CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
    )
    _attr_has_entity_name = True
    _attr_is_closed: bool | None = None  # unknown until first move

    def __init__(
        self, coordinator: CinesoundCoordinator, desc: CinesoundCoverDescription
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

    async def async_open_cover(self, **kwargs) -> None:
        desc: CinesoundCoverDescription = self.entity_description
        await self._coordinator.async_motor_start(desc.open_code, desc.pid, desc.key)
        self._attr_is_closed = False
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs) -> None:
        desc: CinesoundCoverDescription = self.entity_description
        await self._coordinator.async_motor_start(desc.close_code, desc.pid, desc.key)
        self._attr_is_closed = True
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs) -> None:
        await self._coordinator.async_motor_stop(self.entity_description.key)
        self._attr_is_closed = None
        self.async_write_ha_state()
