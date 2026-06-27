"""Config flow: auto-discovered via Bluetooth or manual address entry."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import CONF_ADDRESS, CONF_NAME, DOMAIN


class CinesoundConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle Cinesound config flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None

    # ------------------------------------------------------------------
    # Bluetooth auto-discovery (triggered by service UUID in manifest)
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
    # Manual setup fallback
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_ADDRESS].upper())
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, "Cinesound Sofa"),
                data=user_input,
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDRESS): str,
                vol.Optional(CONF_NAME, default="Cinesound Sofa"): str,
            }),
            errors=errors,
        )
