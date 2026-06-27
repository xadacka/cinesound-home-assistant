"""BLE connection coordinator for the Cinesound sofa."""
from __future__ import annotations

import asyncio
import logging

from bleak import BleakClient, BleakError

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.core import HomeAssistant

from .const import MOTOR_SAFETY_TIMEOUT, NOTIFY_UUID, WRITE_UUID
from . import sofa_protocol as P

_LOGGER = logging.getLogger(__name__)


class CinesoundCoordinator:
    """Single BLE connection to the sofa, shared by all platform entities.

    Motor control model: send one move command (sofa keeps running autonomously),
    then auto-stop after MOTOR_SAFETY_TIMEOUT seconds or on explicit stop_cover.
    The Android app's 150 ms deadman repeat is a safety belt, not a hardware
    requirement; a single command is sufficient.
    """

    def __init__(self, hass: HomeAssistant, address: str, name: str) -> None:
        self.hass = hass
        self.address = address
        self.name = name
        self._client: BleakClient | None = None
        self._connect_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        # Per-motor safety timeout handles keyed by motor_key string.
        self._motor_timeouts: dict[str, asyncio.TimerHandle] = {}
        # Remember which PID (side) each motor was started on, so the stop
        # command can be addressed to the correct side.
        self._motor_pids: dict[str, int] = {}
        self._serial = 0

    def _next_serial(self) -> int:
        self._serial = (self._serial + 1) & 0xFF
        return self._serial

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_setup(self) -> None:
        """Attempt initial connect; retries happen on demand."""
        await self.async_connect()

    async def async_teardown(self) -> None:
        """Cancel all timers, send stop, and disconnect cleanly."""
        for handle in list(self._motor_timeouts.values()):
            handle.cancel()
        self._motor_timeouts.clear()
        if self._client and self._client.is_connected:
            try:
                await self._raw_write(P.CMD["stop_motor"], pid=P.PID_CTRL)
                await self._raw_write(P.CMD["stop_motor"], pid=P.PID_CTRL_RIGHT)
                await self._client.disconnect()
            except Exception:  # noqa: BLE001
                pass
        self._client = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def async_connect(self) -> bool:
        async with self._connect_lock:
            if self._client and self._client.is_connected:
                return True
            ble_device = async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if ble_device is None:
                _LOGGER.debug(
                    "BLE device %s not yet visible; will retry on next command",
                    self.address,
                )
                return False
            try:
                client = BleakClient(
                    ble_device, disconnected_callback=self._on_disconnect
                )
                await client.connect()
                # Status notifications are only used for debug logging; failing to
                # subscribe must not prevent command writes. Keep it non-fatal.
                try:
                    await client.start_notify(NOTIFY_UUID, self._on_notify)
                except (BleakError, asyncio.TimeoutError, EOFError) as err:
                    _LOGGER.debug(
                        "Notify setup on %s failed (status feedback disabled): %s",
                        self.address, err,
                    )
                # Only commit the client if the link is genuinely still up. The
                # sofa sometimes drops immediately after connect (e.g. phone app
                # still holding the single allowed BLE connection).
                if not client.is_connected:
                    self._client = None
                    return False
                self._client = client
                _LOGGER.info("Connected to %s (%s)", self.name, self.address)
                return True
            except (BleakError, asyncio.TimeoutError) as err:
                _LOGGER.warning("Connect to %s failed: %s", self.address, err)
                self._client = None
                return False

    def _on_disconnect(self, _client: BleakClient) -> None:
        _LOGGER.warning("%s disconnected; will reconnect on next command", self.name)
        self._client = None

    def _on_notify(self, _char, data: bytearray) -> None:
        _LOGGER.debug("Status from %s: %s", self.name, data.hex())

    # ------------------------------------------------------------------
    # Low-level write
    # ------------------------------------------------------------------

    async def _raw_write(self, code: int, param: int = 0, pid: int = P.PID_CTRL) -> bool:
        packet = P.build_packet(code, param, pid=pid, serial=self._next_serial())
        async with self._write_lock:
            try:
                await self._client.write_gatt_char(WRITE_UUID, packet, response=True)
                return True
            except (BleakError, asyncio.TimeoutError) as err:
                _LOGGER.error("Write to %s failed: %s", self.name, err)
                self._client = None
                return False

    async def async_send(
        self, code: int, param: int = 0, pid: int = P.PID_CTRL
    ) -> bool:
        """Send a command, reconnecting first if needed."""
        if not (self._client and self._client.is_connected):
            if not await self.async_connect():
                return False
        return await self._raw_write(code, param, pid)

    # ------------------------------------------------------------------
    # Motor control
    # ------------------------------------------------------------------

    async def async_motor_start(
        self, move_code: int, pid: int, motor_key: str
    ) -> None:
        """Send one move command and arm a safety-stop timer."""
        self._cancel_motor_timeout(motor_key)
        self._motor_pids[motor_key] = pid
        await self.async_send(move_code, pid=pid)

        loop = asyncio.get_event_loop()

        def _safety_stop() -> None:
            _LOGGER.debug("Safety timeout for motor %s, sending stop", motor_key)
            # Stop must target the same side (PID) the motor was started on.
            asyncio.ensure_future(self.async_send(P.CMD["stop_motor"], pid=pid))
            self._motor_timeouts.pop(motor_key, None)

        self._motor_timeouts[motor_key] = loop.call_later(
            MOTOR_SAFETY_TIMEOUT, _safety_stop
        )

    async def async_motor_stop(
        self, motor_key: str | None = None, pid: int | None = None
    ) -> None:
        """Cancel timeout and send stop immediately to the correct side."""
        if motor_key:
            self._cancel_motor_timeout(motor_key)
            send_pid = (
                pid if pid is not None
                else self._motor_pids.get(motor_key, P.PID_CTRL)
            )
            await self.async_send(P.CMD["stop_motor"], pid=send_pid)
        else:
            for k in list(self._motor_timeouts):
                self._cancel_motor_timeout(k)
            # No specific motor: stop both sides to be safe.
            await self.async_send(P.CMD["stop_motor"], pid=P.PID_CTRL)
            await self.async_send(P.CMD["stop_motor"], pid=P.PID_CTRL_RIGHT)

    def _cancel_motor_timeout(self, motor_key: str) -> None:
        handle = self._motor_timeouts.pop(motor_key, None)
        if handle:
            handle.cancel()
