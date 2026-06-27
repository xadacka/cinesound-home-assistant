"""Light entity for the sofa's LED strip (full RGB + brightness)."""
from __future__ import annotations

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CinesoundCoordinator
from . import sofa_protocol as P


def _rgbv_param(rgb: tuple[int, int, int], brightness: int) -> int:
    """Pack colour + brightness into the led_rgbv parameter.

    Encoding reverse-engineered from the app's NewRGBActivity:
        dp = (0xRRGGBB << 8) | (brightness & 0xFF)   ->   0xRRGGBBVV
    The low byte is the brightness/value (0-255); a value of 0 = off.
    """
    r, g, b = rgb
    return ((r & 0xFF) << 24) | ((g & 0xFF) << 16) | ((b & 0xFF) << 8) | (brightness & 0xFF)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CinesoundCoordinator = entry.runtime_data
    async_add_entities([CinesoundLight(coordinator)])


class CinesoundLight(LightEntity):
    """LED ambient lighting on the sofa.

    Full RGB colour wheel plus brightness, both carried in the led_rgbv
    parameter (0xRRGGBBVV). The hardware's preset/effect commands
    (solid colours, breathing, modes) do nothing on this unit, so they
    are not exposed.
    """

    _attr_name = "LED"
    _attr_has_entity_name = True
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
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
        self._attr_rgb_color: tuple[int, int, int] = (255, 255, 255)
        self._attr_brightness = 255

    async def async_turn_on(self, **kwargs) -> None:
        if ATTR_RGB_COLOR in kwargs:
            self._attr_rgb_color = kwargs[ATTR_RGB_COLOR]
        if ATTR_BRIGHTNESS in kwargs:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]

        brightness = self._attr_brightness or 255
        param = _rgbv_param(self._attr_rgb_color, brightness)
        await self._coordinator.async_send(P.CMD["led_rgbv"], param)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self._coordinator.async_send(P.CMD["led_off"])
        self._attr_is_on = False
        self.async_write_ha_state()
