"""Config flow for Decora WiFi integration."""

from __future__ import annotations

import logging
from typing import Any

from decora_wifi import DecoraWiFiSession
from decora_wifi.models.residence import Residence
from decora_wifi.models.residential_account import ResidentialAccount
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SelectOptionDict,
)

from .const import (
    CONF_DEVICE_OVERRIDES,
    DEVICE_TYPE_AUTO,
    DEVICE_TYPE_FAN,
    DEVICE_TYPE_LIGHT,
    DOMAIN,
    KNOWN_FAN_MODELS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_credentials(hass, username: str, password: str) -> dict[str, Any]:
    """Validate the user credentials and return device info."""
    session = DecoraWiFiSession()

    # Run blocking login in executor
    success = await hass.async_add_executor_job(session.login, username, password)

    if success is None:
        raise InvalidAuth("Failed to authenticate with myLeviton")

    # Get all devices
    devices = []

    def get_devices():
        perms = session.user.get_residential_permissions()
        all_switches = []
        for permission in perms:
            if permission.residentialAccountId is not None:
                acct = ResidentialAccount(session, permission.residentialAccountId)
                for residence in acct.get_residences():
                    all_switches.extend(residence.get_iot_switches())
            elif permission.residenceId is not None:
                residence = Residence(session, permission.residenceId)
                all_switches.extend(residence.get_iot_switches())
        return all_switches

    switches = await hass.async_add_executor_job(get_devices)

    for switch in switches:
        model = switch.data.get("model", "")
        is_known_fan = any(fm in model for fm in KNOWN_FAN_MODELS)
        devices.append(
            {
                "id": switch.serial,
                "name": switch.name,
                "model": model,
                "detected_type": DEVICE_TYPE_FAN if is_known_fan else DEVICE_TYPE_LIGHT,
            }
        )

    return {"devices": devices, "account_id": username}


class DecoraWifiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Decora WiFi."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - credential entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_credentials(
                    self.hass,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )

                # Use email as unique ID to prevent duplicate entries
                await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
                self._abort_if_unique_id_configured()

                # Store device info for later use
                devices = info["devices"]
                _LOGGER.info(
                    "Found %d Decora WiFi devices: %s",
                    len(devices),
                    [d["name"] for d in devices],
                )

                # Create entry with credentials and empty overrides
                # Users can configure device types in options flow
                return self.async_create_entry(
                    title=f"Decora WiFi ({user_input[CONF_USERNAME]})",
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                    options={
                        CONF_DEVICE_OVERRIDES: {},  # serial -> device_type
                    },
                )

            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected error during setup")
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return DecoraWifiOptionsFlow()


class DecoraWifiOptionsFlow(OptionsFlow):
    """Handle options flow for Decora WiFi - allows device type overrides."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._devices: list[dict] = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage device type options."""
        errors: dict[str, str] = {}

        # Get current devices from coordinator
        coordinator = self.hass.data.get(DOMAIN, {}).get(
            self.config_entry.entry_id, {}
        ).get("coordinator")

        if coordinator and coordinator.data:
            self._devices = coordinator.data.get("devices", [])
        else:
            # Try to fetch devices if coordinator not available
            try:
                info = await validate_credentials(
                    self.hass,
                    self.config_entry.data[CONF_USERNAME],
                    self.config_entry.data[CONF_PASSWORD],
                )
                self._devices = info["devices"]
            except Exception:
                _LOGGER.exception("Failed to fetch devices for options")
                return self.async_abort(reason="cannot_connect")

        if not self._devices:
            return self.async_abort(reason="no_devices")

        if user_input is not None:
            # Build device overrides from user input
            overrides = {}

            # Build name-to-serial mapping
            name_to_serial = {
                f"{d['name']} ({d['model'] or 'Unknown'})": d["id"]
                for d in self._devices
            }

            for field_name, selected_type in user_input.items():
                serial = name_to_serial.get(field_name)
                if serial and selected_type != DEVICE_TYPE_AUTO:
                    overrides[serial] = selected_type

            return self.async_create_entry(
                title="",
                data={CONF_DEVICE_OVERRIDES: overrides},
            )

        # Build schema with current device types
        current_overrides = self.config_entry.options.get(CONF_DEVICE_OVERRIDES, {})

        schema_dict = {}

        for device in self._devices:
            serial = device["id"]
            name = device["name"]
            model = device["model"] or "Unknown"
            detected = device["detected_type"]

            # Get current override or use auto
            current = current_overrides.get(serial, DEVICE_TYPE_AUTO)

            # Use device name as field label by making it the description
            field_label = f"{name} ({model})"

            # Create selector with proper labels
            schema_dict[vol.Required(field_label, default=current)] = SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=DEVICE_TYPE_AUTO, label=f"Auto ({detected})"),
                        SelectOptionDict(value=DEVICE_TYPE_LIGHT, label="Light"),
                        SelectOptionDict(value=DEVICE_TYPE_FAN, label="Fan"),
                    ],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            )

        # Store device mapping for processing (name -> serial)
        self._name_to_serial = {
            f"{d['name']} ({d['model'] or 'Unknown'})": d["id"]
            for d in self._devices
        }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={"devices": str(len(self._devices))},
        )


class InvalidAuth(Exception):
    """Error to indicate invalid authentication."""
