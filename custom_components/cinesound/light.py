"""Light entity for the sofa's LED strip."""
from __future__ import annotations

from homeassistant.components.light import (
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CinesoundCoordinator
from . import sofa_protocol as P

# Named effects (modes + special)
EFFECTS: dict[str, int] = {
    "Rainbow": P.CMD["led_rgbv"],
    "Breathing": P.CMD["led_breath"],
    "Mode 1": P.CMD["led_m1"],
    "Mode 2": P.CMD["led_m2"],
    "Mode 3": P.CMD["led_m3"],
    "Mode 4": P.CMD["led_m4"],
    "Mode 5": P.CMD["led_m5"],
    "Mode 6": P.CMD["led_m6"],
}

# Hue (°) → LED preset command.  Saturation < 25 → white.
_HUE_MAP = [
    (0,   P.CMD["led_r"]),   # red
    (60,  P.CMD["led_rg"]),  # yellow
    (120, P.CMD["led_g"]),   # green
    (180, P.CMD["led_gb"]),  # cyan
    (240, P.CMD["led_b"]),   # blue
    (300, P.CMD["led_rb"]),  # magenta
]


def _hs_to_cmd(hs: tuple[float, float]) -> int:
    """Quantize an HS color to the nearest sofa LED preset."""
    hue, sat = hs
    if sat < 25:
        return P.CMD["led_white"]
    return min(
        _HUE_MAP,
        key=lambda hp: min(abs(hp[0] - hue), 360 - abs(hp[0] - hue)),
    )[1]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CinesoundCoordinator = entry.runtime_data
    async_add_entities([CinesoundLight(coordinator)])


class CinesoundLight(LightEntity):
    """LED ambient lighting on the sofa.

    HS color wheel in HA is quantized to the sofa's 6 solid presets plus white.
    Effects cover Rainbow, Breathing, and Mode 1–6.
    """

    _attr_name = "LED"
    _attr_has_entity_name = True
    _attr_color_mode = ColorMode.HS
    _attr_supported_color_modes = {ColorMode.HS}
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = list(EFFECTS)
    _attr_icon = "mdi:led-strip-variant"

    def __init__(self, coordinator: CinesoundCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.address}_led"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.name,
            manufacturer="YKD / DFS",
            model="Aventra Cinesound",
        )
        self._attr_is_on = False
        self._attr_hs_color: tuple[float, float] = (0, 0)  # white default
        self._attr_effect: str | None = None

    async def async_turn_on(self, **kwargs) -> None:
        effect = kwargs.get(ATTR_EFFECT)
        hs = kwargs.get(ATTR_HS_COLOR)

        if effect:
            code = EFFECTS[effect]
            self._attr_effect = effect
            self._attr_hs_color = (0, 0)
        elif hs:
            code = _hs_to_cmd(hs)
            self._attr_hs_color = hs
            self._attr_effect = None
        else:
            # plain turn_on with no kwargs; restore last state
            code = (
                EFFECTS[self._attr_effect]
                if self._attr_effect
                else _hs_to_cmd(self._attr_hs_color)
            )

        await self._coordinator.async_send(code)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self._coordinator.async_send(P.CMD["led_off"])
        self._attr_is_on = False
        self.async_write_ha_state()
