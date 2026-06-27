"""Config flow: auto-discovered via Bluetooth or scan-and-select."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_ADDRESS, CONF_NAME, DOMAIN, SERVICE_UUID


class CinesoundConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle Cinesound config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None

    # ------------------------------------------------------------------
    # Passive auto-discovery (HA BLE scanner sees service UUID in adv)
    # ------------------------------------------------------------------

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or discovery_info.address
        }
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            d = self._discovery
            return self.async_create_entry(
                title=d.name or "Cinesound Sofa",
                data={CONF_ADDRESS: d.address, CONF_NAME: d.name or "Cinesound Sofa"},
            )
        d = self._discovery
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": d.name or d.address},
        )

    # ------------------------------------------------------------------
    # Manual setup: scan what HA has already seen and show a picker
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        # Collect nearby devices advertising the sofa's service UUID.
        # The sofa appears twice under different CoreBluetooth/BlueZ addresses
        # but with the same name (ECBLE583) — deduplicate by name, keep strongest RSSI.
        candidates: dict[str, BluetoothServiceInfoBleak] = {}
        for info in async_discovered_service_info(self.hass, connectable=True):
            if SERVICE_UUID not in [u.lower() for u in (info.service_uuids or [])]:
                continue
            key = info.name or info.address
            if key not in candidates or info.rssi > candidates[key].rssi:
                candidates[key] = info

        if user_input is not None:
            if "discovered_device" in user_input:
                info = candidates[user_input["discovered_device"]]
                address = info.address
                name = info.name or "Cinesound Sofa"
            else:
                address = user_input[CONF_ADDRESS].strip().upper()
                name = "Cinesound Sofa"
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=name,
                data={CONF_ADDRESS: address, CONF_NAME: name},
            )

        if candidates:
            # Show a dropdown of found devices — no address typing needed
            schema = vol.Schema({
                vol.Required("discovered_device"): vol.In(list(candidates))
            })
            errors: dict[str, str] = {}
        else:
            # Nothing seen yet — fall back to raw address entry
            schema = vol.Schema({vol.Required(CONF_ADDRESS): str})
            errors = {"base": "no_devices_found"}

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
