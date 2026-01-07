"""DataUpdateCoordinator for Decora WiFi integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from decora_wifi import DecoraWiFiSession
from decora_wifi.models.person import Person
from decora_wifi.models.residence import Residence
from decora_wifi.models.residential_account import ResidentialAccount

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DEVICE_OVERRIDES,
    DEVICE_TYPE_AUTO,
    DEVICE_TYPE_FAN,
    DEVICE_TYPE_LIGHT,
    DOMAIN,
    KNOWN_FAN_MODELS,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class DecoraWifiCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage Decora WiFi data updates."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.config_entry = entry
        self._session: DecoraWiFiSession | None = None
        self._switches: dict[str, Any] = {}  # serial -> switch object

    async def _async_setup(self) -> None:
        """Set up the coordinator - login and get initial data."""
        username = self.config_entry.data[CONF_USERNAME]
        password = self.config_entry.data[CONF_PASSWORD]

        self._session = DecoraWiFiSession()

        def do_login():
            return self._session.login(username, password)

        success = await self.hass.async_add_executor_job(do_login)

        if success is None:
            raise UpdateFailed("Failed to authenticate with myLeviton")

        _LOGGER.debug("Successfully logged into myLeviton")

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Decora WiFi API."""
        if self._session is None:
            await self._async_setup()

        def fetch_switches():
            """Fetch all switches from the API."""
            perms = self._session.user.get_residential_permissions()
            all_switches = []
            for permission in perms:
                if permission.residentialAccountId is not None:
                    acct = ResidentialAccount(
                        self._session, permission.residentialAccountId
                    )
                    for residence in acct.get_residences():
                        all_switches.extend(residence.get_iot_switches())
                elif permission.residenceId is not None:
                    residence = Residence(self._session, permission.residenceId)
                    all_switches.extend(residence.get_iot_switches())
            return all_switches

        def refresh_switches():
            """Refresh existing switches."""
            for switch in self._switches.values():
                try:
                    switch.refresh()
                except Exception as err:
                    _LOGGER.warning("Failed to refresh switch: %s", err)

        try:
            # First time or if we need to rediscover
            if not self._switches:
                switches = await self.hass.async_add_executor_job(fetch_switches)
                self._switches = {sw.serial: sw for sw in switches}
                _LOGGER.info("Discovered %d Decora WiFi devices", len(self._switches))
            else:
                # Just refresh existing switches
                await self.hass.async_add_executor_job(refresh_switches)

        except Exception as err:
            # Session might have expired, try to re-login
            _LOGGER.warning("Update failed, attempting re-login: %s", err)
            self._session = None
            await self._async_setup()
            switches = await self.hass.async_add_executor_job(fetch_switches)
            self._switches = {sw.serial: sw for sw in switches}

        # Get device type overrides from options
        overrides = self.config_entry.options.get(CONF_DEVICE_OVERRIDES, {})

        # Build device list with type information
        devices = []
        lights = []
        fans = []

        for serial, switch in self._switches.items():
            model = switch.data.get("model", "")
            custom_type = switch.data.get("customType", "")

            # Detect fan by customType (set in myLeviton app) or known model
            is_fan = (
                custom_type == "ceiling-fan"
                or any(fm in model for fm in KNOWN_FAN_MODELS)
            )
            detected_type = DEVICE_TYPE_FAN if is_fan else DEVICE_TYPE_LIGHT

            _LOGGER.debug(
                "Device %s: model=%s, customType=%s, detected=%s",
                switch.name,
                model,
                custom_type,
                detected_type,
            )

            # Check for user override
            override = overrides.get(serial, DEVICE_TYPE_AUTO)
            if override == DEVICE_TYPE_AUTO:
                device_type = detected_type
            else:
                device_type = override

            device_info = {
                "id": serial,
                "name": switch.name,
                "model": model,
                "detected_type": detected_type,
                "device_type": device_type,
                "switch": switch,
            }

            devices.append(device_info)

            if device_type == DEVICE_TYPE_FAN:
                fans.append(device_info)
            else:
                lights.append(device_info)

        _LOGGER.debug(
            "Device summary: %d lights, %d fans", len(lights), len(fans)
        )

        return {
            "devices": devices,
            "lights": lights,
            "fans": fans,
            "switches": self._switches,
        }

    def get_switch(self, serial: str):
        """Get a switch object by serial number."""
        return self._switches.get(serial)

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and logout."""
        if self._session is not None:

            def do_logout():
                try:
                    Person.logout(self._session)
                except Exception:
                    _LOGGER.debug("Logout failed, session may already be closed")

            await self.hass.async_add_executor_job(do_logout)
            self._session = None
