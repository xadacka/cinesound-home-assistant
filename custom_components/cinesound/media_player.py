"""Media player entity for the Cinesound built-in audio system."""
from __future__ import annotations

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CinesoundCoordinator
from . import sofa_protocol as P

SUPPORTED = (
    MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PAUSE
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_MUTE
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CinesoundCoordinator = entry.runtime_data
    async_add_entities([CinesoundMediaPlayer(coordinator)])


class CinesoundMediaPlayer(MediaPlayerEntity):
    """Cinesound built-in audio.

    Volume is relative-only (no feedback), so we use VOLUME_STEP
    rather than VOLUME_SET. State is tracked optimistically.
    """

    _attr_name = "Audio"
    _attr_has_entity_name = True
    _attr_supported_features = SUPPORTED
    _attr_icon = "mdi:speaker"

    def __init__(self, coordinator: CinesoundCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.address}_audio"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.name,
            manufacturer="YKD / DFS",
            model="Aventra Cinesound",
        )
        self._attr_state = MediaPlayerState.IDLE
        self._attr_is_volume_muted = False

    async def async_media_play(self) -> None:
        await self._coordinator.async_send(P.CMD["audio_play"])
        self._attr_state = MediaPlayerState.PLAYING
        self.async_write_ha_state()

    async def async_media_pause(self) -> None:
        await self._coordinator.async_send(P.CMD["audio_pause"])
        self._attr_state = MediaPlayerState.PAUSED
        self.async_write_ha_state()

    async def async_media_stop(self) -> None:
        await self._coordinator.async_send(P.CMD["audio_off"])
        self._attr_state = MediaPlayerState.IDLE
        self.async_write_ha_state()

    async def async_media_next_track(self) -> None:
        await self._coordinator.async_send(P.CMD["audio_next"])

    async def async_media_previous_track(self) -> None:
        await self._coordinator.async_send(P.CMD["audio_prev"])

    async def async_volume_up(self) -> None:
        await self._coordinator.async_send(P.CMD["audio_vol_up"])

    async def async_volume_down(self) -> None:
        await self._coordinator.async_send(P.CMD["audio_vol_down"])

    async def async_mute_volume(self, mute: bool) -> None:
        code = P.CMD["audio_mute"] if mute else P.CMD["audio_unmute"]
        await self._coordinator.async_send(code)
        self._attr_is_volume_muted = mute
        self.async_write_ha_state()
